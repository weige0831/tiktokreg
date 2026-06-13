"""指纹随机化生成器。"""
import random
from dataclasses import dataclass


# 常见 User-Agent 候选（Chrome stable 频道）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

WEBGL_VENDORS = ["Google Inc. (NVIDIA)", "Google Inc. (Intel)", "Google Inc. (AMD)"]
WEBGL_RENDERERS = [
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
]


@dataclass
class Fingerprint:
    user_agent: str
    viewport: dict
    timezone: str
    locale: str
    webgl_vendor: str
    webgl_renderer: str
    platform: str
    hardware_concurrency: int
    device_memory: int

    @property
    def hash(self) -> str:
        import hashlib

        raw = f"{self.user_agent}|{self.viewport}|{self.timezone}|{self.locale}|{self.webgl_vendor}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def generate_fingerprint(viewports: list[dict], timezones: list[str], locales: list[str]) -> Fingerprint:
    ua = random.choice(USER_AGENTS)
    platform = "Win32" if "Windows" in ua else ("MacIntel" if "Mac" in ua else "Linux x86_64")
    return Fingerprint(
        user_agent=ua,
        viewport=random.choice(viewports) if viewports else {"width": 1920, "height": 1080},
        timezone=random.choice(timezones) if timezones else "America/New_York",
        locale=random.choice(locales) if locales else "en-US",
        webgl_vendor=random.choice(WEBGL_VENDORS),
        webgl_renderer=random.choice(WEBGL_RENDERERS),
        platform=platform,
        hardware_concurrency=random.choice([4, 8, 12, 16]),
        device_memory=random.choice([4, 8, 16]),
    )
