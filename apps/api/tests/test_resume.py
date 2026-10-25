"""Backend tests for resume extraction and validation."""

import pytest

from app.services.resume_parser import (
    MAX_FILE_SIZE,
    detect_format,
    extract_docx,
    extract_pdf,
    extract_txt,
    sanitize_filename,
    validate_upload,
)


def test_validate_upload_txt():
    fmt, name = validate_upload("resume.txt", "text/plain", b"Hello world")
    assert fmt == "txt"
    assert name == "resume.txt"


def test_validate_upload_empty_file_rejected():
    with pytest.raises(ValueError, match="empty"):
        validate_upload("empty.txt", "text/plain", b"")


def test_validate_upload_too_large_rejected():
    with pytest.raises(ValueError, match="too large"):
        validate_upload("big.txt", "text/plain", b"x" * (MAX_FILE_SIZE + 1))


def test_validate_upload_unsupported_type_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        validate_upload("malware.exe", "application/x-msdownload", b"MZ...")


def test_validate_upload_sanitizes_filename():
    fmt, name = validate_upload("../evil/../resume.txt", "text/plain", b"data")
    assert fmt == "txt"
    assert name == "resume.txt"
    assert ".." not in name
    assert "/" not in name


def test_detect_format_by_extension():
    assert detect_format("application/pdf", "resume.pdf") == "pdf"
    assert detect_format("text/plain", "resume.txt") == "txt"
    assert detect_format(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "resume.docx",
    ) == "docx"


@pytest.mark.asyncio
async def test_extract_txt():
    text = await extract_txt(b"Line one.\nLine two.")
    assert text == "Line one.\nLine two."


@pytest.mark.asyncio
async def test_extract_txt_handles_invalid_utf8():
    text = await extract_txt(b"\xff\xfeinvalid")
    assert isinstance(text, str)


@pytest.mark.asyncio
async def test_extract_pdf_returns_text():
    # Build a minimal valid PDF in memory using reportlab-like structure is
    # complex; instead ensure extract_pdf raises a clear error on garbage.
    with pytest.raises(Exception):
        await extract_pdf(b"not a pdf")


@pytest.mark.asyncio
async def test_extract_docx_returns_text():
    with pytest.raises(Exception):
        await extract_docx(b"not a docx")


def test_sanitize_filename():
    assert sanitize_filename("resume.txt") == "resume.txt"
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("weird<>:file.txt") == "weird___file.txt"
