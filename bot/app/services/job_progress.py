from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class JobProgress:
    sent: int = 0
    failed: int = 0
    cursor: str | None = None
    status: str = "queued"


def advance(progress: JobProgress, results: Sequence[tuple[str, bool]], more: bool) -> JobProgress:
    sent = progress.sent
    failed = progress.failed
    cursor = progress.cursor
    for student_id, delivered in results:
        cursor = student_id
        if delivered:
            sent += 1
        else:
            failed += 1
    return JobProgress(sent, failed, cursor, "sending" if more else "sent")
