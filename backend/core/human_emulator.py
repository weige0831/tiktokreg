"""人类行为模拟：贝塞尔鼠标轨迹、打字节奏、随机停顿。

所有方法均为 async，配合 Playwright 使用。
"""
import asyncio
import math
import random

from .config_loader import HumanConfig


class HumanEmulator:
    def __init__(self, cfg: HumanConfig):
        self.cfg = cfg

    async def sleep(self, min_s: float | None = None, max_s: float | None = None) -> None:
        """模拟人类思考停顿。"""
        mn = min_s if min_s is not None else self.cfg.action_pause_min
        mx = max_s if max_s is not None else self.cfg.action_pause_max
        await asyncio.sleep(random.uniform(mn, mx))

    async def human_type(self, page, selector: str, text: str) -> None:
        """模拟人类逐字符输入：随机延迟 + 偶尔停顿。"""
        await page.click(selector)
        await self.sleep(0.3, 0.7)
        for i, ch in enumerate(text):
            await page.keyboard.type(ch)
            delay = random.uniform(self.cfg.type_delay_min, self.cfg.type_delay_max) / 1000
            await asyncio.sleep(delay)
            # 偶尔停顿（5% 概率，模拟看屏幕）
            if random.random() < 0.05:
                await self.sleep(0.5, 1.5)

    async def human_click(self, page, selector: str) -> None:
        """模拟人类点击：先移动到元素附近，停顿后点击。"""
        box = await page.locator(selector).bounding_box()
        if box:
            target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
            target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
            await self._move_mouse(page, target_x, target_y)
        await self.sleep(0.2, 0.6)
        await page.click(selector)

    async def _move_mouse(self, page, target_x: float, target_y: float) -> None:
        """贝塞尔曲线鼠标移动。"""
        current = await page.evaluate("() => ({x: window.__mx || 0, y: window.__my || 0})")
        steps = 25
        # 生成 2 个控制点
        ctrl1_x = random.uniform(min(current["x"], target_x), max(current["x"], target_x))
        ctrl1_y = random.uniform(current["y"], target_y)
        ctrl2_x = random.uniform(min(current["x"], target_x), max(current["x"], target_x))
        ctrl2_y = random.uniform(current["y"], target_y)

        for i in range(1, steps + 1):
            t = i / steps
            x = (
                (1 - t) ** 3 * current["x"]
                + 3 * (1 - t) ** 2 * t * ctrl1_x
                + 3 * (1 - t) * t**2 * ctrl2_x
                + t**3 * target_x
            )
            y = (
                (1 - t) ** 3 * current["y"]
                + 3 * (1 - t) ** 2 * t * ctrl1_y
                + 3 * (1 - t) * t**2 * ctrl2_y
                + t**3 * target_y
            )
            await page.mouse.move(x, y)
            await page.evaluate(f"window.__mx = {x}; window.__my = {y};")
            await asyncio.sleep(
                random.uniform(self.cfg.mouse_step_delay_min, self.cfg.mouse_step_delay_max) / 1000
            )

    async def human_drag_slider(
        self, page, slider_selector: str, distance: float, jitter: bool = True
    ) -> None:
        """模拟人类拖动滑块：先移动到滑块 → 按下 → 加速→减速→微调 → 释放。"""
        box = await page.locator(slider_selector).bounding_box()
        if not box:
            raise RuntimeError(f"无法获取滑块 bounding_box: {slider_selector}")

        start_x = box["x"] + box["width"] / 2
        start_y = box["y"] + box["height"] / 2

        await self._move_mouse(page, start_x, start_y)
        await self.sleep(0.2, 0.5)
        await page.mouse.down()

        duration = random.uniform(
            self.cfg.slider_drag_duration_min, self.cfg.slider_drag_duration_max
        )
        steps = max(30, int(duration / 0.02))

        # 模拟"先快后慢"的轨迹：用 ease-out 曲线
        overshoot = random.uniform(2, 12) if jitter else 0  # 偶尔过冲
        track: list[tuple[float, float]] = []
        for i in range(1, steps + 1):
            t = i / steps
            eased = 1 - (1 - t) ** 3  # ease-out cubic
            x_offset = distance * eased
            # 在 70%-90% 时引入过冲
            if 0.7 < t < 0.9 and overshoot > 0:
                x_offset += overshoot * math.sin((t - 0.7) / 0.2 * math.pi)
            # 末端微调
            if t > 0.95:
                x_offset += random.uniform(-1, 1)
            y_jitter = random.uniform(-1.5, 1.5) if jitter else 0
            track.append((start_x + x_offset, start_y + y_jitter))

        for x, y in track:
            await page.mouse.move(x, y)
            await asyncio.sleep(duration / steps + random.uniform(0, 0.005))

        # 末端停留一会
        await self.sleep(0.1, 0.3)
        await page.mouse.up()
