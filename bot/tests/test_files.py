from app.services.files import file_extension, sha256_hex, storage_path
from app.services.keywords import sanitise


def test_hash_is_stable_and_full_length():
    assert sha256_hex(b"naps") == sha256_hex(b"naps")
    assert len(sha256_hex(b"naps")) == 64
    assert sha256_hex(b"naps") != sha256_hex(b"nap")


def test_extension_prefers_the_filename():
    assert file_extension("PQ.PDF", "application/octet-stream") == ".pdf"
    assert file_extension("scan", "image/png") == ".png"
    assert file_extension(None, None) == ".bin"


def test_path_is_content_addressed():
    path = storage_path("PHY201", "pq", "a" * 64, "paper.pdf", "application/pdf")
    assert path == f"PHY201/pq/{'a' * 16}.pdf"
    assert storage_path(None, "template", "b" * 64, None, None) == f"general/template/{'b' * 16}.bin"


def test_keyword_cleaning_drops_callback_separators():
    assert sanitise("  optics:lecture  ") == "optics lecture"
    assert sanitise("!!!") == ""
    assert sanitise(None) == ""
    assert len(sanitise("a" * 60)) == 40
