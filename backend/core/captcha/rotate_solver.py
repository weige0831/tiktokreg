"""3D 旋转验证码求解器（预留 stub）。

TikTok 偶尔会出现 3D 物体旋转对齐验证。本模块先实现占位接口，
后续可接入：
  - 自研轻量 CNN 回归模型
  - rotate-captcha-cracker 开源项目
  - 付费打码平台
"""
from .base import BaseCaptchaProvider


class RotateSolver:
    """3D 旋转验证码 stub。"""

    async def solve(self, image_bytes: bytes) -> int:
        raise NotImplementedError(
            "3D 旋转验证码求解器尚未实现。"
            "TikTok 主要使用滑块验证，本模块预留接口。"
            "如需启用，可参考 https://github.com/garethgeorge/rotate-captcha-cracker"
        )
