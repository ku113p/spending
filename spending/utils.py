import asyncio
from functools import wraps
import logging
import time
from typing import Optional


def create_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    logger = logging.Logger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def async_timing(logger: Optional[logging.Logger] = None):
    def decorator(func):
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("async_timing decorator only works with async functions")

        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            end = time.perf_counter()
            duration = end - start
            (logger or create_logger()).info(f"{func.__name__} took {duration:.4f} seconds")
            return result

        return wrapper
    return decorator
