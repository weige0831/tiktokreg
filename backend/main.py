"""TikTok 批量注册机入口。

运行在 GitHub Actions 中，注册完成后通过 webhook 推送凭证到前端服务。
"""
import argparse
import asyncio
import os
import random
import string
import sys
from datetime import datetime
from pathlib import Path

# 把 backend/ 加入 path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright

from core.config_loader import AppConfig, load_config
from core.logger import logger, setup_logger
from core.proxy_manager import ProxyManager
from core.register_pipeline import RegisterPipeline
from core.tempmail_client import TempMailClient
from core.webhook_exporter import WebhookExporter


def gen_password(length: int = 16) -> str:
    """生成强随机密码（包含大小写字母+数字+特殊符号，符合 TikTok 要求）。"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    # 确保至少每种字符都有
    pwd = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*"),
    ]
    pwd += [random.choice(chars) for _ in range(length - 4)]
    random.shuffle(pwd)
    return "".join(pwd)


def gen_birth_date() -> str:
    """生成 18-35 岁之间的随机生日 (MM/DD/YYYY)。"""
    year = random.randint(1988, 2005)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{month:02d}/{day:02d}/{year}"


async def run(count: int, concurrency: int, config_path: str) -> int:
    """主流程：注册 count 个账号，并发 concurrency。返回成功数。"""
    cfg: AppConfig = load_config(config_path)
    # 命令行覆盖
    cfg.register.count = count
    cfg.register.concurrency = concurrency

    setup_logger(level=os.environ.get("LOG_LEVEL", "INFO"))

    logger.info("=" * 60)
    logger.info(f"TikTok 批量注册机启动 - 目标 {count} 个账号，并发 {concurrency}")
    logger.info(f"tempmail: {cfg.tempmail.base_url or '(未配置)'}")
    logger.info(f"webhook : {cfg.webhook.url or '(未配置，结果不会推送)'}")
    logger.info(f"代理启用: {cfg.proxy.enabled}")
    logger.info("=" * 60)

    # 关键 secrets 检查
    if not cfg.tempmail.base_url:
        logger.error("TEMPMAIL_BASE_URL 环境变量未配置，无法注册")
        return 1
    if not cfg.webhook.url:
        logger.warning("WEBHOOK_URL 未配置，注册结果将不会推送（仅记录日志）")

    proxy_manager = ProxyManager(
        enabled=cfg.proxy.enabled,
        proxy_file=str(Path(__file__).parent / cfg.proxy.proxy_file),
        max_uses=cfg.proxy.max_uses_per_proxy,
        max_fails=cfg.proxy.max_fails_per_proxy,
    )

    # 预生成所有邮箱和密码
    async with TempMailClient(cfg.tempmail) as mail:
        emails: list[tuple[str, str]] = []  # (email, token)
        for i in range(count):
            for attempt in range(3):
                try:
                    email, token = await mail.create_address()
                    emails.append((email, token))
                    break
                except Exception as e:
                    logger.warning(f"创建邮箱失败 ({attempt}): {e}")
                    await asyncio.sleep(2)
            else:
                logger.error(f"无法创建第 {i+1} 个邮箱，跳过")
        logger.info(f"成功预创建 {len(emails)} 个临时邮箱")

    if not emails:
        logger.error("没有任何可用邮箱，退出")
        return 1

    # 并发执行注册
    sem = asyncio.Semaphore(concurrency)
    results = []

    async def register_one(pw, email: str, token: str) -> None:
        async with sem:
            password = gen_password()
            birth = gen_birth_date()
            logger.info(f"[{email}] password={password} birth={birth}")
            pipeline = RegisterPipeline(cfg, pw, proxy_manager)
            result = await pipeline.run(email, token, password, birth)
            results.append(result)
            # 注册间隔（避免并发对同 IP 造成风控）
            await asyncio.sleep(random.uniform(5, 15))

    async with async_playwright() as pw:
        tasks = [register_one(pw, e, t) for e, t in emails]
        await asyncio.gather(*tasks, return_exceptions=True)

    # 推送结果
    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count
    logger.info(f"注册完成: 成功 {success_count}/{len(results)}，失败 {failed_count}")

    if cfg.webhook.url:
        async with WebhookExporter(cfg.webhook) as exporter:
            payload = {
                "batch_id": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
                "registered_at": datetime.utcnow().isoformat() + "Z",
                "total": len(results),
                "success_count": success_count,
                "failed_count": failed_count,
                "accounts": [r.to_dict() for r in results],
            }
            try:
                await exporter.post_batch(payload)
            except Exception as e:
                logger.error(f"webhook 推送失败: {e}")

    # 控制台输出汇总（便于 Actions 日志查看）
    logger.info("=" * 60)
    logger.info("账号汇总:")
    for r in results:
        status = "✓" if r.success else "✗"
        line = f"  {status} {r.email}"
        if r.success and r.credentials:
            line += f"  session={r.credentials.get('session_id', '')[:20]}..."
        elif r.error_msg:
            line += f"  err={r.error_msg[:80]}"
        logger.info(line)
    logger.info("=" * 60)

    return 0 if success_count > 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="TikTok 批量注册机")
    parser.add_argument("--count", type=int, default=None, help="注册数量")
    parser.add_argument("--concurrency", type=int, default=None, help="并发数")
    parser.add_argument(
        "--config", type=str, default=str(Path(__file__).parent / "config.yaml"),
        help="配置文件路径",
    )
    args = parser.parse_args()

    count = args.count or 5
    concurrency = args.concurrency or 2
    return asyncio.run(run(count=count, concurrency=concurrency, config_path=args.config))


if __name__ == "__main__":
    sys.exit(main())
