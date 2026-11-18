from dataclasses import dataclass
from pathlib import PurePosixPath

import asyncpg
from aiogram.types import BufferedInputFile

from app import texts
from app.keyboards import material_keyboard
from app.services import catalog
from app.services.caption import UploadFields
from app.services.storage import StorageError
from app.services.telegram import send_document, send_text
from app.services.versioning import MaterialVersion, version_plan


@dataclass(frozen=True)
class StoredFile:
    storage_path: str
    mime_type: str | None
    size_bytes: int
    sha256: str


class DuplicateMaterial(Exception):
    def __init__(self, title: str):
        super().__init__(title)
        self.title = title


class UnknownCourse(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


async def save_material(db, upload: UploadFields, stored: StoredFile, added_by: int) -> tuple[dict, int, str | None]:
    course = None
    if upload.course_code:
        course = await db.fetchrow("select code, level from courses where code = $1", upload.course_code)
        if course is None:
            raise UnknownCourse(upload.course_code)

    try:
        async with db.transaction() as connection:
            existing = await connection.fetch(
                "select id, version, is_current from materials "
                "where course_code is not distinct from $1 and category = $2 "
                "and lower(title) = lower($3) and coalesce(year, 0) = coalesce($4::int, 0)",
                upload.course_code,
                upload.category,
                upload.title,
                upload.year,
            )
            plan = version_plan([MaterialVersion(row["id"], row["version"], row["is_current"]) for row in existing])
            row = await connection.fetchrow(
                "insert into materials "
                "(course_code, category, title, year, semester, lecturer, storage_path, mime_type, size_bytes, sha256, version, added_by) "
                "values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) returning *",
                upload.course_code,
                upload.category,
                upload.title,
                upload.year,
                upload.semester,
                upload.lecturer,
                stored.storage_path,
                stored.mime_type,
                stored.size_bytes,
                stored.sha256,
                plan.version,
                added_by,
            )
            if plan.supersede_ids:
                await connection.execute(
                    "update materials set is_current = false where id = any($1::bigint[])",
                    list(plan.supersede_ids),
                )
    except asyncpg.UniqueViolationError:
        clash = await db.fetchrow("select title from materials where sha256 = $1", stored.sha256)
        raise DuplicateMaterial(clash["title"] if clash else upload.title)

    return dict(row), len(plan.supersede_ids), course["level"] if course else None


def back_target(material: dict) -> tuple[str, str]:
    if material["category"] == "template" or not material.get("course_code"):
        return "Templates", "tpl:1"
    level = material.get("course_level")
    if level:
        return "Back to course", f"cat:{level}:{material['course_code']}"
    return "Home", "home"


async def deliver(bot, db, bucket, settings, chat_id: int, material: dict, student_id: str | None = None) -> None:
    saved = await catalog.is_saved(db, student_id, material["id"]) if student_id else False
    back_label, back_data = back_target(material)
    caption = texts.material_caption(material)
    markup = material_keyboard(material, settings.site_url, saved, back_label, back_data)

    if material["telegram_file_id"]:
        await send_document(bot, chat_id, material["telegram_file_id"], caption, markup)
        return

    if (material["size_bytes"] or 0) > settings.send_limit_bytes:
        size_mb = round((material["size_bytes"] or 0) / (1024 * 1024))
        await send_text(bot, chat_id, texts.large_file(material["title"], size_mb), markup)
        return

    try:
        payload = await bucket.get(material["storage_path"])
    except StorageError:
        await send_text(bot, chat_id, texts.file_unavailable(), markup)
        return

    document = BufferedInputFile(payload, filename=PurePosixPath(material["storage_path"]).name)
    sent = await send_document(bot, chat_id, document, caption, markup)
    if sent is not None and sent.document is not None:
        await db.execute(
            "update materials set telegram_file_id = $2 where id = $1",
            material["id"],
            sent.document.file_id,
        )


async def remove(db, bucket, material_id: int) -> dict | None:
    material = await db.fetchrow("select id, title, storage_path from materials where id = $1", material_id)
    if material is None:
        return None
    await bucket.delete(material["storage_path"])
    await db.execute("delete from materials where id = $1", material_id)
    return dict(material)
