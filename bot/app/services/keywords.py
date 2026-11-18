import re

KEYWORD_LIMIT = 40


def sanitise(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[^\w\s\-.]", " ", value)
    return re.sub(r"\s+", " ", cleaned).strip()[:KEYWORD_LIMIT]
