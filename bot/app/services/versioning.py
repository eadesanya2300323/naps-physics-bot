from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialVersion:
    id: int
    version: int
    is_current: bool


@dataclass(frozen=True)
class VersionPlan:
    version: int
    supersede_ids: tuple[int, ...]


def version_plan(existing: Sequence[MaterialVersion]) -> VersionPlan:
    supersede_ids = tuple(item.id for item in existing if item.is_current)
    highest = max((item.version for item in existing), default=0)
    return VersionPlan(highest + 1, supersede_ids)


def status_label(is_current: bool) -> str:
    return "Current" if is_current else "Outdated"
