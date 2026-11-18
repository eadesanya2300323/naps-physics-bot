from dataclasses import replace

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import texts
from app.keyboards import (
    home_keyboard,
    semester_keyboard,
    upload_category_keyboard,
    upload_courses_keyboard,
    upload_lecturer_keyboard,
    year_keyboard,
)
from app.services import audit, catalog, jobs
from app.services.caption import (
    CATEGORY_LABELS,
    TITLE_LIMIT,
    CaptionError,
    UploadFields,
    clean_text,
    parse_upload_caption,
)
from app.services.files import sha256_hex, storage_path
from app.services.lecturers import match_lecturer, normalise_lecturer
from app.services.materials import DuplicateMaterial, StoredFile, UnknownCourse, save_material
from app.services.permissions import can
from app.services.storage import StorageError
from app.services.telegram import acknowledge, edit_message, run_in_background

router = Router(name="admin_upload")


class UploadFlow(StatesGroup):
    upload = State()


async def prepare_lecturer(db, code: str | None, raw: str | None) -> str | None:
    if not raw:
        return None
    if not code:
        return normalise_lecturer(raw)
    names = await catalog.course_lecturers(db, code)
    return match_lecturer(names, raw)


async def finish_upload(target: Message, state: FSMContext, db, bucket, fields: UploadFields, actor: int) -> None:
    data = await state.get_data()
    file = data.get("file")
    if not file:
        await state.clear()
        await target.answer(texts.upload_prompt())
        return

    path = storage_path(fields.course_code, fields.category, file["sha256"], file["filename"], file["mime_type"])
    try:
        await bucket.put(path, file["bytes"], file["mime_type"] or "application/octet-stream")
    except StorageError:
        await state.clear()
        await target.answer(texts.file_unavailable())
        return

    stored = StoredFile(path, file["mime_type"], file["size"], file["sha256"])
    try:
        material, superseded, level = await save_material(db, fields, stored, actor)
    except DuplicateMaterial as duplicate:
        await bucket.delete(path)
        await state.clear()
        await target.answer(texts.duplicate_file(duplicate.title))
        return
    except UnknownCourse as unknown:
        await bucket.delete(path)
        await state.clear()
        await target.answer(texts.course_missing(unknown.code))
        return

    await audit.record(db, actor, "material.upload", f"materials/{material['id']}")
    await state.clear()
    await target.answer(
        texts.upload_done(fields.course_code, fields.category, fields.title, material["version"], superseded)
    )

    if level:
        await jobs.enqueue(db, "alert", "level", texts.alert_message(material), level=level, ref=str(material["id"]))
        run_in_background(jobs.process(db, target.bot))


@router.message(F.document)
async def receive_document(message: Message, state: FSMContext, db, bucket, settings, admin_role: str | None) -> None:
    if not can(admin_role, "materials"):
        await message.answer("Only admins can add files. Send /help for what this bot does.")
        return

    document = message.document
    size = document.file_size or 0
    if size > settings.upload_limit_bytes:
        await message.answer(texts.upload_too_large(round(size / (1024 * 1024))))
        return

    downloaded = await message.bot.download(document)
    payload = downloaded.getvalue()
    digest = sha256_hex(payload)
    duplicate = await db.fetchrow("select title from materials where sha256 = $1", digest)
    if duplicate:
        await message.answer(texts.duplicate_file(duplicate["title"]))
        return

    await state.clear()
    await state.set_state(UploadFlow.upload)
    await state.update_data(
        file={
            "bytes": payload,
            "filename": document.file_name or "file",
            "mime_type": document.mime_type,
            "size": len(payload),
            "sha256": digest,
        },
        step="course",
    )

    if message.caption:
        try:
            fields = parse_upload_caption(message.caption)
        except CaptionError as error:
            await message.answer(f"{error}\n{texts.caption_format()}")
            await state.clear()
            return
        fields = replace(fields, lecturer=await prepare_lecturer(db, fields.course_code, fields.lecturer))
        await finish_upload(message, state, db, bucket, fields, message.from_user.id)
        return

    rows, total, pages = await catalog.all_courses(db, 1)
    if total == 0:
        await state.clear()
        await message.answer("No courses on file yet. Add one with /addcourse, then send the file again.")
        return
    await message.answer(texts.upload_choose_course(), reply_markup=upload_courses_keyboard(rows, 1, pages))


@router.callback_query(F.data.startswith("up:"))
async def upload_callback(callback: CallbackQuery, state: FSMContext, db, bucket, admin_role: str | None) -> None:
    if not can(admin_role, "materials"):
        await acknowledge(callback)
        return

    parts = callback.data.split(":")
    action = parts[1]
    data = await state.get_data()
    await acknowledge(callback)

    if action == "cancel":
        await state.clear()
        await edit_message(callback.message, texts.upload_reset(), home_keyboard(admin_role))
        return

    if action == "crs":
        page = int(parts[2])
        rows, _, pages = await catalog.all_courses(db, page)
        await edit_message(callback.message, texts.upload_choose_course(), upload_courses_keyboard(rows, page, pages))
        return

    if action == "tpl":
        await state.update_data(course_code=None, category="template", step="title")
        await edit_message(callback.message, texts.upload_ask_title(None, "template"))
        return

    if action == "code":
        code = parts[2]
        await state.update_data(course_code=code, step="category")
        await edit_message(callback.message, texts.upload_choose_category(code), upload_category_keyboard(code))
        return

    if not data.get("file"):
        await state.clear()
        await edit_message(callback.message, texts.upload_prompt(), home_keyboard(admin_role))
        return

    if action == "cat":
        category = parts[2]
        if category not in CATEGORY_LABELS or not data.get("course_code"):
            return
        await state.update_data(category=category, step="title")
        await edit_message(callback.message, texts.upload_ask_title(data["course_code"], category))
        return

    if action == "yr":
        year = None if parts[2] == "-" else int(parts[2])
        await state.update_data(year=year, step="semester")
        await edit_message(callback.message, texts.upload_ask_semester(data.get("title", "")), semester_keyboard())
        return

    if action == "sem":
        semester = None if parts[2] == "-" else int(parts[2])
        await state.update_data(semester=semester, step="lecturer")
        code = data.get("course_code")
        names = await catalog.course_lecturers(db, code) if code else []
        await edit_message(
            callback.message,
            texts.upload_ask_lecturer(code, len(names)),
            upload_lecturer_keyboard(names),
        )
        return

    if action == "lecnew":
        await state.update_data(step="lecturer_new")
        await edit_message(callback.message, texts.upload_ask_lecturer_typed(data.get("course_code") or "Template"))
        return

    if action == "lec":
        code = data.get("course_code")
        names = await catalog.course_lecturers(db, code) if code else []
        index = int(parts[2])
        if not 0 <= index < len(names):
            return
        await complete(callback.message, state, db, bucket, data, names[index], admin_role, callback.from_user.id)
        return

    if action == "lecskip":
        await complete(callback.message, state, db, bucket, data, None, admin_role, callback.from_user.id)


async def complete(target: Message, state: FSMContext, db, bucket, data: dict, lecturer: str | None, role: str | None, actor: int) -> None:
    if not data.get("title"):
        return
    fields = UploadFields(
        data.get("course_code"),
        data["category"],
        data["title"],
        data.get("year"),
        data.get("semester"),
        lecturer,
    )
    await finish_upload(target, state, db, bucket, fields, actor)


@router.message(UploadFlow.upload, F.text, ~F.text.startswith("/"))
async def upload_text(message: Message, state: FSMContext, db, bucket, admin_role: str | None) -> None:
    if not can(admin_role, "materials"):
        await state.clear()
        return

    data = await state.get_data()
    step = data.get("step")

    if step == "title":
        try:
            title = clean_text(message.text, TITLE_LIMIT, "title")
        except CaptionError as error:
            await message.answer(str(error))
            return
        await state.update_data(title=title, step="year")
        await message.answer(texts.upload_ask_year(title), reply_markup=year_keyboard())
        return

    if step == "lecturer_new":
        if not data.get("title") or not data.get("category"):
            await state.clear()
            await message.answer(texts.upload_prompt())
            return
        lecturer = await prepare_lecturer(db, data.get("course_code"), message.text)
        await complete(message, state, db, bucket, data, lecturer, admin_role, message.from_user.id)
        return

    await message.answer(texts.upload_prompt())
