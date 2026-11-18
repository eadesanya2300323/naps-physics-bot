from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from app import texts
from app.keyboards import search_keyboard
from app.services import catalog
from app.services.keywords import sanitise
from app.services.telegram import acknowledge, edit_message

router = Router(name="search")


def results_markup(rows, page: int, pages: int, keyword: str):
    return search_keyboard(rows, page, pages, keyword) if rows else None


@router.message(Command("search"))
async def search_command(message: Message, command: CommandObject, db) -> None:
    keyword = sanitise(command.args)
    if not keyword:
        await message.answer(texts.search_prompt_short())
        return
    rows, total, pages = await catalog.search(db, keyword, 1)
    await message.answer(
        texts.search_results(keyword, total, 1, pages),
        reply_markup=results_markup(rows, 1, pages, keyword),
    )


@router.callback_query(F.data.startswith("sr:"))
async def search_page(callback: CallbackQuery, db) -> None:
    head, _, tail = callback.data.rpartition(":")
    keyword = head[3:]
    page = int(tail)
    await acknowledge(callback)
    rows, total, pages = await catalog.search(db, keyword, page)
    await edit_message(
        callback.message,
        texts.search_results(keyword, total, page, pages),
        results_markup(rows, page, pages, keyword),
    )
