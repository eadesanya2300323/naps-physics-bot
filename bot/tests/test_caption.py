import pytest
from app.services.caption import (
    CaptionError,
    UploadFields,
    parse_course_line,
    parse_upload_caption,
)


def test_reads_every_field():
    fields = parse_upload_caption("PHY201 | pq | First semester past questions | 2023 | 1 | Dr Okafor")
    assert fields == UploadFields("PHY201", "pq", "First semester past questions", 2023, 1, "Dr Okafor")


def test_normalises_code_category_and_spacing():
    fields = parse_upload_caption("  phy 201 | NOTES | Optics   notes | 2024 | sem2 ")
    assert fields == UploadFields("PHY201", "notes", "Optics notes", 2024, 2, None)


def test_minimal_caption_leaves_optional_fields_empty():
    fields = parse_upload_caption("MTH101 | notes | Limits")
    assert fields == UploadFields("MTH101", "notes", "Limits", None, None, None)


@pytest.mark.parametrize(
    "caption",
    [
        "",
        "PHY201 | pq",
        "PHY201 | slides | Deck",
        "PHY201 | pq |    ",
        "PHY201 | pq | Deck | 23 | 1",
        "PHY201 | pq | Deck | 2023 | 3",
        "P1 | pq | Deck",
        "PHY201 | pq | Deck | 2023 | 1 | " + "x" * 90,
    ],
)
def test_rejects_bad_captions(caption):
    with pytest.raises(CaptionError):
        parse_upload_caption(caption)


def test_rejects_long_titles():
    with pytest.raises(CaptionError):
        parse_upload_caption("PHY201 | pq | " + "title " * 30)


def test_course_line():
    assert parse_course_line("PHY201 | Optics | 200L | 2") == ("PHY201", "Optics", "200", 2)
    assert parse_course_line("phy202|Waves|300") == ("PHY202", "Waves", "300", None)


@pytest.mark.parametrize("line", ["PHY201 | Optics", "PHY201 | Optics | 500", "PHY201 |  | 200"])
def test_course_line_rejects_bad_rows(line):
    with pytest.raises(CaptionError):
        parse_course_line(line)
