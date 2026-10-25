"""Resume document processing service.

Extracts raw text from PDF, DOCX, and TXT resumes. Parsing is intentionally
kept separate from semantic profile extraction (which is handled by the
ProfileExtractor boundary).

Supported formats: PDF, DOCX, TXT. OCR and image resumes are not supported.
"""

import mimetypes
import os
import re
from typing import Protocol, Tuple

import docx
import fitz  # PyMuPDF

# Development upload limit: 10 MB.
MAX_FILE_SIZE = 10 * 1024 * 1024

SUPPORTED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}

# Characters that are unsafe in a stored filename.
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")


class ResumeParser(Protocol):
    """Protocol for resume text extraction."""

    async def extract_text(
        self,
        file_name: str,
        content_type: str,
        data: bytes,
    ) -> str:
        """Return the extracted plain-text content of a resume file."""
        ...


def sanitize_filename(file_name: str) -> str:
    """Return a safe, sanitized version of a file name."""
    base = os.path.basename(file_name)
    safe = _UNSAFE_FILENAME_CHARS.sub("_", base)
    return safe or "resume.txt"


def detect_format(content_type: str, file_name: str) -> str:
    """Detect the resume format from content type and file name."""
    ct = (content_type or "").lower().strip()
    if ct in SUPPORTED_CONTENT_TYPES:
        return SUPPORTED_CONTENT_TYPES[ct]
    # Fall back to extension guessing.
    ext = os.path.splitext(file_name)[1].lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext == ".txt":
        return "txt"
    guessed, _ = mimetypes.guess_type(file_name)
    if guessed in SUPPORTED_CONTENT_TYPES:
        return SUPPORTED_CONTENT_TYPES[guessed]
    raise ValueError(f"Unsupported file type: {content_type or file_name}")


def validate_upload(file_name: str, content_type: str, data: bytes) -> Tuple[str, str]:
    """Validate an uploaded resume file.

    Returns (format, sanitized_file_name). Raises ValueError on invalid input.
    """
    if not data:
        raise ValueError("The uploaded file is empty.")
    if len(data) > MAX_FILE_SIZE:
        raise ValueError(
            f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB."
        )
    fmt = detect_format(content_type, file_name)
    return fmt, sanitize_filename(file_name)


async def extract_pdf(data: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    text_parts = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


async def extract_docx(data: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    from io import BytesIO

    document = docx.Document(BytesIO(data))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


async def extract_txt(data: bytes) -> str:
    """Extract text from TXT bytes."""
    return data.decode("utf-8", errors="replace")


class PyMuPDFParser:
    """ResumeParser implementation using PyMuPDF / python-docx / stdlib."""

    async def extract_text(
        self,
        file_name: str,
        content_type: str,
        data: bytes,
    ) -> str:
        fmt, _ = validate_upload(file_name, content_type, data)
        if fmt == "pdf":
            return await extract_pdf(data)
        if fmt == "docx":
            return await extract_docx(data)
        if fmt == "txt":
            return await extract_txt(data)
        raise ValueError(f"Unsupported format: {fmt}")
