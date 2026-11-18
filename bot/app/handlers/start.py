from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from app import texts
from app.keyboards import home_keyboard, level_keyboard
from app.services.permissions import is_admin
from app.services.telegram import acknowledge, edit_message

router = Router(name="start")


@router.message(CommandStart())
async def start(message: Message, student: dict) -> None:
    await message.answer(texts.welcome(), reply_markup=level_keyboard(student["level"]))


@router.message(Command("help"))
async def help_command(message: Message, admin_role: str | None) -> None:
    await message.answer(texts.help_text())
    if is_admin(admin_role):
        await message.answer(texts.admin_help_text(admin_role))


@router.callback_query(F.data == "home")
async def home(callback: CallbackQuery, student: dict, admin_role: str | None) -> None:
    await acknowledge(callback)
    await edit_message(
        callback.message,
        texts.home(),
        home_keyboard(admin_role, student["notify_uploads"]),
    )


@router.callback_query(F.data == "helptext")
async def help_callback(callback: CallbackQuery, student: dict, admin_role: str | None) -> None:
    await acknowledge(callback)
    await edit_message(
        callback.message,
        texts.help_text(),
        home_keyboard(admin_role, student["notify_uploads"]),
    )


@router.callback_query(F.data == "admhelp")
async def admin_help_callback(callback: CallbackQuery, student: dict, admin_role: str | None) -> None:
    await acknowledge(callback)
    body = texts.admin_help_text(admin_role) if is_admin(admin_role) else texts.help_text()
    await edit_message(
        callback.message,
        body,
        home_keyboard(admin_role, student["notify_uploads"]),
    )


@router.callback_query(F.data == "searchhelp")
async def search_help(callback: CallbackQuery, student: dict, admin_role: str | None) -> None:
    await acknowledge(callback)
    await edit_message(
        callback.message,
        texts.search_prompt(),
        home_keyboard(admin_role, student["notify_uploads"]),
    )


@router.callback_query(F.data == "uploadhelp")
async def upload_help(callback: CallbackQuery, student: dict, admin_role: str | None) -> None:
    await acknowledge(callback)
    if not is_admin(admin_role):
        return
    await edit_message(
        callback.message,
        texts.upload_prompt(),
        home_keyboard(admin_role, student["notify_uploads"]),
    )


@router.message(Command("notify"))
async def notify_command(message: Message, student: dict, db) -> None:
    enabled = not student["notify_uploads"]
    await db.execute("update students set notify_uploads = $2 where id = $1", student["id"], enabled)
    await message.answer(texts.notify_on() if enabled else texts.notify_off())


@router.callback_query(F.data == "ntf")
async def notify_callback(callback: CallbackQuery, student: dict, admin_role: str | None, db) -> None:
    enabled = not student["notify_uploads"]
    await db.execute("update students set notify_uploads = $2 where id = $1", student["id"], enabled)
    await callback.answer(texts.notify_on() if enabled else texts.notify_off())
    await edit_message(
        callback.message,
        texts.home(),
        home_keyboard(admin_role, enabled),
    )
