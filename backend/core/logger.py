"""日志工具，基于 loguru。"""
import sys
from loguru import logger
from pathlib import Path


def setup_logger(level: str = "INFO", log_dir: str | None = None) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <7}</level> | "
               "<cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        logger.add(
            Path(log_dir) / "register_{time:YYYYMMDD}.log",
            level=level,
            rotation="50 MB",
            retention="7 days",
            encoding="utf-8",
        )


__all__ = ["logger", "setup_logger"]
