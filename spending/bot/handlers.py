import os
import pickle
import tempfile
from typing import Any
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot

import utils
from .context import CustomContext
from graphs.agents.schemas import ReceiptBase
from graphs.pipelines.full_pipeline import FullPipelineController, FullPipelineParams, FullPipelineResponse, InterruptType, OnExistsChoice

logger = utils.create_logger(__name__)

WELCOME_TEXT = "send invoice image or photo to start processing"


async def start(update: Update, context: CustomContext):
    await update.message.reply_text(WELCOME_TEXT)


async def image(update: Update, context: CustomContext):
    file_id = update.message.document.file_id
    await run_photo_pipeline(update.message.chat.id, file_id, context)


async def photo(update: Update, context: CustomContext):
    file_id = update.message.photo[-1].file_id
    await run_photo_pipeline(update.message.chat.id, file_id, context)


async def text(update: Update, context: CustomContext):
    config_bytes = await context.redis_cache.get(update.message.chat.id)
    if config_bytes is None:
        await update.message.reply_text("No image processing in progress.")
        return
    config = pickle.loads(config_bytes)

    await run_controller_pipeline(update.message.chat.id, update.message.text, config['task_id'], config['image_fp'], context)


async def callback_query(update: Update, context: CustomContext):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    data = query.data

    config_bytes = await context.redis_cache.get(chat_id)
    if config_bytes is None:
        await processing_error(context.bot, chat_id, Exception("No config found"))
        return
    config = pickle.loads(config_bytes)

    try:
        choice = OnExistsChoice(data)
    except ValueError:
        logger.error(f"Invalid callback data: {data}")
        await processing_error(context.bot, chat_id, Exception("Invalid callback data"))
        return

    await run_controller_pipeline(chat_id, choice, config['task_id'], config['image_fp'], context)


async def run_controller_pipeline(chat_id: str | int, input: Any, task_id: uuid.UUID, image_fp: str, context: CustomContext):
    params = FullPipelineParams(
        task_id=task_id,
        image_fp=image_fp,
        checkpointer=context.graph_checkpointer,
        store=context.graph_store,
    )
    controller = FullPipelineController(params=params)
    if isinstance(input, OnExistsChoice):
        response = await controller.on_exists_answer(input)
    else:
        response = await controller.on_review(input)

    await process_controller_response(chat_id, response, context)


async def run_photo_pipeline(chat_id: str | int, file_id: str, context: CustomContext):
    file = await context.bot.get_file(file_id)
    task_id = uuid.uuid4()

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        file_path = temp_file.name
        await file.download_to_drive(file_path)

        config = {"task_id": task_id, "image_fp": file_path}
        await context.redis_cache.set(
            chat_id,
            value=pickle.dumps(config),
            ttl=utils.Config.REDIS_CACHE_CONFIG_TTL
        )
        
        params = FullPipelineParams(
            task_id=task_id,
            image_fp=file_path,
            checkpointer=context.graph_checkpointer,
            store=context.graph_store,
        )
        controller = FullPipelineController(params=params)
        response = await controller.start()

        await process_controller_response(chat_id, response, context)


async def process_controller_response(chat_id: str | int, response: FullPipelineResponse, context: CustomContext):
    if response.interrupt_info is None:
        await processing_finished(context.bot, chat_id)
        await context.redis_cache.delete(chat_id)
        os.remove(response.state['image_fp'])
        return

    interrupt_info = response.interrupt_info
    receipt = interrupt_info.receipt

    if interrupt_info.type == InterruptType.ALREADY_EXISTS:
        await on_exists_ask(context.bot, chat_id)
    elif interrupt_info.type == InterruptType.IS_IT_OK:
        await review_ask(context.bot, chat_id, receipt)
    else:
        logger.error(f"Unknown interrupt type: {interrupt_info.type}")
        await processing_error(context.bot, chat_id, Exception("Unknown interrupt type"))


def get_on_exists_data(choice: OnExistsChoice) -> tuple[str, str]:
    mapping = {
        OnExistsChoice.REWRITE: "Rewrite",
        OnExistsChoice.CORRECT: "Review",
        OnExistsChoice.FINISH: "Cancel",
    }

    return mapping[choice], choice.value


async def on_exists_ask(bot: Bot, chat_id: int | str):
    keyboard = []
    for choice in OnExistsChoice:
        text, callback_data = get_on_exists_data(choice)
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(chat_id=chat_id, text="what to do with already exists document", reply_markup=reply_markup)


async def review_ask(bot: Bot, chat_id: int | str, receipt: ReceiptBase):
    products_text = "\n".join(
        f"{product.name.normalized} - {product.quantity} - {product.price}"
        for product in receipt.products
    )

    text = (
        f"Is receipt data correct?\n"
        f"Shop: {receipt.shop.name.raw}\n"
        f"Total: {receipt.total}\n"
        f"Products:\n{products_text}\n"
        f"Created at: {receipt.created_at.isoformat()}\n\n"
        f"Reply with 'correct' to confirm, or specify what to change."
    )

    await bot.send_message(chat_id=chat_id, text=text)


async def processing_finished(bot: Bot, chat_id: int | str):
    text = f"Processing finished. You can now view the receipt in your history."
    await bot.send_message(chat_id=chat_id, text=text)


async def processing_error(bot: Bot, chat_id: int | str, error: Exception):
    text = f"An error occurred during processing: {str(error)}"
    await bot.send_message(chat_id=chat_id, text=text)
