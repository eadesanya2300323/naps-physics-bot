import re
from dataclasses import dataclass

CATEGORIES = ("pq", "notes", "test", "assign", "template", "other")
CATEGORY_ORDER = CATEGORIES
COURSE_PATTERN = re.compile(r"^[A-Z]{2,4}\d{3}$")
TITLE_LIMIT = 120
LECTURER_LIMIT = 80
YEAR_FLOOR = 1990
YEAR_CEILING = 2100

CATEGORY_LABELS = {
    "pq": "Past questions",
    "notes": "Notes",
    "test": "Test papers",
    "assign": "Assignments",
    "template": "Templates",
    "other": "Other",
}


class CaptionError(ValueError):
    pass


@dataclass(frozen=True)
class UploadFields:
    course_code: str | None
    category: str
    title: str
    year: int | None
    semester: int | None
    lecturer: str | None


def normalise_course_code(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def valid_course_code(value: str) -> bool:
    return bool(COURSE_PATTERN.match(normalise_course_code(value)))


def clean_text(value: str, limit: int, field: str) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        raise CaptionError(f"A {field} is required.")
    if len(text) > limit:
        raise CaptionError(f"The {field} must be {limit} characters or fewer.")
    return text


def optional_text(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        return None
    if len(text) > limit:
        raise CaptionError(f"That value must be {limit} characters or fewer.")
    return text


def parse_year(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    if not text.isdigit() or len(text) != 4:
        raise CaptionError("The year should be four digits, like 2023.")
    year = int(text)
    if year < YEAR_FLOOR or year > YEAR_CEILING:
        raise CaptionError("That year is outside the range this library accepts.")
    return year


def parse_semester(value: str) -> int | None:
    text = value.strip().lower()
    if not text:
        return None
    if text in {"1", "sem1", "first"}:
        return 1
    if text in {"2", "sem2", "second"}:
        return 2
    raise CaptionError("The semester should be 1 or 2.")


def parse_upload_caption(text: str) -> UploadFields:
    parts = [part.strip() for part in text.split("|")]
    if len(parts) < 3:
        raise CaptionError("A caption needs a course code, a category and a title, separated by |.")
    course_code = normalise_course_code(parts[0])
    if not valid_course_code(course_code):
        raise CaptionError("The course code should look like PHY201.")
    category = parts[1].strip().lower()
    if category not in CATEGORIES:
        raise CaptionError("The category is one of pq, notes, test, assign, template or other.")
    title = clean_text(parts[2], TITLE_LIMIT, "title")
    year = parse_year(parts[3]) if len(parts) > 3 else None
    semester = parse_semester(parts[4]) if len(parts) > 4 else None
    lecturer = optional_text(parts[5] if len(parts) > 5 else None, LECTURER_LIMIT)
    return UploadFields(course_code, category, title, year, semester, lecturer)


def parse_course_line(text: str) -> tuple[str, str, str, int | None]:
    parts = [part.strip() for part in text.split("|")]
    if len(parts) < 3:
        raise CaptionError("Send the course as CODE | Title | Level | Semester.")
    course_code = normalise_course_code(parts[0])
    if not valid_course_code(course_code):
        raise CaptionError("The course code should look like PHY201.")
    title = clean_text(parts[1], TITLE_LIMIT, "title")
    level = parts[2].strip().lower().removesuffix("l")
    if level not in {"100", "200", "300", "400"}:
        raise CaptionError("The level is one of 100, 200, 300 or 400.")
    semester = parse_semester(parts[3]) if len(parts) > 3 else None
    return course_code, title, level, semester
