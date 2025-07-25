import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import wraps
import hashlib
import logging
import pickle
import time
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional, Self

import redis.asyncio as redis
from langfuse.langchain import CallbackHandler
from redis.typing import EncodableT

from config import Config


log_level = logging.INFO
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def create_logger(name: str = __name__, level: int = log_level) -> logging.Logger:
    logger = logging.Logger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = create_logger()


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


def get_langfuse_handler() -> CallbackHandler:
    cb_handler = CallbackHandler()

    if cb_handler.client.auth_check():
        return cb_handler

    raise Exception("langfuse dead connection")


async def publish_message(channel_name: str, message: EncodableT) -> int:
    async with _get_redis_connection() as r:
        return await r.publish(channel_name, pickle.dumps(message))


@asynccontextmanager
async def _get_redis_connection() -> AsyncGenerator[redis.Redis, None]:
    async with redis.Redis.from_url(Config.REDIS_URL) as r:
        yield r


async def subscribe_to_channel(channel_name: str, callback: Callable[[Any], Awaitable]):
    async with _get_redis_connection() as r:
        pubsub = r.pubsub()
        await pubsub.subscribe(channel_name)

        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    decoded_message = message['data']
                    msg = pickle.loads(decoded_message)
                    await callback(msg)
        except asyncio.CancelledError:
            logger.info("Subscriber task cancelled.")
        except KeyboardInterrupt:
            logger.info("Subscriber stopped by keyboard interrupt.")
        finally:
            await pubsub.unsubscribe(channel_name)
            logger.info(f"Unsubscribed from channel: '{channel_name}'")


@dataclass
class RedisCache:
    conn: redis.Redis

    @classmethod
    @asynccontextmanager
    async def create(cls) -> AsyncGenerator[Self, None]:
        async with redis.Redis.from_url(Config.REDIS_URL) as r:
            yield RedisCache(conn=r)

    async def get(self, key: str) -> Any:
        return await self.conn.get(key)
    
    async def set(self, key: str, value: EncodableT, ttl: int):
        return await self.conn.set(key, value, ex=ttl)
    
    async def delete(self, key: str):
        return await self.conn.delete(key)


def calculate_hash(file_path) -> str:
   sha256_hash = hashlib.sha256()
   with open(file_path, "rb") as file:
       while True:
           data = file.read(65536)  # Read the file in 64KB chunks.
           if not data:
               break
           sha256_hash.update(data)
   return sha256_hash.hexdigest()
