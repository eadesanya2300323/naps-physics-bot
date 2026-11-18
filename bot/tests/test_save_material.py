import asyncio

import asyncpg
import pytest
from app.services.caption import UploadFields
from app.services.materials import (
    DuplicateMaterial,
    StoredFile,
    UnknownCourse,
    save_material,
)

COURSE = {"code": "PHY201", "level": "200"}
TITLE = "First semester past questions"


class FakeConnection:
    def __init__(self, database: "FakeDatabase"):
        self.database = database

    async def fetch(self, query, *args):
        code, category, title, year = args
        return [
            {"id": row["id"], "version": row["version"], "is_current": row["is_current"]}
            for row in self.database.materials
            if row["course_code"] == code
            and row["category"] == category
            and row["title"].lower() == title.lower()
            and (row["year"] or 0) == (year or 0)
        ]

    async def fetchrow(self, query, *args):
        return await self.database.insert(args)

    async def execute(self, query, *args):
        for row in self.database.materials:
            if row["id"] in args[0]:
                row["is_current"] = False


class FakeTransaction:
    def __init__(self, database: "FakeDatabase"):
        self.database = database

    async def __aenter__(self):
        return FakeConnection(self.database)

    async def __aexit__(self, *args):
        return False


class FakeDatabase:
    def __init__(self, course, materials):
        self.course = course
        self.materials = [dict(row) for row in materials]

    def transaction(self):
        return FakeTransaction(self)

    async def fetchrow(self, query, *args):
        if "from courses" in query:
            return self.course
        if "sha256" in query:
            for row in self.materials:
                if row["sha256"] == args[0]:
                    return {"title": row["title"]}
        return None

    async def insert(self, args):
        course_code, category, title, year, semester, lecturer, path, mime, size, sha, version, added_by = args
        if any(row["sha256"] == sha for row in self.materials):
            raise asyncpg.UniqueViolationError("duplicate key value violates unique constraint")
        row = {
            "id": max((row["id"] for row in self.materials), default=0) + 1,
            "course_code": course_code,
            "category": category,
            "title": title,
            "year": year,
            "semester": semester,
            "lecturer": lecturer,
            "storage_path": path,
            "mime_type": mime,
            "size_bytes": size,
            "sha256": sha,
            "version": version,
            "is_current": True,
            "added_by": added_by,
        }
        self.materials.append(row)
        return row


def existing(identifier=7, version=2, current=True, sha="b" * 64, title=TITLE):
    return {
        "id": identifier,
        "course_code": "PHY201",
        "category": "pq",
        "title": title,
        "year": 2023,
        "version": version,
        "is_current": current,
        "sha256": sha,
    }


def payload(sha="a" * 64):
    fields = UploadFields("PHY201", "pq", TITLE, 2023, 1, None)
    stored = StoredFile("PHY201/pq/aaaaaaaaaaaaaaaa.pdf", "application/pdf", 10, sha)
    return fields, stored


def test_first_upload_is_version_one():
    database = FakeDatabase(COURSE, [])
    fields, stored = payload()
    material, superseded, level = asyncio.run(save_material(database, fields, stored, 42))
    assert material["version"] == 1
    assert superseded == 0
    assert level == "200"


def test_same_identity_supersedes_the_previous_version():
    database = FakeDatabase(COURSE, [existing()])
    fields, stored = payload()
    material, superseded, _ = asyncio.run(save_material(database, fields, stored, 42))
    assert material["version"] == 3
    assert superseded == 1
    assert database.materials[0]["is_current"] is False
    assert database.materials[1]["version"] == 3


def test_duplicate_bytes_are_rejected_with_the_existing_title():
    database = FakeDatabase(COURSE, [existing(sha="a" * 64, title="Optics past questions")])
    fields, stored = payload()
    with pytest.raises(DuplicateMaterial) as error:
        asyncio.run(save_material(database, fields, stored, 42))
    assert error.value.title == "Optics past questions"


def test_unknown_course_is_reported():
    database = FakeDatabase(None, [])
    fields, stored = payload()
    with pytest.raises(UnknownCourse):
        asyncio.run(save_material(database, fields, stored, 42))
