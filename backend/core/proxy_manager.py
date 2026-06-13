"""代理管理器：读取代理列表、轮换、失败计数。

默认 enabled=False 时返回 None，走 GitHub Actions 本机 IP。
"""
import random
from pathlib import Path
from threading import Lock

from .logger import logger


class ProxyInfo:
    def __init__(self, raw: str):
        # 支持 http://user:pass@ip:port 或 ip:port 或 user:pass@ip:port
        self.raw = raw.strip()
        self.uses = 0
        self.fails = 0
        self.blacklisted = False
        self._parse()

    def _parse(self) -> None:
        raw = self.raw
        if "://" not in raw:
            raw = "http://" + raw
        from urllib.parse import urlparse

        u = urlparse(raw)
        self.scheme = u.scheme or "http"
        self.username = u.username
        self.password = u.password
        self.host = u.hostname
        self.port = u.port

    @property
    def playwright_arg(self) -> dict:
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return {"server": f"{self.scheme}://{auth}{self.host}:{self.port}"}

    def __repr__(self) -> str:
        return f"<Proxy {self.host}:{self.port} uses={self.uses} fails={self.fails}>"


class ProxyManager:
    def __init__(self, enabled: bool, proxy_file: str, max_uses: int, max_fails: int):
        self.enabled = enabled
        self.max_uses = max_uses
        self.max_fails = max_fails
        self.proxies: list[ProxyInfo] = []
        self._lock = Lock()
        if enabled:
            self._load(proxy_file)

    def _load(self, proxy_file: str) -> None:
        p = Path(proxy_file)
        if not p.exists():
            logger.warning(f"代理文件不存在: {p}, 将走本机 IP")
            self.enabled = False
            return
        lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
        for line in lines:
            try:
                self.proxies.append(ProxyInfo(line))
            except Exception as e:
                logger.warning(f"无法解析代理: {line} ({e})")
        logger.info(f"加载代理 {len(self.proxies)} 个")

    def acquire(self) -> dict | None:
        """获取一个可用代理（playwright 格式）。返回 None 表示走本机。"""
        if not self.enabled or not self.proxies:
            return None
        with self._lock:
            available = [p for p in self.proxies if not p.blacklisted and p.uses < self.max_uses]
            if not available:
                logger.warning("所有代理均不可用，本次走本机 IP")
                return None
            chosen = random.choice(available)
            chosen.uses += 1
            logger.info(f"使用代理: {chosen.host}:{chosen.port} (累计 {chosen.uses}/{self.max_uses})")
            return chosen.playwright_arg

    def report_fail(self, proxy_arg: dict | None) -> None:
        if proxy_arg is None:
            return
        with self._lock:
            for p in self.proxies:
                if p.playwright_arg == proxy_arg:
                    p.fails += 1
                    if p.fails >= self.max_fails:
                        p.blacklisted = True
                        logger.warning(f"代理拉黑: {p.host}:{p.port} 连续失败 {p.fails} 次")
                    break
