"""验证码求解器抽象基类 + 付费平台预留接口。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SliderChallenge:
    """滑块验证码挑战数据。"""
    bg_image_bytes: bytes       # 背景图（带缺口）
    slider_image_bytes: bytes   # 滑块图
    container_width: int        # 拖动容器宽度（CSS 像素）
    raw_image_width: int        # 原始图片宽度（用于换算）


@dataclass
class SliderSolution:
    """滑块求解结果。"""
    target_x: float             # 拖动距离（CSS 像素）
    confidence: float           # 置信度 [0, 1]
    raw_x: int                  # 原始图像坐标系下的缺口 X


class BaseSliderSolver(ABC):
    @abstractmethod
    async def solve(self, challenge: SliderChallenge) -> SliderSolution:
        ...


class BaseCaptchaProvider(ABC):
    """付费打码平台抽象基类（预留接口）。"""

    name: str = "base"

    @abstractmethod
    async def solve_slider(self, bg_bytes: bytes, slider_bytes: bytes) -> int:
        """返回缺口 X 坐标（原始图像坐标）。"""
        ...

    @abstractmethod
    async def solve_rotate(self, img_bytes: bytes) -> int:
        """返回旋转角度（度）。"""
        ...


class TwoCaptchaProvider(BaseCaptchaProvider):
    """2Captcha 付费打码平台预留实现（占位）。"""
    name = "2captcha"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def solve_slider(self, bg_bytes: bytes, slider_bytes: bytes) -> int:
        raise NotImplementedError("2Captcha 接入预留，需要时再实现")

    async def solve_rotate(self, img_bytes: bytes) -> int:
        raise NotImplementedError("2Captcha 接入预留，需要时再实现")


class CapSolverProvider(BaseCaptchaProvider):
    """CapSolver 付费打码平台预留实现（占位）。"""
    name = "capsolver"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def solve_slider(self, bg_bytes: bytes, slider_bytes: bytes) -> int:
        raise NotImplementedError("CapSolver 接入预留，需要时再实现")

    async def solve_rotate(self, img_bytes: bytes) -> int:
        raise NotImplementedError("CapSolver 接入预留，需要时再实现")
