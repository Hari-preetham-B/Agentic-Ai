"""Profile and resume API routes."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import resume  # noqa: F401  (router included in main)
from app.core.database import get_session
from app.schemas.profile import (
    CareerGoalCreate,
    CareerGoalResponse,
    CareerGoalUpdate,
    EducationCreate,
    EducationResponse,
    EducationUpdate,
    ExperienceCreate,
    ExperienceResponse,
    ExperienceUpdate,
    ProfileCreate,
    ProfileDetailResponse,
    ProfileResponse,
    ProfileUpdate,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ResumeExtractResponse,
    SkillCreate,
    SkillResponse,
    SkillUpdate,
    ValidationResult,
)
from app.services.profile_service import (
    add_child,
    confirm_profile,
    create_profile,
    delete_child,
    delete_profile,
    get_profile,
    get_profile_detail,
    list_children,
    profile_to_detail_response,
    update_child,
    update_profile,
    validate_profile_for_confirmation,
)

router = APIRouter(tags=["profiles"])


# ---------------------------------------------------------------------------
# Profile CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/profiles",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new profile draft",
)
async def create_profile_endpoint(
    data: ProfileCreate, session: AsyncSession = Depends(get_session)
):
    profile = await create_profile(session, data)
    return ProfileResponse.model_validate(profile, from_attributes=True)


@router.get(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    summary="Get a profile by ID",
)
async def get_profile_endpoint(
    profile_id: UUID, session: AsyncSession = Depends(get_session)
):
    profile = await get_profile(session, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse.model_validate(profile, from_attributes=True)


@router.get(
    "/profiles/{profile_id}/detail",
    response_model=ProfileDetailResponse,
    summary="Get a profile with all child records",
)
async def get_profile_detail_endpoint(
    profile_id: UUID, session: AsyncSession = Depends(get_session)
):
    profile = await get_profile_detail(session, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile_to_detail_response(profile)


@router.put(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    summary="Update a profile",
)
async def update_profile_endpoint(
    profile_id: UUID,
    data: ProfileUpdate,
    session: AsyncSession = Depends(get_session),
):
    profile = await update_profile(session, profile_id, data)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse.model_validate(profile, from_attributes=True)


@router.delete(
    "/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a profile and all its child records",
)
async def delete_profile_endpoint(
    profile_id: UUID, session: AsyncSession = Depends(get_session)
):
    deleted = await delete_profile(session, profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    return None


# ---------------------------------------------------------------------------
# Validation & confirmation
# ---------------------------------------------------------------------------


@router.post(
    "/profiles/{profile_id}/validate",
    response_model=ValidationResult,
    summary="Validate a profile without confirming it",
)
async def validate_profile_endpoint(
    profile_id: UUID, session: AsyncSession = Depends(get_session)
):
    return await validate_profile_for_confirmation(session, profile_id)


@router.post(
    "/profiles/{profile_id}/confirm",
    response_model=ProfileResponse,
    summary="Confirm a profile after validation",
)
async def confirm_profile_endpoint(
    profile_id: UUID, session: AsyncSession = Depends(get_session)
):
    profile, validation = await confirm_profile(session, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    if validation is not None and not validation.valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Profile cannot be confirmed. Fix validation errors.",
                "errors": [e.model_dump() for e in validation.errors],
                "warnings": [w.model_dump() for w in validation.warnings],
            },
        )
    return ProfileResponse.model_validate(profile, from_attributes=True)


# ---------------------------------------------------------------------------
# Child record endpoints
# ---------------------------------------------------------------------------


def _child_routes(section: str, create_schema, response_schema, update_schema):
    """Register child CRUD routes for a given section."""

    @router.post(
        f"/profiles/{{profile_id}}/{section}",
        response_model=response_schema,
        status_code=status.HTTP_201_CREATED,
        summary=f"Add {section} to a profile",
    )
    async def add_child_endpoint(
        profile_id: UUID,
        data: create_schema,
        session: AsyncSession = Depends(get_session),
    ):
        instance = await add_child(session, profile_id, section, data)
        if instance is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        return response_schema.model_validate(instance, from_attributes=True)

    @router.get(
        f"/profiles/{{profile_id}}/{section}",
        response_model=List[response_schema],
        summary=f"List {section} for a profile",
    )
    async def list_children_endpoint(
        profile_id: UUID,
        session: AsyncSession = Depends(get_session),
    ):
        items = await list_children(session, profile_id, section)
        return [response_schema.model_validate(i, from_attributes=True) for i in items]

    @router.put(
        f"/profiles/{{profile_id}}/{section}/{{child_id}}",
        response_model=response_schema,
        summary=f"Update a {section} record",
    )
    async def update_child_endpoint(
        profile_id: UUID,
        child_id: UUID,
        data: update_schema,
        session: AsyncSession = Depends(get_session),
    ):
        instance = await update_child(session, profile_id, section, child_id, data)
        if instance is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return response_schema.model_validate(instance, from_attributes=True)

    @router.delete(
        f"/profiles/{{profile_id}}/{section}/{{child_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
        summary=f"Delete a {section} record",
    )
    async def delete_child_endpoint(
        profile_id: UUID,
        child_id: UUID,
        session: AsyncSession = Depends(get_session),
    ):
        deleted = await delete_child(session, profile_id, section, child_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Record not found")
        return None

    return add_child_endpoint, list_children_endpoint


# Register child routes for all sections.
_child_routes("education", EducationCreate, EducationResponse, EducationUpdate)
_child_routes("skills", SkillCreate, SkillResponse, SkillUpdate)
_child_routes("projects", ProjectCreate, ProjectResponse, ProjectUpdate)
_child_routes("experience", ExperienceCreate, ExperienceResponse, ExperienceUpdate)
_child_routes(
    "career-goals", CareerGoalCreate, CareerGoalResponse, CareerGoalUpdate
)
