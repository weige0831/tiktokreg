"""滑块验证码求解器：基于 OpenCV 边缘检测 + 模板匹配。

核心思路：
1. 从 TikTok 验证码 SDK 获取背景图（带缺口）和滑块图
2. Canny 边缘检测突出缺口轮廓
3. matchTemplate 定位缺口 X 坐标
4. 换算到浏览器 CSS 像素
"""
import asyncio

import cv2
import numpy as np

from .base import SliderChallenge, SliderSolution, BaseSliderSolver
from ..logger import logger


def _crop_whitespace(img: np.ndarray) -> np.ndarray:
    """裁剪掉图像四周的透明/纯色边框。"""
    if len(img.shape) == 3 and img.shape[2] == 4:
        alpha = img[:, :, 3]
        coords = cv2.findNonZero(alpha)
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            return img[y : y + h, x : x + w]
    # 灰度图
    gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    coords = cv2.findNonZero(255 - gray)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        return img[y : y + h, x : x + w]
    return img


def _to_edge(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY) if img.shape[2] == 4 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Canny(img, 100, 200)


def solve_offline(bg_bytes: bytes, slider_bytes: bytes) -> tuple[int, float]:
    """纯函数：输入图像 bytes，返回 (缺口 X 像素, 置信度)。"""
    bg_arr = np.frombuffer(bg_bytes, dtype=np.uint8)
    slider_arr = np.frombuffer(slider_bytes, dtype=np.uint8)
    bg = cv2.imdecode(bg_arr, cv2.IMREAD_UNCHANGED)
    slider = cv2.imdecode(slider_arr, cv2.IMREAD_UNCHANGED)
    if bg is None or slider is None:
        raise ValueError("图像解码失败")

    slider = _crop_whitespace(slider)
    bg_edge = _to_edge(bg)
    slider_edge = _to_edge(slider)

    result = cv2.matchTemplate(bg_edge, slider_edge, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    return int(max_loc[0]), float(max_val)


class OpenCVSliderSolver(BaseSliderSolver):
    """基于 OpenCV 的滑块求解器（异步包装）。"""

    async def solve(self, challenge: SliderChallenge) -> SliderSolution:
        logger.debug(
            f"求解滑块: raw_img_w={challenge.raw_image_width} "
            f"container_w={challenge.container_width}"
        )
        # 在线程池里跑 OpenCV（避免阻塞 event loop）
        raw_x, confidence = await asyncio.to_thread(
            solve_offline, challenge.bg_image_bytes, challenge.slider_image_bytes
        )
        # 换算到浏览器坐标系
        scale = challenge.container_width / challenge.raw_image_width
        target_x = raw_x * scale
        logger.info(
            f"滑块求解结果: raw_x={raw_x} conf={confidence:.3f} target_x={target_x:.1f}"
        )
        return SliderSolution(
            target_x=target_x,
            confidence=confidence,
            raw_x=raw_x,
        )
