import re

KINDS = ("suggestion", "bug", "report", "other")

KIND_LABELS = {
    "suggestion": "Idea",
    "bug": "Bot problem",
    "report": "Report a file",
    "other": "Something else",
}

STATUSES = ("new", "read", "resolved")

MIN_BODY = 5
MAX_BODY = 1000


def clean_body(value: str | None) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) < MIN_BODY:
        raise ValueError(f"Write at least {MIN_BODY} characters.")
    if len(text) > MAX_BODY:
        raise ValueError(f"Keep it under {MAX_BODY} characters.")
    return text


def status_label(status: str) -> str:
    return {"new": "New", "read": "Read", "resolved": "Resolved"}.get(status, status.title())


async def create(db, student_id, kind: str, body: str, material_id: int | None = None) -> int:
    return await db.fetchval(
        "insert into feedback (student_id, kind, body, material_id) values ($1, $2, $3, $4) returning id",
        student_id,
        kind,
        body,
        material_id,
    )


async def page(db, offset: int, limit: int):
    total = await db.fetchval("select count(*) from feedback")
    new_count = await db.fetchval("select count(*) from feedback where status = 'new'")
    rows = await db.fetch(
        "select * from feedback order by (status = 'new') desc, created_at desc limit $1 offset $2",
        limit,
        offset,
    )
    return rows, total, new_count


async def one(db, identifier: int):
    return await db.fetchrow(
        "select f.*, m.title as material_title, m.course_code as course_code "
        "from feedback f left join materials m on m.id = f.material_id where f.id = $1",
        identifier,
    )


async def set_status(db, identifier: int, status: str) -> None:
    await db.execute("update feedback set status = $2 where id = $1", identifier, status)


async def material_id_for(db, identifier: int) -> int | None:
    return await db.fetchval("select material_id from feedback where id = $1", identifier)
