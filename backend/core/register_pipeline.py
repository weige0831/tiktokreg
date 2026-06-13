"""TikTok 注册主流程编排。"""
import asyncio
import random
from datetime import datetime
from typing import Any

from playwright.async_api import Page, Playwright, TimeoutError as PWTimeoutError

from .browser import BrowserManager
from .config_loader import AppConfig
from .credential_extractor import extract_credentials
from .fingerprint_gen import generate_fingerprint
from .human_emulator import HumanEmulator
from .logger import logger
from .proxy_manager import ProxyManager
from .retry import async_retry
from .tempmail_client import TempMailClient
from .captcha.slider_solver import OpenCVSliderSolver
from .captcha.base import SliderChallenge


# TikTok 注册页 URL
SIGNUP_URL = "https://www.tiktok.com/signup?lang=en"


class AccountResult:
    """单账号注册结果。"""

    def __init__(self, email: str):
        self.email = email
        self.success: bool = False
        self.credentials: dict[str, Any] | None = None
        self.error_msg: str = ""
        self.started_at: datetime = datetime.utcnow()
        self.finished_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "email": self.email,
            "status": "success" if self.success else "failed",
            "error_msg": self.error_msg,
            "registered_at": (self.finished_at or datetime.utcnow()).isoformat() + "Z",
        }
        if self.credentials:
            d.update(self.credentials)
        return d


class RegisterPipeline:
    """单账号注册流程。"""

    def __init__(
        self,
        cfg: AppConfig,
        pw: Playwright,
        proxy_manager: ProxyManager,
    ):
        self.cfg = cfg
        self.pw = pw
        self.proxy_manager = proxy_manager
        self.browser_mgr = BrowserManager(cfg)
        self.human = HumanEmulator(cfg.human)
        self.slider_solver = OpenCVSliderSolver()

    async def run(self, email: str, email_token: str, password: str, birth_date: str) -> AccountResult:
        result = AccountResult(email=email)
        proxy_arg = self.proxy_manager.acquire()

        fingerprint = generate_fingerprint(
            self.cfg.browser.viewports,
            self.cfg.browser.timezones,
            self.cfg.browser.locales,
        )
        logger.info(f"[{email}] 开始注册流程，fingerprint={fingerprint.hash}")

        try:
            await asyncio.wait_for(
                self._do_register(email, email_token, password, birth_date, proxy_arg, fingerprint, result),
                timeout=self.cfg.register.single_account_timeout,
            )
        except PWTimeoutError as e:
            result.error_msg = f"页面超时: {e}"
        except asyncio.TimeoutError:
            result.error_msg = f"注册流程超时 ({self.cfg.register.single_account_timeout}s)"
        except Exception as e:
            result.error_msg = f"{type(e).__name__}: {e}"
            logger.exception(f"[{email}] 注册异常")

        if not result.success and proxy_arg:
            self.proxy_manager.report_fail(proxy_arg)

        result.finished_at = datetime.utcnow()
        status_text = "成功" if result.success else "失败"
        logger.info(f"[{email}] 注册{status_text}: {result.error_msg or 'OK'}")
        return result

    async def _do_register(
        self,
        email: str,
        email_token: str,
        email_password: str,
        birth_date: str,
        proxy_arg: dict | None,
        fingerprint,
        result: AccountResult,
    ) -> None:
        context = await self.browser_mgr.launch_context(self.pw, fingerprint, proxy_arg)
        try:
            page = await context.new_page()
            page.set_default_timeout(30_000)

            # Step 1: 打开注册页
            logger.info(f"[{email}] 访问 {SIGNUP_URL}")
            await page.goto(SIGNUP_URL, wait_until="domcontentloaded")
            await self.human.sleep(2, 4)

            # Step 2: 选择邮箱注册（默认是手机号）
            # TikTok 注册页 UI 经常变动，这里用多个备选选择器
            await self._choose_email_signup(page)

            # Step 3: 填邮箱和密码
            await self._fill_email_password(page, email, email_password)

            # Step 4: 填生日（必须 ≥ 18 岁）
            await self._fill_birth_date(page, birth_date)

            # Step 5: 提交，触发验证码
            await self._click_signup_button(page)
            await self.human.sleep(2, 4)

            # Step 6: 处理验证码（滑块）
            await self._handle_captcha_if_present(page)

            # Step 7: 邮箱验证码
            await self._submit_email_code(page, email_token)

            # Step 8: 等待跳转到首页（注册成功标志）
            await self._wait_for_success(page)

            # Step 9: 抽取凭证
            username = await self._extract_username(page)
            result.credentials = await extract_credentials(
                context, self.cfg, fingerprint,
                email=email,
                password=email_password,
                username=username,
                birth_date=birth_date,
                proxy_used=(proxy_arg.get("server") if proxy_arg else None),
            )
            result.success = True
        finally:
            try:
                await context.close()
            except Exception:
                pass

    # ---------- 各步骤实现 ----------

    async def _choose_email_signup(self, page: Page) -> None:
        """TikTok 注册页选择邮箱注册方式。"""
        # 备选选择器（按优先级）
        selectors = [
            'a[href*="email"]',
            'div[data-e2e="signup-email-tab"]',
            'text="Sign up with email"',
            'text="Email"',
            'div[class*="email"]',
        ]
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    await self.human.human_click(page, sel)
                    logger.info(f"切换到邮箱注册 (selector={sel})")
                    await self.human.sleep()
                    return
            except Exception:
                continue
        logger.warning("未找到邮箱注册切换按钮，假设当前已是邮箱注册页")

    async def _fill_email_password(self, page: Page, email: str, password: str) -> None:
        """填入邮箱、密码。"""
        email_selectors = [
            'input[name="email"]',
            'input[type="email"]',
            'input[placeholder*="email" i]',
        ]
        for sel in email_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    await self.human.human_type(page, sel, email)
                    logger.info(f"邮箱已填入 ({sel})")
                    break
            except Exception:
                continue

        await self.human.sleep(0.5, 1.2)

        pwd_selectors = [
            'input[name="password"]',
            'input[type="password"]',
        ]
        for sel in pwd_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    await self.human.human_type(page, sel, password)
                    logger.info(f"密码已填入 ({sel})")
                    break
            except Exception:
                continue

    async def _fill_birth_date(self, page: Page, birth_date: str) -> None:
        """填生日 (MM/DD/YYYY)。TikTok 通常用三段 select。"""
        # 多数情况 TikTok 不在第一页就要生日，所以宽容处理
        try:
            # 尝试寻找生日输入
            month, day, year = birth_date.split("/")
            for sel, value in [
                ('select[name="month"]', month),
                ('select[name="day"]', day),
                ('select[name="year"]', year),
            ]:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.select_option(value=value)
                    await self.human.sleep(0.3, 0.8)
            logger.info(f"生日已填入: {birth_date}")
        except Exception as e:
            logger.debug(f"生日填写跳过（可能未到该步骤）: {e}")

    async def _click_signup_button(self, page: Page) -> None:
        """点击注册提交按钮。"""
        selectors = [
            'button[type="submit"]',
            'button[data-e2e="signup-button"]',
            'button:has-text("Sign up")',
            'div[role="button"]:has-text("Sign up")',
            'button:has-text("Continue")',
        ]
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    await self.human.human_click(page, sel)
                    logger.info(f"点击注册按钮 ({sel})")
                    return
            except Exception:
                continue
        logger.warning("未找到注册按钮，可能已自动提交")

    async def _handle_captcha_if_present(self, page: Page) -> None:
        """检测并处理验证码（滑块为主）。"""
        for attempt in range(1, self.cfg.register.captcha_max_retries + 1):
            try:
                # 检测验证码容器
                captcha_selectors = [
                    'div[class*="captcha"]',
                    'iframe[src*="captcha"]',
                    'div[id*="captcha"]',
                ]
                visible = False
                for sel in captcha_selectors:
                    try:
                        loc = page.locator(sel).first
                        if await loc.count() > 0 and await loc.is_visible(timeout=2000):
                            visible = True
                            break
                    except Exception:
                        continue
                if not visible:
                    logger.info("无验证码或已通过")
                    return

                logger.info(f"检测到验证码，尝试第 {attempt} 次")
                await self._solve_slider_captcha(page)
                await self.human.sleep(2, 4)
            except Exception as e:
                logger.warning(f"验证码处理失败: {e}")
                if attempt >= self.cfg.register.captcha_max_retries:
                    raise RuntimeError(f"验证码求解失败 ({attempt} 次)")

    async def _solve_slider_captcha(self, page: Page) -> None:
        """从 TikTok 验证码 iframe 抓取图像并求解。"""
        # TikTok 验证码通常在 iframe 内
        iframe_loc = page.locator('iframe[src*="captcha"], iframe[id*="captcha"]').first
        target_frame = page.main_frame
        if await iframe_loc.count() > 0:
            try:
                element = await iframe_loc.element_handle()
                if element:
                    frame = await element.content_frame()
                    if frame:
                        target_frame = frame
            except Exception:
                pass

        # 抓取背景图和滑块图（TikTok Sec Captcha v2 结构）
        # 实际 selector 可能因版本变化，这里用多个备选
        bg_candidates = [
            'img[class*="captcha-verify-image"]',
            'img[id*="captcha-bg"]',
            'img[src*="verify"]',
        ]
        slider_candidates = [
            'div[class*="captcha-verify-slider"]',
            'img[class*="captcha-slider"]',
            'div[data-e2e="captcha-slider"]',
        ]

        bg_url: str | None = None
        for sel in bg_candidates:
            try:
                loc = target_frame.locator(sel).first
                if await loc.count() > 0:
                    bg_url = await loc.get_attribute("src")
                    if bg_url:
                        break
            except Exception:
                continue
        if not bg_url:
            raise RuntimeError("无法抓取背景图")

        container_size = await target_frame.evaluate(
            """() => {
                const el = document.querySelector('img[class*="captcha-verify-image"]');
                return el ? el.width : 340;
            }"""
        )

        # 下载背景图
        bg_bytes = await self._fetch_image_bytes(page, bg_url)

        # TikTok 通常没有单独的滑块图（缺口已嵌在背景图里），我们用边缘检测找缺口
        from .captcha.slider_solver import solve_offline
        raw_x, confidence = await asyncio.to_thread(solve_offline, bg_bytes, bg_bytes)

        # 找滑块手柄
        slider_handle_sel: str | None = None
        for sel in slider_candidates:
            try:
                loc = target_frame.locator(sel).first
                if await loc.count() > 0:
                    slider_handle_sel = sel
                    break
            except Exception:
                continue

        if not slider_handle_sel:
            raise RuntimeError("找不到滑块手柄")

        # 拖动滑块（贝塞尔轨迹）
        scale = container_size / 552  # TikTok 标准背景宽 552px
        target_distance = raw_x * scale
        logger.info(f"准备拖动滑块: {target_distance:.1f}px")
        await self.human.human_drag_slider(target_frame, slider_handle_sel, target_distance)

    async def _fetch_image_bytes(self, page: Page, url: str) -> bytes:
        """通过浏览器抓取图片二进制（保留 cookie / referer）。"""
        # 用 page.evaluate 在浏览器内 fetch 二进制
        b64 = await page.evaluate(
            """async (url) => {
                const r = await fetch(url, { credentials: 'include' });
                const buf = await r.arrayBuffer();
                const bytes = new Uint8Array(buf);
                let binary = '';
                for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
                return btoa(binary);
            }""",
            url,
        )
        import base64
        return base64.b64decode(b64)

    async def _submit_email_code(self, page: Page, email_token: str) -> None:
        """等待并提交邮箱验证码。"""
        async with TempMailClient(self.cfg.tempmail) as mail:
            code = await mail.poll_verification_code(email_token)
        # 找验证码输入框
        code_selectors = [
            'input[name="code"]',
            'input[data-e2e="email-verification-code"]',
            'input[placeholder*="code" i]',
            'input[type="text"][maxlength="6"]',
        ]
        submitted = False
        for sel in code_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=5000):
                    await self.human.human_type(page, sel, code)
                    await self.human.sleep(0.5, 1.2)
                    # 尝试找提交按钮
                    try_submit = [
                        'button[type="submit"]',
                        'button:has-text("Verify")',
                        'button:has-text("Continue")',
                        'button:has-text("Next")',
                    ]
                    for btn_sel in try_submit:
                        try:
                            btn = page.locator(btn_sel).first
                            if await btn.count() > 0 and await btn.is_visible():
                                await self.human.human_click(page, btn_sel)
                                submitted = True
                                break
                        except Exception:
                            continue
                    if submitted:
                        break
            except Exception:
                continue
        if submitted:
            logger.info("邮箱验证码已提交")
        else:
            logger.warning("未找到验证码输入框，可能不需要邮箱验证")

    async def _wait_for_success(self, page: Page) -> None:
        """等待注册成功（跳转首页或出现用户菜单）。"""
        success_indicators = [
            lambda: page.wait_for_url("**/foryou**", timeout=15000),
            lambda: page.wait_for_url("**/tiktok.com/**", timeout=15000),
            lambda: page.locator('div[data-e2e="profile-icon"]').wait_for(timeout=15000),
        ]
        errors = []
        for ind in success_indicators:
            try:
                await ind()
                logger.info("注册成功（已检测到登录后页面）")
                await self.human.sleep(2, 4)
                return
            except Exception as e:
                errors.append(str(e))
        raise RuntimeError(f"无法确认注册成功: {errors[0][:100]}")

    async def _extract_username(self, page: Page) -> str | None:
        """从首页抓取生成的 username。"""
        try:
            return await page.evaluate(
                """() => {
                    const el = document.querySelector('[data-e2e="profile-icon"]') ||
                               document.querySelector('.avatar');
                    if (el && el.getAttribute('aria-label')) {
                        return el.getAttribute('aria-label');
                    }
                    return null;
                }"""
            )
        except Exception:
            return None
