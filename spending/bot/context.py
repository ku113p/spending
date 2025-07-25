from langgraph.checkpoint.memory import BaseCheckpointSaver
from langgraph.store.memory import BaseStore
from telegram.ext import CallbackContext, ExtBot

import utils

logger = utils.create_logger(__name__)


class ChatData:
    redis_cache: utils.RedisCache
    graph_checkpointer: BaseCheckpointSaver
    graph_store: BaseStore


class CustomContext(CallbackContext[ExtBot, dict, ChatData, dict]):
    @property
    def redis_cache(self) -> utils.RedisCache:
        return self.chat_data.redis_cache

    @property
    def graph_checkpointer(self) -> BaseCheckpointSaver:
        return self.chat_data.graph_checkpointer

    @property
    def graph_store(self) -> BaseStore:
        return self.chat_data.graph_store
