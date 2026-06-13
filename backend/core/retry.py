"""失败重试装饰器。"""
import asyncio
import functools
from typing import Awaitable, Callable, TypeVar

from .logger import logger

T = TypeVar("T")


def async_retry(max_retries: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """异步重试装饰器。失败 max_retries 次后抛出最后一次异常。"""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    logger.warning(
                        f"{func.__name__} 第 {attempt}/{max_retries} 次失败: {type(e).__name__}: {e}"
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(delay * attempt)
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator
