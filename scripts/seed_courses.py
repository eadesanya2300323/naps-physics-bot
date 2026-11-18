import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bot"))

from app.config import get_settings
from app.db import Database

LEVELS = {"100", "200", "300", "400"}


def read_rows(path: Path) -> list[tuple[str, str, str, int | None]]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            code = (raw.get("code") or "").strip().upper()
            title = (raw.get("title") or "").strip()
            level = (raw.get("level") or "").strip().upper().removesuffix("L")
            semester_text = (raw.get("semester") or "").strip()
            if not code or not title or level not in LEVELS:
                raise SystemExit(f"Bad row: {raw}")
            if semester_text not in {"", "1", "2"}:
                raise SystemExit(f"Bad semester in row: {raw}")
            semester = int(semester_text) if semester_text else None
            rows.append((code, title, level, semester))
    return rows


async def seed(path: Path) -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    await database.connect()
    try:
        rows = read_rows(path)
        for row in rows:
            await database.execute(
                "insert into courses (code, title, level, semester) values ($1, $2, $3, $4) "
                "on conflict (code) do update set title = excluded.title, "
                "level = excluded.level, semester = excluded.semester",
                *row,
            )
        print(f"{len(rows)} courses written")
    finally:
        await database.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/seed_courses.py courses.csv")
    asyncio.run(seed(Path(sys.argv[1])))
