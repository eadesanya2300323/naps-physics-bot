import asyncio
from collections.abc import Awaitable

from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import CallbackQuery, Message

_background_tasks: set[asyncio.Task] = set()


def run_in_background(coro: Awaitable[None]) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def edit_message(message: Message, text: str, markup=None) -> None:
    try:
        await message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            return
        await message.answer(text, reply_markup=markup, disable_web_page_preview=True)


async def present(event, text: str, markup=None) -> None:
    if isinstance(event, CallbackQuery):
        await edit_message(event.message, text, markup)
    else:
        await event.answer(text, reply_markup=markup, disable_web_page_preview=True)


async def acknowledge(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass


async def send_document(bot, chat_id: int, document, caption: str, markup=None, attempts: int = 3):
    for _ in range(attempts):
        try:
            return await bot.send_document(chat_id, document=document, caption=caption, reply_markup=markup)
        except TelegramRetryAfter as error:
            await asyncio.sleep(error.retry_after)
        except TelegramForbiddenError:
            raise
    return None


async def send_text(bot, chat_id: int, text: str, markup=None, attempts: int = 3):
    for _ in range(attempts):
        try:
            return await bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True)
        except TelegramRetryAfter as error:
            await asyncio.sleep(error.retry_after)
        except TelegramForbiddenError:
            raise
    return None
