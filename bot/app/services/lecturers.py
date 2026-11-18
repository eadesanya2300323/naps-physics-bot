import re
from collections.abc import Sequence

TITLE_ALIASES = {
    "dr": "Dr",
    "dr.": "Dr",
    "prof": "Prof",
    "prof.": "Prof",
    "professor": "Prof",
    "mr": "Mr",
    "mr.": "Mr",
    "mrs": "Mrs",
    "mrs.": "Mrs",
    "miss": "Miss",
    "ms": "Ms",
    "ms.": "Ms",
    "engr": "Engr",
    "engr.": "Engr",
}


def normalise_lecturer(value: str | None) -> str | None:
    if not value:
        return None
    collapsed = re.sub(r"\s+", " ", value).strip()
    if not collapsed:
        return None
    collapsed = re.sub(r"\s*-\s*", "-", collapsed)
    words = []
    for word in collapsed.split(" "):
        alias = TITLE_ALIASES.get(word.lower())
        words.append(alias if alias else word.title())
    return " ".join(words)


def lecturer_key(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def match_lecturer(candidates: Sequence[str], value: str | None) -> str | None:
    normalised = normalise_lecturer(value)
    if normalised is None:
        return None
    wanted = lecturer_key(normalised)
    for candidate in candidates:
        if lecturer_key(candidate) == wanted:
            return candidate
    return normalised


def dedupe_lecturers(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    names = []
    for value in values:
        normalised = normalise_lecturer(value)
        if normalised is None:
            continue
        key = lecturer_key(normalised)
        if key in seen:
            continue
        seen.add(key)
        names.append(normalised)
    return names
