import hashlib
import re
from pathlib import PurePosixPath

MIME_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "text/plain": ".txt",
    "application/zip": ".zip",
}

EXTENSION_PATTERN = re.compile(r"^\.[a-z0-9]{1,5}$")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_extension(filename: str | None, mime_type: str | None) -> str:
    suffix = PurePosixPath(filename or "").suffix.lower()
    if EXTENSION_PATTERN.match(suffix):
        return suffix
    return MIME_EXTENSIONS.get(mime_type or "", ".bin")


def storage_path(course_code: str | None, category: str, digest: str, filename: str | None, mime_type: str | None) -> str:
    folder = course_code or "general"
    return f"{folder}/{category}/{digest[:16]}{file_extension(filename, mime_type)}"
