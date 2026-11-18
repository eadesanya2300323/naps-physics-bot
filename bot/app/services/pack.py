from collections.abc import Sequence

BATCH_SIZE = 5


def pack_batches(materials: Sequence[dict], size: int = BATCH_SIZE) -> list[list[dict]]:
    return [list(materials[index : index + size]) for index in range(0, len(materials), size)]


def pack_total(materials: Sequence[dict]) -> int:
    return len(materials)


def progress_counts(done: int, total: int) -> tuple[int, int]:
    return min(done, total), total
