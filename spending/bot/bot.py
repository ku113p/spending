import asyncio
import re
from langgraph.checkpoint.memory import BaseCheckpointSaver, InMemorySaver
from langgraph.store.memory import BaseStore, InMemoryStore
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

import utils
from . import context, handlers

logger = utils.create_logger(__name__)


def _get_application(
    api_token: str,
    redis_cache: utils.RedisCache,
    graph_checkpointer: BaseCheckpointSaver,
    graph_store: BaseStore,
) -> Application:
    class _ChatData(context.ChatData):
        def __init__(self):
            super().__init__()
            self.redis_cache = redis_cache
            self.graph_checkpointer = graph_checkpointer
            self.graph_store = graph_store


    context_types = ContextTypes(context=context.CustomContext, chat_data=_ChatData)
    application = Application.builder().token(api_token).context_types(context_types).build()
    
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.start))
    application.add_handler(CommandHandler("receipts", handlers.receipts))
    application.add_handler(CommandHandler("export", handlers.export))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handlers.image))
    application.add_handler(MessageHandler(filters.PHOTO, handlers.photo))
    application.add_handler(CallbackQueryHandler(handlers.already_exists_callback_query, handlers.ON_EXISTS_PATTERN))
    application.add_handler(CallbackQueryHandler(handlers.receipts_page_callaback_query, handlers.RECEIPTS_PAGE_PATTERN))
    application.add_handler(CallbackQueryHandler(handlers.view_receipt_callback_query, pattern=handlers.VIEW_RECEIPT_PATTERN))
    application.add_handler(CallbackQueryHandler(handlers.delete_receipt_callback_query, pattern=handlers.DELETE_RECEIPT_PATTERN))
    application.add_handler(MessageHandler(filters.TEXT, handlers.text))
    
    return application


async def run_bot(api_token: str):
    graph_checkpointer = InMemorySaver()
    graph_store = InMemoryStore()
    async with utils.RedisCache.create() as redis_cache:
        application = _get_application(api_token, redis_cache, graph_checkpointer, graph_store)

        async with application:
            await application.start()
            await application.updater.start_polling()

            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                logger.info("Event loop cancelled, preparing for shutdown.")

            await application.updater.stop()
            await application.stop()
