from dataclasses import dataclass

from app.keyboards import PAGE_SIZE
from app.services.lecturers import dedupe_lecturers

LIST_COLUMNS = (
    "m.id, m.course_code, m.category, m.title, m.year, m.semester, m.lecturer, "
    "m.version, m.is_current, m.is_key, m.size_bytes, m.telegram_file_id, m.storage_path, m.mime_type, m.created_at"
)

FILTER_CLAUSE = (
    "m.course_code = $1 "
    "and ($2::text is null or m.category = $2) "
    "and ($3::int is null or m.year = $3) "
    "and ($4::smallint is null or m.semester = $4) "
    r"and ($5::text is null or lower(regexp_replace(m.lecturer, '\s+', ' ', 'g')) = lower($5))"
)


@dataclass(frozen=True)
class MaterialFilter:
    code: str
    category: str | None = None
    year: int | None = None
    semester: int | None = None
    lecturer: str | None = None

    def args(self) -> list:
        return [self.code, self.category, self.year, self.semester, self.lecturer]


def page_count(total: int, size: int = PAGE_SIZE) -> int:
    return max(1, -(-total // size))


async def course(db, code: str):
    return await db.fetchrow("select code, title, level, semester from courses where code = $1", code)


async def courses_for_level(db, level: str, page: int = 1):
    offset = (page - 1) * PAGE_SIZE
    total = await db.fetchval("select count(*) from courses where level = $1", level)
    rows = await db.fetch(
        "select code, title, level from courses where level = $1 order by code limit $2 offset $3",
        level,
        PAGE_SIZE,
        offset,
    )
    return rows, total, page_count(total)


async def all_courses(db, page: int = 1):
    offset = (page - 1) * PAGE_SIZE
    total = await db.fetchval("select count(*) from courses")
    rows = await db.fetch(
        "select code, title, level from courses order by code limit $1 offset $2",
        PAGE_SIZE,
        offset,
    )
    return rows, total, page_count(total)


async def lecturers(db, code: str, category: str):
    rows = await db.fetch(
        "select distinct lecturer from materials "
        "where course_code = $1 and category = $2 and lecturer is not null "
        "order by lecturer limit 40",
        code,
        category,
    )
    return dedupe_lecturers([row["lecturer"] for row in rows])


async def course_lecturers(db, code: str):
    rows = await db.fetch(
        "select distinct lecturer from materials where course_code = $1 and lecturer is not null order by lecturer limit 40",
        code,
    )
    return dedupe_lecturers([row["lecturer"] for row in rows])


async def listing(db, filters: MaterialFilter, page: int = 1):
    offset = (page - 1) * PAGE_SIZE
    total = await db.fetchval(f"select count(*) from materials m where {FILTER_CLAUSE}", *filters.args())
    rows = await db.fetch(
        f"select {LIST_COLUMNS} from materials m where {FILTER_CLAUSE} "
        "order by m.is_current desc, coalesce(m.year, 0) desc, m.title "
        "limit $6 offset $7",
        *filters.args(),
        PAGE_SIZE,
        offset,
    )
    return rows, total, page_count(total)


async def material(db, material_id: int):
    return await db.fetchrow(
        "select m.*, c.title as course_title, c.level as course_level "
        "from materials m left join courses c on c.code = m.course_code where m.id = $1",
        material_id,
    )


async def search(db, keyword: str, page: int = 1):
    pattern = f"%{keyword}%"
    offset = (page - 1) * PAGE_SIZE
    total = await db.fetchval(
        "select count(*) from materials m where m.course_code ilike $1 or m.title ilike $1",
        pattern,
    )
    rows = await db.fetch(
        f"select {LIST_COLUMNS} from materials m "
        "where m.course_code ilike $1 or m.title ilike $1 "
        "order by m.is_current desc, m.created_at desc limit $2 offset $3",
        pattern,
        PAGE_SIZE,
        offset,
    )
    return rows, total, page_count(total)


async def favourites(db, student_id: str, page: int = 1):
    offset = (page - 1) * PAGE_SIZE
    total = await db.fetchval("select count(*) from favorites where student_id = $1", student_id)
    rows = await db.fetch(
        f"select {LIST_COLUMNS} from favorites f join materials m on m.id = f.material_id "
        "where f.student_id = $1 order by f.created_at desc limit $2 offset $3",
        student_id,
        PAGE_SIZE,
        offset,
    )
    return rows, total, page_count(total)


async def recent(db, student_id: str, page: int = 1):
    offset = (page - 1) * PAGE_SIZE
    total = await db.fetchval("select count(*) from recent_views where student_id = $1", student_id)
    rows = await db.fetch(
        f"select {LIST_COLUMNS} from recent_views r join materials m on m.id = r.material_id "
        "where r.student_id = $1 order by r.viewed_at desc limit $2 offset $3",
        student_id,
        PAGE_SIZE,
        offset,
    )
    return rows, total, page_count(total)


async def key_materials(db, level: str):
    return await db.fetch(
        "select m.*, c.title as course_title, c.level as course_level from materials m "
        "join courses c on c.code = m.course_code "
        "where c.level = $1 and m.is_key and m.is_current "
        "order by m.course_code, coalesce(m.year, 0) desc, m.title",
        level,
    )


async def templates(db, page: int = 1):
    offset = (page - 1) * PAGE_SIZE
    total = await db.fetchval("select count(*) from materials where category = 'template'")
    rows = await db.fetch(
        f"select m.*, null::text as course_title, null::text as course_level from materials m "
        "where m.category = 'template' "
        "order by m.is_current desc, m.created_at desc limit $1 offset $2",
        PAGE_SIZE,
        offset,
    )
    return rows, total, page_count(total)


async def is_saved(db, student_id: str, material_id: int) -> bool:
    return bool(
        await db.fetchval(
            "select exists(select 1 from favorites where student_id = $1 and material_id = $2)",
            student_id,
            material_id,
        )
    )


async def toggle_favourite(db, student_id: str, material_id: int) -> bool:
    removed = await db.fetchval(
        "delete from favorites where student_id = $1 and material_id = $2 returning material_id",
        student_id,
        material_id,
    )
    if removed is not None:
        return False
    await db.execute(
        "insert into favorites (student_id, material_id) values ($1, $2) on conflict do nothing",
        student_id,
        material_id,
    )
    return True


async def touch_recent(db, student_id: str, material_id: int) -> None:
    await db.execute(
        "insert into recent_views (student_id, material_id, viewed_at) values ($1, $2, now()) "
        "on conflict (student_id, material_id) do update set viewed_at = now()",
        student_id,
        material_id,
    )
