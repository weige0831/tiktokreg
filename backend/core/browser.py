"""Playwright 浏览器封装 + stealth 反检测注入。"""
import random

from playwright.async_api import Browser, BrowserContext, Playwright

from .config_loader import AppConfig
from .fingerprint_gen import Fingerprint
from .logger import logger

# stealth.min.js（精简版，覆盖 navigator.webdriver、chrome.runtime 等关键点）
_STEALTH_JS = """
// 隐藏 webdriver 标记
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 伪造 chrome.runtime
window.chrome = { runtime: {} };

// 修正 permissions API
const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
  window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : originalQuery(parameters)
  );
}

// 修正 plugins 长度
Object.defineProperty(navigator, 'plugins', {
  get: () => [1, 2, 3, 4, 5],
});

// 修正 languages
Object.defineProperty(navigator, 'languages', {
  get: () => ['__LOCALE__', 'en'],
});

// WebGL 伪造
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function (parameter) {
  if (parameter === 37445) return '__WEBGL_VENDOR__';
  if (parameter === 37446) return '__WEBGL_RENDERER__';
  return getParameter.call(this, parameter);
};

// hardwareConcurrency
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => __HC__ });
// deviceMemory
Object.defineProperty(navigator, 'deviceMemory', { get: () => __DM__ });
"""


class BrowserManager:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg

    async def launch_context(
        self,
        pw: Playwright,
        fingerprint: Fingerprint,
        proxy_arg: dict | None = None,
    ) -> BrowserContext:
        """启动一个 BrowserContext，注入 stealth + 指纹。"""
        launch_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            f"--window-size={fingerprint.viewport['width']},{fingerprint.viewport['height']}",
        ]

        logger.info(
            f"启动浏览器: UA={fingerprint.user_agent[:50]}... "
            f"viewport={fingerprint.viewport} tz={fingerprint.timezone}"
        )

        browser: Browser = await pw.chromium.launch(
            headless=True,
            args=launch_args,
        )

        context_kwargs = {
            "user_agent": fingerprint.user_agent,
            "viewport": fingerprint.viewport,
            "timezone_id": fingerprint.timezone,
            "locale": fingerprint.locale,
            "ignore_https_errors": True,
            "java_script_enabled": True,
        }
        if proxy_arg:
            context_kwargs["proxy"] = proxy_arg

        context = await browser.new_context(**context_kwargs)

        # 注入 stealth
        stealth = (
            _STEALTH_JS.replace("__LOCALE__", fingerprint.locale)
            .replace("__WEBGL_VENDOR__", fingerprint.webgl_vendor)
            .replace("__WEBGL_RENDERER__", fingerprint.webgl_renderer)
            .replace("__HC__", str(fingerprint.hardware_concurrency))
            .replace("__DM__", str(fingerprint.device_memory))
        )
        await context.add_init_script(stealth)

        # 设置屏幕分辨率与窗口一致
        await context.set_extra_http_headers(
            {
                "Accept-Language": f"{fingerprint.locale},en;q=0.9",
                "Sec-Ch-Ua-Platform": f'"{fingerprint.platform}"',
            }
        )

        return context
