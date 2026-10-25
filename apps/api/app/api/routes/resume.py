"""Resume extraction route."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.param_functions import Depends

from app.services.profile_extractor import ProfileExtractor, profile_extractor
from app.services.resume_parser import (
    MAX_FILE_SIZE,
    ResumeParser,
    PyMuPDFParser,
    validate_upload,
)

router = APIRouter(tags=["resume"])


def get_parser() -> ResumeParser:
    """Dependency provider for the resume parser."""
    return PyMuPDFParser()


def get_extractor() -> ProfileExtractor:
    """Dependency provider for the profile extractor."""
    return profile_extractor


@router.post(
    "/profiles/extract-resume",
    status_code=status.HTTP_200_OK,
    summary="Extract raw text from an uploaded resume (PDF/DOCX/TXT)",
)
async def extract_resume(
    file: UploadFile = File(...),
    parser: ResumeParser = Depends(get_parser),
):
    """Accept a resume file, validate it, and return extracted text.

    No LLM is called in this phase. Extraction is deterministic.
    """
    content_type = file.content_type or ""
    data = await file.read()

    try:
        validate_upload(file.filename or "resume", content_type, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    extracted = await parser.extract_text(
        file_name=file.filename or "resume",
        content_type=content_type,
        data=data,
    )

    return {
        "extracted_text": extracted,
        "file_name": file.filename or "resume",
        "content_type": content_type,
        "size_bytes": len(data),
        "character_count": len(extracted),
        "word_count": len(extracted.split()),
    }


@router.post(
    "/profiles/extract-resume/draft",
    status_code=status.HTTP_200_OK,
    summary="Extract a structured profile draft from an uploaded resume",
)
async def extract_resume_draft(
    file: UploadFile = File(...),
    parser: ResumeParser = Depends(get_parser),
    extractor: ProfileExtractor = Depends(get_extractor),
):
    """Upload a resume and receive a structured ProfileDraft for review.

    The draft is not persisted. The user reviews and edits it before
    confirmation. No LLM is called in this phase.
    """
    content_type = file.content_type or ""
    data = await file.read()

    try:
        _, safe_name = validate_upload(
            file.filename or "resume", content_type, data
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    extracted = await parser.extract_text(
        file_name=safe_name,
        content_type=content_type,
        data=data,
    )

    fmt = (file.filename or "resume").rsplit(".", 1)[-1].upper()
    source_type = f"RESUME_{fmt}"
    draft = await extractor.extract(
        extracted, source_type=source_type, source_file_name=safe_name
    )
    return draft
