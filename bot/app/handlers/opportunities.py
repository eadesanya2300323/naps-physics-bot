import re
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import texts
from app.keyboards import (
    PAGE_SIZE,
    home_keyboard,
    opportunity_detail_keyboard,
    opportunity_edit_keyboard,
    opportunity_kind_keyboard,
    opportunity_list_keyboard,
    opportunity_notify_keyboard,
    skip_keyboard,
)
from app.services import audit, catalog, jobs
from app.services import opportunities as store
from app.services.opportunities import (
    EDITABLE_FIELDS,
    KINDS,
    parse_deadline,
    parse_levels,
    parse_url,
)
from app.services.permissions import can
from app.services.telegram import acknowledge, edit_message, run_in_background

router = Router(name="opportunities")

STEPS = ("title", "organisation", "deadline", "levels", "url", "description")
NEXT_STEP = {
    "title": "organisation",
    "organisation": "deadline",
    "deadline": "levels",
    "levels": "url",
    "url": "description",
    "description": None,
}
PROMPTS = {
    "title": texts.opportunity_title_prompt,
    "organisation": texts.opportunity_organisation_prompt,
    "deadline": texts.opportunity_deadline_prompt,
    "levels": texts.opportunity_levels_prompt,
    "url": texts.opportunity_url_prompt,
    "description": texts.opportunity_description_prompt,
}
FIELD_LABELS = {
    "title": "Title",
    "organisation": "Organisation",
    "deadline": "Deadline",
    "levels": "Levels",
    "url": "Link",
    "description": "Description",
}


class OpportunityFlow(StatesGroup):
    value = State()


class OpportunityEdit(StatesGroup):
    value = State()


async def ask(target: Message, state: FSMContext, step: str) -> None:
    await state.update_data(step=step)
    if step == "title":
        await target.answer(PROMPTS[step]())
        return
    await target.answer(PROMPTS[step](), reply_markup=skip_keyboard("opskip"))


def parse_value(step: str, raw: str):
    text = re.sub(r"\s+", " ", raw).strip()
    if step == "title":
        if not 2 <= len(text) <= 120:
            raise ValueError("The title must be between 2 and 120 characters.")
        return text
    if step == "organisation":
        if len(text) > 120:
            raise ValueError("Keep the organisation under 120 characters.")
        return text or None
    if step == "deadline":
        return parse_deadline(text)
    if step == "levels":
        return parse_levels(text)
    if step == "url":
        return parse_url(text)
    if len(text) > 800:
        raise ValueError("Keep the description under 800 characters.")
    return text or None


async def finish(message: Message, state: FSMContext, db, actor: int) -> None:
    data = await state.get_data()
    if not data.get("title") or data.get("kind") not in KINDS:
        await state.clear()
        await message.answer(texts.opportunity_kind_prompt(), reply_markup=opportunity_kind_keyboard())
        return
    identifier = await store.create(
        db,
        data["kind"],
        data["title"],
        data.get("organisation"),
        data.get("deadline"),
        data.get("levels"),
        data.get("url"),
        data.get("description"),
        actor,
    )
    await audit.record(db, actor, "opportunity.create", str(identifier))
    await state.clear()
    await message.answer(texts.opportunity_saved(identifier), reply_markup=opportunity_notify_keyboard(identifier))


async def show_list(target: Message, db, kind: str | None, page: int, replace: bool) -> None:
    rows, total = await store.page(db, kind, (page - 1) * PAGE_SIZE, PAGE_SIZE)
    pages = catalog.page_count(total)
    body = texts.opportunity_header(kind, total, page, pages)
    markup = opportunity_list_keyboard(rows, page, pages, kind)
    if replace:
        await edit_message(target, body, markup)
    else:
        await target.answer(body, reply_markup=markup)


async def show_detail(target: Message, db, identifier: int, role: str | None, replace: bool) -> None:
    opportunity = await store.one(db, identifier)
    if opportunity is None:
        await target.answer(texts.opportunity_missing())
        return
    body = texts.opportunity_body(opportunity, date.today())
    markup = opportunity_detail_keyboard(opportunity, can(role, "opportunities"))
    if replace:
        await edit_message(target, body, markup)
    else:
        await target.answer(body, reply_markup=markup)


@router.message(Command("opportunities"))
async def list_opportunities(message: Message, db) -> None:
    await show_list(message, db, None, 1, False)


@router.callback_query(F.data.startswith("opps:"))
async def list_by_kind(callback: CallbackQuery, db) -> None:
    parts = callback.data.split(":")
    kind = None if parts[1] == "all" else parts[1]
    page = int(parts[2])
    await acknowledge(callback)
    if kind is not None and kind not in KINDS:
        return
    await show_list(callback.message, db, kind, page, True)


@router.callback_query(F.data.startswith("opp:"))
async def detail(callback: CallbackQuery, db, admin_role: str | None) -> None:
    identifier = int(callback.data.split(":")[1])
    await acknowledge(callback)
    await show_detail(callback.message, db, identifier, admin_role, True)


@router.message(Command("addopportunity"))
async def add_opportunity(message: Message, state: FSMContext, admin_role: str | None) -> None:
    if not can(admin_role, "opportunities"):
        await message.answer(texts.admin_only())
        return
    await state.clear()
    await state.set_state(OpportunityFlow.value)
    await state.update_data(step="kind")
    await message.answer(texts.opportunity_kind_prompt(), reply_markup=opportunity_kind_keyboard())


@router.callback_query(F.data.startswith("ochoose:"))
async def choose_kind(callback: CallbackQuery, state: FSMContext, admin_role: str | None) -> None:
    if not can(admin_role, "opportunities"):
        await acknowledge(callback)
        return
    kind = callback.data.split(":")[1]
    if kind not in KINDS:
        await acknowledge(callback)
        return
    await acknowledge(callback)
    await state.update_data(kind=kind)
    await state.set_state(OpportunityFlow.value)
    await ask(callback.message, state, "title")


@router.message(OpportunityFlow.value, F.text, ~F.text.startswith("/"))
async def flow_text(message: Message, state: FSMContext, db, admin_role: str | None) -> None:
    if not can(admin_role, "opportunities"):
        await state.clear()
        return
    data = await state.get_data()
    step = data.get("step")
    if step not in STEPS:
        await state.clear()
        await message.answer(texts.opportunity_kind_prompt(), reply_markup=opportunity_kind_keyboard())
        return
    try:
        value = parse_value(step, message.text)
    except ValueError as error:
        await message.answer(str(error))
        return
    await state.update_data({step: value})
    following = NEXT_STEP[step]
    if following is None:
        await finish(message, state, db, message.from_user.id)
        return
    await ask(message, state, following)


@router.callback_query(F.data == "opskip")
async def skip_step(callback: CallbackQuery, state: FSMContext, db, admin_role: str | None) -> None:
    if not can(admin_role, "opportunities"):
        await acknowledge(callback)
        return
    data = await state.get_data()
    step = data.get("step")
    await acknowledge(callback)
    if step not in STEPS or step == "title":
        return
    await state.update_data({step: None})
    following = NEXT_STEP[step]
    if following is None:
        await finish(callback.message, state, db, callback.from_user.id)
        return
    await edit_message(callback.message, PROMPTS[following](), skip_keyboard("opskip"))


@router.callback_query(F.data.startswith("oppedit:"))
async def edit_menu(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "opportunities"):
        await acknowledge(callback)
        return
    opportunity = await store.one(db, int(callback.data.split(":")[1]))
    await acknowledge(callback)
    if opportunity is None:
        await edit_message(callback.message, texts.opportunity_missing())
        return
    await edit_message(callback.message, texts.opportunity_body(opportunity, date.today()), opportunity_edit_keyboard(opportunity))


@router.callback_query(F.data.startswith("oedit:"))
async def edit_field(callback: CallbackQuery, state: FSMContext, db, admin_role: str | None) -> None:
    if not can(admin_role, "opportunities"):
        await acknowledge(callback)
        return
    parts = callback.data.split(":")
    identifier = int(parts[1])
    field = parts[2]
    if field not in EDITABLE_FIELDS:
        await acknowledge(callback)
        return
    opportunity = await store.one(db, identifier)
    await acknowledge(callback)
    if opportunity is None:
        await edit_message(callback.message, texts.opportunity_missing())
        return
    current = opportunity[field]
    await state.set_state(OpportunityEdit.value)
    await state.update_data(identifier=identifier, field=field)
    shown = str(current) if current is not None else None
    await edit_message(callback.message, texts.opportunity_edit_prompt(FIELD_LABELS[field], shown))


@router.message(OpportunityEdit.value, F.text, ~F.text.startswith("/"))
async def save_edit(message: Message, state: FSMContext, db, admin_role: str | None) -> None:
    if not can(admin_role, "opportunities"):
        await state.clear()
        return
    data = await state.get_data()
    identifier = data.get("identifier")
    field = data.get("field")
    if identifier is None or field not in EDITABLE_FIELDS:
        await state.clear()
        return
    try:
        value = parse_value(field, message.text)
    except ValueError as error:
        await message.answer(str(error))
        return
    await store.update_field(db, identifier, field, value)
    await audit.record(db, message.from_user.id, "opportunity.update", f"{identifier}:{field}")
    await state.clear()
    await show_detail(message, db, identifier, admin_role, False)


@router.callback_query(F.data.startswith("oparchive:"))
async def archive(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "opportunities"):
        await acknowledge(callback)
        return
    identifier = int(callback.data.split(":")[1])
    await store.archive(db, identifier)
    await audit.record(db, callback.from_user.id, "opportunity.archive", str(identifier))
    await acknowledge(callback)
    await edit_message(callback.message, texts.opportunity_archived(), home_keyboard(admin_role))


@router.message(Command("delopportunity"))
async def delete_opportunity(message: Message, command: CommandObject, db, admin_role: str | None) -> None:
    if not can(admin_role, "opportunities"):
        await message.answer(texts.admin_only())
        return
    tokens = (command.args or "").split()
    if not tokens or not tokens[0].isdigit():
        await message.answer("Send /delopportunity <id>")
        return
    identifier = int(tokens[0])
    if await store.one(db, identifier) is None:
        await message.answer(texts.opportunity_missing())
        return
    await store.remove(db, identifier)
    await audit.record(db, message.from_user.id, "opportunity.delete", str(identifier))
    await message.answer(texts.opportunity_removed())


@router.callback_query(F.data.startswith("opush:"))
async def push_to_level(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "broadcasts"):
        await acknowledge(callback)
        return
    parts = callback.data.split(":")
    identifier = int(parts[1])
    level = parts[2]
    if level not in {"100", "200", "300", "400"}:
        await acknowledge(callback)
        return
    opportunity = await store.one(db, identifier)
    if opportunity is None:
        await acknowledge(callback)
        await edit_message(callback.message, texts.opportunity_missing())
        return
    await jobs.enqueue(db, "broadcast", "level", texts.opportunity_body(opportunity, date.today()), level)
    await audit.record(db, callback.from_user.id, "opportunity.push", f"{identifier}:{level}")
    await acknowledge(callback)
    run_in_background(jobs.process(db, callback.bot))
    await edit_message(callback.message, texts.opportunity_pushed(level), home_keyboard(admin_role))
