from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app import texts
from app.keyboards import (
    LEVELS,
    button,
    category_keyboard,
    course_keyboard,
    lecturer_keyboard,
    level_keyboard,
    materials_keyboard,
)
from app.services import catalog
from app.services.caption import (
    CaptionError,
    normalise_course_code,
    parse_semester,
    parse_year,
)
from app.services.catalog import MaterialFilter
from app.services.telegram import acknowledge, edit_message

router = Router(name="browse")


def optional_int(value: str) -> int | None:
    if value in {"", "-"}:
        return None
    return int(value)


def course_nav(level: str, code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[button("Back to course", f"cat:{level}:{code}"), button("Home", "home")]]
    )


async def show_listing(
    target: Message,
    db,
    level: str,
    code: str,
    category: str,
    year: int | None,
    semester: int | None,
    lecturer_index: int | None,
    page: int,
    prefix: str,
    replace: bool,
) -> None:
    names = await catalog.lecturers(db, code, category)
    lecturer = None
    if lecturer_index is not None and 0 <= lecturer_index < len(names):
        lecturer = names[lecturer_index]
    if lecturer_index is not None and lecturer is None:
        lecturer_index = None
        page = 1

    rows, total, pages = await catalog.listing(db, MaterialFilter(code, category, year, semester, lecturer), page)

    if total == 0:
        text = texts.empty_listing(code, category)
        markup = course_nav(level, code)
    else:
        text = texts.listing_prompt(code, category, total, page, pages, year, semester, lecturer)
        markup = materials_keyboard(rows, page, pages, prefix, level, code, category)

    if replace:
        await edit_message(target, text, markup)
    else:
        await target.answer(text, reply_markup=markup)


@router.message(Command("browse"))
async def browse_command(message: Message, student: dict) -> None:
    await message.answer(texts.level_prompt(), reply_markup=level_keyboard(student["level"]))


@router.callback_query(F.data == "browse")
async def browse_callback(callback: CallbackQuery, student: dict) -> None:
    await acknowledge(callback)
    await edit_message(callback.message, texts.level_prompt(), level_keyboard(student["level"]))


@router.callback_query(F.data.startswith("lvl:"))
async def choose_level(callback: CallbackQuery, student: dict, db) -> None:
    level = callback.data.split(":")[1]
    await acknowledge(callback)
    if level not in LEVELS:
        return
    await db.execute("update students set level = $2 where id = $1", student["id"], level)
    rows, total, pages = await catalog.courses_for_level(db, level, 1)
    await edit_message(
        callback.message,
        texts.courses_prompt(level, total),
        course_keyboard(rows, level, 1, pages) if total else None,
    )


@router.callback_query(F.data.startswith("crs:"))
async def course_page(callback: CallbackQuery, db) -> None:
    parts = callback.data.split(":")
    level = parts[1]
    page = int(parts[2])
    await acknowledge(callback)
    if level not in LEVELS:
        return
    rows, total, pages = await catalog.courses_for_level(db, level, page)
    await edit_message(
        callback.message,
        texts.courses_prompt(level, total),
        course_keyboard(rows, level, page, pages) if total else None,
    )


@router.callback_query(F.data.startswith("cat:"))
async def category_list(callback: CallbackQuery, db) -> None:
    parts = callback.data.split(":")
    level = parts[1]
    code = parts[2]
    await acknowledge(callback)
    course = await catalog.course(db, code)
    if course is None:
        await edit_message(callback.message, texts.course_missing(code))
        return
    await edit_message(
        callback.message,
        texts.categories_prompt(code, course["title"]),
        category_keyboard(level, code),
    )


@router.callback_query(F.data.startswith("ml:"))
async def material_list(callback: CallbackQuery, db) -> None:
    parts = callback.data.split(":")
    if len(parts) != 8:
        await acknowledge(callback)
        return
    _, level, code, category, year, semester, lecturer_index, page = parts
    await acknowledge(callback)
    course = await catalog.course(db, code)
    if course is None:
        await edit_message(callback.message, texts.course_missing(code))
        return
    await show_listing(
        callback.message,
        db,
        level,
        code,
        category,
        optional_int(year),
        optional_int(semester),
        optional_int(lecturer_index),
        int(page),
        ":".join(parts[:-1]),
        True,
    )


@router.callback_query(F.data.startswith("lec:"))
async def lecturer_menu(callback: CallbackQuery, db) -> None:
    parts = callback.data.split(":")
    level = parts[1]
    code = parts[2]
    category = parts[3]
    await acknowledge(callback)
    names = await catalog.lecturers(db, code, category)
    await edit_message(
        callback.message,
        texts.lecturer_prompt(code, category, len(names)),
        lecturer_keyboard(level, code, category, names),
    )


@router.callback_query(F.data.startswith("lcp:"))
async def lecturer_choice(callback: CallbackQuery, db) -> None:
    parts = callback.data.split(":")
    level = parts[1]
    code = parts[2]
    category = parts[3]
    index = int(parts[4])
    await acknowledge(callback)
    prefix = f"ml:{level}:{code}:{category}:-:-:{index}"
    await show_listing(callback.message, db, level, code, category, None, None, index, 1, prefix, True)


@router.message(Command("pq"))
async def past_questions(message: Message, command: CommandObject, db) -> None:
    tokens = (command.args or "").split()
    if not tokens:
        await message.answer(texts.pq_usage())
        return
    code = normalise_course_code(tokens[0])
    year = None
    semester = None
    try:
        for token in tokens[1:]:
            lowered = token.lower()
            if lowered.startswith("sem"):
                semester = parse_semester(lowered)
            elif token.isdigit():
                year = parse_year(token)
            else:
                await message.answer(texts.pq_usage())
                return
    except CaptionError as error:
        await message.answer(f"{error}\n{texts.pq_usage()}")
        return

    course = await catalog.course(db, code)
    if course is None:
        await message.answer(texts.course_missing(code))
        return
    prefix = f"pq:{code}:{year or '-'}:{semester or '-'}:-"
    await show_listing(message, db, course["level"], code, "pq", year, semester, None, 1, prefix, False)


@router.callback_query(F.data.startswith("pq:"))
async def past_questions_page(callback: CallbackQuery, db) -> None:
    parts = callback.data.split(":")
    if len(parts) != 6:
        await acknowledge(callback)
        return
    _, code, year, semester, lecturer_index, page = parts
    await acknowledge(callback)
    course = await catalog.course(db, code)
    if course is None:
        await edit_message(callback.message, texts.course_missing(code))
        return
    await show_listing(
        callback.message,
        db,
        course["level"],
        code,
        "pq",
        optional_int(year),
        optional_int(semester),
        optional_int(lecturer_index),
        int(page),
        ":".join(parts[:-1]),
        True,
    )
