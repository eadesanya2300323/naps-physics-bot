from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from app import texts
from app.keyboards import PAGE_SIZE, fyp_choice_keyboard, fyp_detail_keyboard, fyp_list_keyboard, fyp_menu_keyboard
from app.services import audit, catalog
from app.services import fyp as store
from app.services.fyp import STATUSES, status_label
from app.services.keywords import sanitise
from app.services.permissions import can
from app.services.telegram import acknowledge, edit_message

router = Router(name="fyp")


def index_value(values, index: int):
    if 0 <= index < len(values):
        return values[index]
    return None


async def show_listing(
    target: Message,
    db,
    status: str,
    supervisor_index: int,
    area_index: int,
    year_index: int,
    page: int,
    replace: bool,
) -> None:
    supervisors = await store.supervisors(db, status)
    areas = await store.areas(db, status)
    years = await store.years(db, status)
    supervisor = index_value(supervisors, supervisor_index)
    area = index_value(areas, area_index)
    year = index_value(years, year_index)

    rows, total = await store.page(
        db,
        status,
        supervisor,
        area,
        year,
        None,
        (page - 1) * PAGE_SIZE,
        PAGE_SIZE,
    )
    pages = catalog.page_count(total)
    filters = " · ".join(
        part for part in (supervisor, area, str(year) if year else None) if part
    )
    body = texts.fyp_header(status, total, page, pages, filters)
    prefix = f"fyp:{status}:{supervisor_index}:{area_index}:{year_index}"
    markup = fyp_list_keyboard(rows, page, pages, prefix) if total else fyp_menu_keyboard()
    if replace:
        await edit_message(target, body, markup)
    else:
        await target.answer(body, reply_markup=markup)


async def show_search(target: Message, db, keyword: str, page: int, replace: bool) -> None:
    rows, total = await store.page(db, "available", None, None, None, keyword, (page - 1) * PAGE_SIZE, PAGE_SIZE)
    pages = catalog.page_count(total)
    body = texts.fyp_header("available", total, page, pages, f"Search: {keyword}")
    markup = fyp_list_keyboard(rows, page, pages, f"fyq:{keyword}") if total else fyp_menu_keyboard()
    if replace:
        await edit_message(target, body, markup)
    else:
        await target.answer(body, reply_markup=markup)


@router.message(Command("fyp"))
async def fyp_command(message: Message, command: CommandObject, db) -> None:
    keyword = sanitise(command.args)
    if keyword:
        await show_search(message, db, keyword, 1, False)
        return
    await show_listing(message, db, "available", 0, 0, 0, 1, False)


@router.callback_query(F.data == "fypmenu")
async def menu(callback: CallbackQuery) -> None:
    await acknowledge(callback)
    await edit_message(callback.message, texts.fyp_usage(), fyp_menu_keyboard())


@router.callback_query(F.data.startswith("fyp:"))
async def listing_page(callback: CallbackQuery, db) -> None:
    parts = callback.data.split(":")
    if len(parts) != 6:
        await acknowledge(callback)
        return
    _, status, supervisor_index, area_index, year_index, page = parts
    await acknowledge(callback)
    if status not in STATUSES:
        return
    await show_listing(
        callback.message,
        db,
        status,
        int(supervisor_index),
        int(area_index),
        int(year_index),
        int(page),
        True,
    )


@router.callback_query(F.data.startswith("fyq:"))
async def search_page(callback: CallbackQuery, db) -> None:
    head, _, tail = callback.data.rpartition(":")
    keyword = head[4:]
    await acknowledge(callback)
    await show_search(callback.message, db, keyword, int(tail), True)


@router.callback_query(F.data.startswith("fyps:"))
async def supervisor_screen(callback: CallbackQuery, db) -> None:
    status = callback.data.split(":")[1]
    await acknowledge(callback)
    if status not in STATUSES:
        return
    names = await store.supervisors(db, status)
    await edit_message(
        callback.message,
        texts.fyp_supervisors_prompt(len(names)),
        fyp_choice_keyboard(names, f"fypsel:{status}", "fypmenu"),
    )


@router.callback_query(F.data.startswith("fypa:"))
async def area_screen(callback: CallbackQuery, db) -> None:
    parts = callback.data.split(":")
    status = parts[1]
    supervisor_index = int(parts[2])
    await acknowledge(callback)
    if status not in STATUSES:
        return
    areas = await store.areas(db, status)
    await edit_message(
        callback.message,
        texts.fyp_areas_prompt(len(areas)),
        fyp_choice_keyboard(areas, f"fypasel:{status}:{supervisor_index}", "fypmenu"),
    )


@router.callback_query(F.data.startswith("fypy:"))
async def year_screen(callback: CallbackQuery, db) -> None:
    parts = callback.data.split(":")
    status = parts[1]
    supervisor_index = int(parts[2])
    await acknowledge(callback)
    if status not in STATUSES:
        return
    years = await store.years(db, status)
    await edit_message(
        callback.message,
        texts.fyp_years_prompt(len(years)),
        fyp_choice_keyboard(years, f"fypysel:{status}:{supervisor_index}", "fypmenu"),
    )


@router.callback_query(F.data.startswith("fypsel:"))
async def choose_supervisor(callback: CallbackQuery, db) -> None:
    _, status, index = callback.data.split(":")
    await acknowledge(callback)
    if status not in STATUSES:
        return
    await show_listing(callback.message, db, status, int(index), 0, 0, 1, True)


@router.callback_query(F.data.startswith("fypasel:"))
async def choose_area(callback: CallbackQuery, db) -> None:
    _, status, supervisor_index, index = callback.data.split(":")
    await acknowledge(callback)
    if status not in STATUSES:
        return
    await show_listing(callback.message, db, status, int(supervisor_index), int(index), 0, 1, True)


@router.callback_query(F.data.startswith("fypysel:"))
async def choose_year(callback: CallbackQuery, db) -> None:
    _, status, supervisor_index, index = callback.data.split(":")
    await acknowledge(callback)
    if status not in STATUSES:
        return
    await show_listing(callback.message, db, status, int(supervisor_index), 0, int(index), 1, True)


@router.callback_query(F.data.startswith("fypitem:"))
async def topic_detail(callback: CallbackQuery, db, admin_role: str | None) -> None:
    identifier = int(callback.data.split(":")[1])
    await acknowledge(callback)
    topic = await store.one(db, identifier)
    if topic is None:
        await edit_message(callback.message, texts.fyp_missing())
        return
    await edit_message(
        callback.message,
        texts.fyp_body(topic),
        fyp_detail_keyboard(topic, can(admin_role, "fyp")),
    )


@router.callback_query(F.data.startswith("fypst:"))
async def set_status(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "fyp"):
        await acknowledge(callback)
        return
    _, identifier, status = callback.data.split(":")
    await acknowledge(callback)
    if status not in STATUSES:
        return
    await store.set_status(db, int(identifier), status)
    await audit.record(db, callback.from_user.id, "fyp.status", f"{identifier}:{status}")
    topic = await store.one(db, int(identifier))
    if topic is None:
        await edit_message(callback.message, texts.fyp_missing())
        return
    await edit_message(callback.message, texts.fyp_body(topic), fyp_detail_keyboard(topic, True))


@router.callback_query(F.data.startswith("fypdrop:"))
async def drop_topic(callback: CallbackQuery, db, admin_role: str | None) -> None:
    if not can(admin_role, "fyp"):
        await acknowledge(callback)
        return
    identifier = int(callback.data.split(":")[1])
    await acknowledge(callback)
    await store.remove(db, identifier)
    await audit.record(db, callback.from_user.id, "fyp.delete", str(identifier))
    await edit_message(callback.message, texts.fyp_removed(identifier), fyp_menu_keyboard())
