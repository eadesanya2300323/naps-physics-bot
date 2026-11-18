from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import texts
from app.keyboards import PAGE_SIZE, inbox_detail_keyboard, inbox_keyboard
from app.services import audit, catalog, materials
from app.services import feedback as store
from app.services.feedback import KINDS, STATUSES, clean_body
from app.services.permissions import can
from app.services.telegram import acknowledge, edit_message

router = Router(name="feedback")


class FeedbackFlow(StatesGroup):
    body = State()


def muted(student: dict) -> bool:
    until = student.get("muted_until")
    return until is not None and until > datetime.now(UTC)


async def show_inbox(target: Message, db, page: int, replace: bool) -> None:
    entries, total, new_count = await store.page(db, (page - 1) * PAGE_SIZE, PAGE_SIZE)
    pages = catalog.page_count(total)
    body = texts.inbox_header(new_count, total, page, pages)
    markup = inbox_keyboard(entries, page, pages) if total else None
    if replace:
        await edit_message(target, body, markup)
    else:
        await target.answer(body, reply_markup=markup)


@router.message(Command("feedback"))
async def feedback_command(message: Message, student: dict) -> None:
    if muted(student):
        await message.answer(texts.muted_notice())
        return
    await message.answer(texts.feedback_kind_prompt(), reply_markup=feedback_kind_keyboard())


@router.callback_query(F.data.startswith("fbk:"))
async def choose_kind(callback: CallbackQuery, state: FSMContext, student: dict) -> None:
    kind = callback.data.split(":")[1]
    if kind not in KINDS:
        await acknowledge(callback)
        return
    await acknowledge(callback)
    if muted(student):
        await callback.message.answer(texts.muted_notice())
        return
    await state.set_state(FeedbackFlow.body)
    await state.update_data(kind=kind, material_id=None)
    await edit_message(callback.message, texts.feedback_body_prompt(kind))


@router.callback_query(F.data.startswith("report:"))
async def report_material(callback: CallbackQuery, state: FSMContext, student: dict, db) -> None:
    try:
        material_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await acknowledge(callback)
        return
    await acknowledge(callback)
    if muted(student):
        await callback.message.answer(texts.muted_notice())
        return
    material = await catalog.material(db, material_id)
    if material is None:
        await callback.message.answer(texts.material_removed_missing())
        return
    await state.set_state(FeedbackFlow.body)
    await state.update_data(kind="report", material_id=material_id)
    await callback.message.answer(texts.feedback_report_prompt(material["title"]))


@router.message(FeedbackFlow.body, F.text, ~F.text.startswith("/"))
async def save_feedback(message: Message, state: FSMContext, student: dict, db) -> None:
    data = await state.get_data()
    kind = data.get("kind")
    if kind not in KINDS:
        await state.clear()
        return
    try:
        body = clean_body(message.text)
    except ValueError as error:
        await message.answer(str(error))
        return
    await store.create(db, student["id"], kind, body, data.get("material_id"))
    await state.clear()
    await message.answer(texts.feedback_thanks())


@router.message(Command("inbox"))
async def inbox_command(message: Message, db, admin_role: str | None) -> None:
    if not can(admin_role, "moderation"):
        await message.answer(texts.admin_only())
        return
    await show_inbox(message, db, 1, False)


@router.callback_query(F.data.startswith("inbox:"))
async def inbox_page(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "moderation"):
        await acknowledge(callback)
        return
    page = int(callback.data.split(":")[1])
    await acknowledge(callback)
    await show_inbox(callback.message, db, page, True)


@router.callback_query(F.data.startswith("fb:"))
async def inbox_detail(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "moderation"):
        await acknowledge(callback)
        return
    entry = await store.one(db, int(callback.data.split(":")[1]))
    await acknowledge(callback)
    if entry is None:
        await edit_message(callback.message, texts.inbox_header(0, 0, 1, 1))
        return
    await edit_message(callback.message, texts.inbox_item(entry), inbox_detail_keyboard(entry))


@router.callback_query(F.data.startswith("fbset:"))
async def set_status(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "moderation"):
        await acknowledge(callback)
        return
    _, identifier, status = callback.data.split(":")
    await acknowledge(callback)
    if status not in STATUSES:
        return
    await store.set_status(db, int(identifier), status)
    await audit.record(db, callback.from_user.id, "feedback.status", f"{identifier}:{status}")
    entry = await store.one(db, int(identifier))
    if entry is None:
        return
    await edit_message(callback.message, texts.inbox_item(entry), inbox_detail_keyboard(entry))


@router.callback_query(F.data.startswith("fbfile:"))
async def remove_reported_file(callback: CallbackQuery, db, bucket, admin_role: str | None) -> None:
    if not can(admin_role, "materials"):
        await acknowledge(callback)
        return
    feedback_id = int(callback.data.split(":")[1])
    await acknowledge(callback)
    material_id = await store.material_id_for(db, feedback_id)
    if material_id is None:
        await edit_message(callback.message, texts.material_removed_missing())
        return
    removed = await materials.remove(db, bucket, material_id)
    if removed is None:
        await edit_message(callback.message, texts.material_removed_missing())
        return
    await store.set_status(db, feedback_id, "resolved")
    await audit.record(db, callback.from_user.id, "material.remove", f"{material_id}:feedback{feedback_id}")
    await edit_message(callback.message, texts.file_removed(removed["title"]))
