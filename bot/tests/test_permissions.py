import pytest
from app.services.permissions import can, is_admin


@pytest.mark.parametrize(
    ("role", "capability", "expected"),
    [
        ("super", "materials", True),
        ("uploader", "materials", True),
        ("moderator", "materials", False),
        ("moderator", "broadcasts", True),
        ("uploader", "broadcasts", False),
        ("uploader", "moderation", False),
        ("moderator", "moderation", True),
        ("uploader", "admins", False),
        ("moderator", "admins", False),
        ("super", "ownership", True),
        ("moderator", "ownership", False),
        (None, "materials", False),
        ("student", "materials", False),
        ("super", "unknown", False),
    ],
)
def test_matrix(role, capability, expected):
    assert can(role, capability) is expected


def test_is_admin():
    assert is_admin("super")
    assert is_admin("moderator")
    assert is_admin("uploader")
    assert not is_admin(None)
    assert not is_admin("student")
