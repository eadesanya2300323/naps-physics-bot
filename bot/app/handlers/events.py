from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app import texts
from app.keyboards import events_keyboard
from app.services import audit
from app.services import events as store
from app.services.permissions import can
from app.services.telegram import acknowledge, edit_message

router = Router(name="events")


async def show_events(target: Message, db, role: str | None, active: bool, replace: bool) -> None:
    rows = await store.listing(db, active)
    body = texts.events_header(active, len(rows))
    if rows:
        body = f"{body}\n\n" + "\n\n".join(texts.event_line(row) for row in rows)
    markup = events_keyboard(rows, can(role, "events"), active)
    if replace:
        await edit_message(target, body, markup)
    else:
        await target.answer(body, reply_markup=markup)


@router.message(Command("events"))
async def events_command(message: Message, db, admin_role: str | None) -> None:
    await show_events(message, db, admin_role, True, False)


@router.callback_query(F.data == "events")
async def active_links(callback: CallbackQuery, db, admin_role: str | None) -> None:
    await acknowledge(callback)
    await show_events(callback.message, db, admin_role, True, True)


@router.callback_query(F.data == "evin")
async def inactive_links(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "events"):
        await acknowledge(callback)
        return
    await acknowledge(callback)
    await show_events(callback.message, db, admin_role, False, True)


@router.callback_query(F.data.startswith("evoff:"))
async def switch_off(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "events"):
        await acknowledge(callback)
        return
    identifier = int(callback.data.split(":")[1])
    await acknowledge(callback)
    await store.set_active(db, identifier, False)
    await audit.record(db, callback.from_user.id, "event.off", str(identifier))
    await show_events(callback.message, db, admin_role, True, True)


@router.callback_query(F.data.startswith("evon:"))
async def switch_on(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "events"):
        await acknowledge(callback)
        return
    identifier = int(callback.data.split(":")[1])
    await acknowledge(callback)
    await store.set_active(db, identifier, True)
    await audit.record(db, callback.from_user.id, "event.on", str(identifier))
    await show_events(callback.message, db, admin_role, False, True)
