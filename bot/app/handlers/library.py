import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from app import texts
from app.keyboards import LEVELS, pack_confirm_keyboard, pack_level_keyboard, saved_keyboard, templates_keyboard
from app.services import catalog
from app.services.materials import deliver
from app.services.pack import pack_batches, pack_total
from app.services.telegram import acknowledge, edit_message, run_in_background
from app.services.materials import deliver

router = Router(name="library")
logger = logging.getLogger("naps.library")

PACK_PAUSE = 1.1


async def send_pack(bot, db, bucket, settings, chat_id: int, materials, progress: Message, student_id: str) -> None:
    sent = 0
    total = pack_total(materials)
    try:
        for batch in pack_batches(materials):
            for material in batch:
                await deliver(bot, db, bucket, settings, chat_id, dict(material), student_id)
                sent += 1
                await asyncio.sleep(PACK_PAUSE)
            await edit_message(progress, texts.pack_progress(sent, total))
    except Exception:
        logger.exception("Pack stopped after %s files", sent)
        await edit_message(progress, texts.pack_failed())
        return
    await edit_message(progress, texts.pack_done(sent))


@router.message(Command("library"))
async def library_command(message: Message, student: dict, db) -> None:
    rows, total, pages = await catalog.favourites(db, student["id"], 1)
    await message.answer(
        texts.library_header(total, 1, pages),
        reply_markup=saved_keyboard(rows, 1, pages, "lib") if total else None,
    )


@router.callback_query(F.data.startswith("lib:"))
async def library_page(callback: CallbackQuery, student: dict, db) -> None:
    page = int(callback.data.split(":")[1])
    await acknowledge(callback)
    rows, total, pages = await catalog.favourites(db, student["id"], page)
    await edit_message(
        callback.message,
        texts.library_header(total, page, pages),
        saved_keyboard(rows, page, pages, "lib") if total else None,
    )


@router.message(Command("recent"))
async def recent_command(message: Message, student: dict, db) -> None:
    rows, total, pages = await catalog.recent(db, student["id"], 1)
    await message.answer(
        texts.recent_header(total, 1, pages),
        reply_markup=saved_keyboard(rows, 1, pages, "rec") if total else None,
    )


@router.callback_query(F.data.startswith("rec:"))
async def recent_page(callback: CallbackQuery, student: dict, db) -> None:
    page = int(callback.data.split(":")[1])
    await acknowledge(callback)
    rows, total, pages = await catalog.recent(db, student["id"], page)
    await edit_message(
        callback.message,
        texts.recent_header(total, page, pages),
        saved_keyboard(rows, page, pages, "rec") if total else None,
    )


async def show_pack(target: Message, db, level: str, replace: bool) -> None:
    materials = await catalog.key_materials(db, level)
    body = texts.pack_confirm(level, pack_total(materials))
    markup = pack_confirm_keyboard(level, pack_total(materials))
    if replace:
        await edit_message(target, body, markup)
    else:
        await target.answer(body, reply_markup=markup)


@router.message(Command("pack"))
async def pack_command(message: Message, command: CommandObject, db) -> None:
    tokens = (command.args or "").split()
    if not tokens:
        await message.answer(texts.pack_prompt(), reply_markup=pack_level_keyboard())
        return
    level = tokens[0].lower().removesuffix("l")
    if level not in LEVELS:
        await message.answer(texts.pack_prompt(), reply_markup=pack_level_keyboard())
        return
    await show_pack(message, db, level, False)


@router.callback_query(F.data == "pack")
async def pack_menu(callback: CallbackQuery) -> None:
    await acknowledge(callback)
    await edit_message(callback.message, texts.pack_prompt(), pack_level_keyboard())


@router.callback_query(F.data.startswith("pkl:"))
async def pack_level(callback: CallbackQuery, db) -> None:
    level = callback.data.split(":")[1]
    await acknowledge(callback)
    if level not in LEVELS:
        return
    await show_pack(callback.message, db, level, True)


@router.callback_query(F.data.startswith("pkgo:"))
async def pack_start(callback: CallbackQuery, student: dict, db, bucket, settings) -> None:
    level = callback.data.split(":")[1]
    await acknowledge(callback)
    if level not in LEVELS:
        return
    materials = await catalog.key_materials(db, level)
    if not materials:
        await edit_message(callback.message, texts.pack_confirm(level, 0), pack_confirm_keyboard(level, 0))
        return
    progress = await callback.message.answer(texts.pack_progress(0, pack_total(materials)))
    run_in_background(
        send_pack(callback.bot, db, bucket, settings, callback.message.chat.id, materials, progress, student["id"])
    )


@router.message(Command("templates"))
async def templates_command(message: Message, db) -> None:
    rows, total, pages = await catalog.templates(db, 1)
    await message.answer(
        texts.template_header(total, 1, pages),
        reply_markup=templates_keyboard(rows, 1, pages) if total else None,
    )


@router.callback_query(F.data.startswith("tpl:"))
async def templates_page(callback: CallbackQuery, db) -> None:
    page = int(callback.data.split(":")[1])
    await acknowledge(callback)
    rows, total, pages = await catalog.templates(db, page)
    await edit_message(
        callback.message,
        texts.template_header(total, page, pages),
        templates_keyboard(rows, page, pages) if total else None,
    )
