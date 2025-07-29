from dataclasses import dataclass
import math
import os
import pickle
import re
import tempfile
from typing import Any, AsyncGenerator
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot

import db, utils
from .context import CustomContext
from graphs.agents.schemas import NormalizedReceipt, ReceiptBase
from graphs.pipelines.full_pipeline import FullPipelineController, FullPipelineParams, FullPipelineResponse, InterruptType, OnExistsChoice

logger = utils.create_logger(__name__)

WELCOME_TEXT = "send invoice image or photo to start processing"
RECEIPTS_PER_PAGE = 2
ON_EXISTS_CB_PREFIX = "on_exists"
ON_EXISTS_PATTERN = re.compile(rf"^{ON_EXISTS_CB_PREFIX}_(.+)")
PAGE_CB_PREFIX = "page"
RECEIPTS_PAGE_PATTERN = re.compile(rf"^{PAGE_CB_PREFIX}_(.+)")
VIEW_RECEIPT_CB_PREFIX = "view_receipt"
VIEW_RECEIPT_PATTERN = re.compile(rf"^{VIEW_RECEIPT_CB_PREFIX}_(\d+)")
DELETE_RECEIPT_CB_PREFIX = "delete_receipt"
DELETE_RECEIPT_PATTERN = re.compile(rf"^{DELETE_RECEIPT_CB_PREFIX}_(\d+)")


async def start(update: Update, context: CustomContext):
    await update.message.reply_text(WELCOME_TEXT)


async def receipts(update: Update, context: CustomContext):
    text, keyboard = await list_receipts(0)
    await update.message.reply_text(text, reply_markup=keyboard)


async def receipts_page_callaback_query(update: Update, context: CustomContext):
    query = update.callback_query
    await query.answer()

    page: int = int(get_cb_data(query.data, RECEIPTS_PAGE_PATTERN))

    text, keyboard = await list_receipts(page)
    await update.effective_message.edit_text(text, reply_markup=keyboard)


def get_cb_data(data: str, pattern: str) -> str:
    return next(iter(re.match(pattern, data).groups()))


def build_receipt_buttons(receipts: list[ReceiptBase], page: int, total_count: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i in range(len(receipts)):
        index = i + page * RECEIPTS_PER_PAGE
        row.append(InlineKeyboardButton(f"📄 {index + 1}", callback_data=f"{VIEW_RECEIPT_CB_PREFIX}_{index}"))
        if (i + 1) % 3 == 0 or i == len(receipts) - 1:
            buttons.append(row)
            row = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{PAGE_CB_PREFIX}_{page - 1}"))
    else:
        nav.append(InlineKeyboardButton(" ", callback_data="blank"))
    nav.append(InlineKeyboardButton(f"page #{page + 1}", callback_data="blank"))
    if (page + 1) * RECEIPTS_PER_PAGE < total_count:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"{PAGE_CB_PREFIX}_{page + 1}"))
    else:
        nav.append(InlineKeyboardButton(" ", callback_data="blank"))
    buttons.append(nav)
    return InlineKeyboardMarkup(buttons)


def format_receipts_page(receipts: list[ReceiptBase], page: int, total_pages: int) -> str:
    lines = [f"Page {page + 1} of {total_pages}\n"]
    for idx, r in enumerate(receipts, start=1):
        index = idx + page * RECEIPTS_PER_PAGE
        line1 = f"{index}. ${r.total:.2f}"
        if r.shop.name.normalized:
            line1 += f" · {r.shop.name.normalized}"
        line2 = r.created_at.strftime("%b %d, %H:%M")
        lines.append(line1)
        lines.append(f"      {line2}")
        lines.append("")  # Blank line between items
    return "\n".join(lines).strip()


async def list_receipts(page: int) -> tuple[str, InlineKeyboardMarkup]:
    receipts_filter = {}
    receipts_counter: int = await db.run_operation(
        db.DbOperation.mongo(op=db.OperationType.COUNT),
        {"filter": receipts_filter}
    )
    total_pages: int = math.ceil(receipts_counter / RECEIPTS_PER_PAGE)
    if page < 0:
        page = 0
    elif page >= total_pages:
        page = total_pages - 1 if total_pages > 0 else 0
    first_page_raw_receipts: AsyncGenerator[dict, None] = await db.run_operation(
        db.DbOperation.mongo(op=db.OperationType.LIST),
        {
            "filter": receipts_filter,
            "limit": RECEIPTS_PER_PAGE,
            "sort": [("receipt.created_at", -1)],
            "skip": page * RECEIPTS_PER_PAGE,
        }
    )
    normalized_receipts: list[NormalizedReceipt] = []
    async for db_object in first_page_raw_receipts:
        normalized_receipts.append(NormalizedReceipt.from_raw_mongo(db_object))
    receipts = list(map(ReceiptBase.from_normalized, normalized_receipts))

    text = format_receipts_page(receipts, page, total_pages)
    keyboard = build_receipt_buttons(receipts, page, receipts_counter)

    return text, keyboard


async def view_receipt_callback_query(update: Update, context: CustomContext):
    query = update.callback_query
    await query.answer()

    by_idx_cb_data = ByIndexCallbackData(query.data, VIEW_RECEIPT_PATTERN)
    index = by_idx_cb_data.index
    from_page = by_idx_cb_data.page

    raw = await db.run_operation(
        db.DbOperation.mongo(op=db.OperationType.LIST),
        {
            "filter": {},
            "limit": 1,
            "skip": index,
            "sort": [("receipt.created_at", -1)]
        }
    )

    try:
        db_object = await anext(raw)
    except StopAsyncIteration:
        await query.message.reply_text("Receipt not found.")
        return

    normalized = NormalizedReceipt.from_raw_mongo(db_object)
    receipt = ReceiptBase.from_normalized(normalized)

    text = get_base_receipt_text(receipt)
    buttons = [
        [InlineKeyboardButton("Delete", callback_data=f"{DELETE_RECEIPT_CB_PREFIX}_{index}")],
        [get_back_button(from_page)],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.effective_message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")


@dataclass
class ByIndexCallbackData:
    callback_data: str
    pattern: str

    @property
    def index(self) -> int:
        return int(get_cb_data(self.callback_data, self.pattern))
    
    @property
    def page(self) -> int:
        return math.ceil((self.index + 1) / RECEIPTS_PER_PAGE) - 1


def get_back_button(page: int) -> InlineKeyboardButton:
    return InlineKeyboardButton("⬅️ Back", callback_data=f"{PAGE_CB_PREFIX}_{page}")


async def delete_receipt_callback_query(update: Update, context: CustomContext):
    query = update.callback_query
    await query.answer()

    by_idx_cb_data = ByIndexCallbackData(query.data, DELETE_RECEIPT_PATTERN)
    index = by_idx_cb_data.index
    from_page = by_idx_cb_data.page

    delete_count: int = await db.run_operation(
        db.DbOperation.mongo(op=db.OperationType.DELETE),
        {
            "filter": {},
            "limit": 1,
            "skip": index,
            "sort": [("receipt.created_at", -1)]
        }
    )

    text = "Deleted" if delete_count > 0 else "Not exists"
    keyboard = InlineKeyboardMarkup([[get_back_button(from_page)]])

    await update.effective_message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")


def get_base_receipt_text(receipt: ReceiptBase) -> str:
    products_text = "\n".join(
        f"{p.name.normalized} — ${p.price:.2f}" for p in receipt.products
    )
    shop_name = receipt.shop.name.normalized
    created = receipt.created_at.strftime("%Y-%m-%d %H:%M")

    return (
        f"🧾 *Receipt Details*\n"
        f"*Shop:* {shop_name}\n"
        f"*Total:* ${receipt.total:.2f}\n"
        f"*Created:* {created}\n"
        f"*Products:*\n{products_text}"
    )


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


async def already_exists_callback_query(update: Update, context: CustomContext):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    choice_text: str = get_cb_data(query.data, ON_EXISTS_PATTERN)

    config_bytes = await context.redis_cache.get(chat_id)
    if config_bytes is None:
        await processing_error(context.bot, chat_id, Exception("No config found"))
        return
    config = pickle.loads(config_bytes)

    try:
        choice = OnExistsChoice(choice_text)
    except ValueError:
        logger.error(f"Invalid callback data: {choice_text}")
        await processing_error(context.bot, chat_id, Exception("Invalid callback data"))
        return

    image_fp: str = config['image_fp']
    await run_controller_pipeline(chat_id, choice, config['task_id'], image_fp, context)
    if os.path.exists(image_fp):
        os.remove(image_fp)


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


on_exists_mapping = {
    OnExistsChoice.REWRITE: "Rewrite",
    OnExistsChoice.CORRECT: "Review",
    OnExistsChoice.FINISH: "Left",
}


async def on_exists_ask(bot: Bot, chat_id: int | str):
    keyboard = []
    for choice in OnExistsChoice:
        text = on_exists_mapping[choice]
        callback_data = "_".join([ON_EXISTS_CB_PREFIX, choice.value])
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(chat_id=chat_id, text="what to do with already exists document", reply_markup=reply_markup)


async def review_ask(bot: Bot, chat_id: int | str, receipt: ReceiptBase):
    text = get_base_receipt_text(receipt)
    text += "\n\nReply with 'correct' to confirm, or specify what to change."

    await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")


async def processing_finished(bot: Bot, chat_id: int | str):
    text = f"Processing finished. You can now view the receipt in your history."
    await bot.send_message(chat_id=chat_id, text=text)


async def processing_error(bot: Bot, chat_id: int | str, error: Exception):
    text = f"An error occurred during processing: {str(error)}"
    await bot.send_message(chat_id=chat_id, text=text)
