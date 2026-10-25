"""Pydantic schemas for profiles and their child records.

Naming convention:
- *Create  : request body for creating a resource
- *Update  : request body for updating a resource
- *Response: response body returned to the client
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

PROFILE_STATUSES = ("DRAFT", "REVIEW", "CONFIRMED")
PROFICIENCIES = ("BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT")
SOURCES = ("USER_CONFIRMED", "DOCUMENT_EXTRACTED", "SYSTEM_INFERRED")


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


class ProfileBase(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=200)
    headline: Optional[str] = Field(default=None, max_length=300)
    email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=50)
    location: Optional[str] = Field(default=None, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=2000)
    profile_status: Optional[str] = Field(default="DRAFT")

    @field_validator("profile_status")
    @classmethod
    def _validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PROFILE_STATUSES:
            raise ValueError(
                f"profile_status must be one of {', '.join(PROFILE_STATUSES)}"
            )
        return v


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=200)
    headline: Optional[str] = Field(default=None, max_length=300)
    email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=50)
    location: Optional[str] = Field(default=None, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=2000)
    profile_status: Optional[str] = None

    @field_validator("profile_status")
    @classmethod
    def _validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PROFILE_STATUSES:
            raise ValueError(
                f"profile_status must be one of {', '.join(PROFILE_STATUSES)}"
            )
        return v


class ProfileResponse(ProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    created_at: date  # type: ignore[assignment]  # Pydantic coerces datetime
    updated_at: date


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------


class EducationBase(BaseModel):
    institution: str = Field(..., min_length=1, max_length=200)
    degree: Optional[str] = Field(default=None, max_length=200)
    field_of_study: Optional[str] = Field(default=None, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _check_dates(self) -> "EducationBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class EducationCreate(EducationBase):
    pass


class EducationUpdate(EducationBase):
    institution: Optional[str] = Field(default=None, min_length=1, max_length=200)


class EducationResponse(EducationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    created_at: date


# ---------------------------------------------------------------------------
# Skill
# ---------------------------------------------------------------------------


class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=100)
    proficiency: Optional[str] = Field(default=None, max_length=20)
    years_experience: Optional[float] = Field(default=None, ge=0, le=60)
    source: str = Field(default="USER_CONFIRMED")

    @field_validator("proficiency")
    @classmethod
    def _validate_proficiency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PROFICIENCIES:
            raise ValueError(
                f"proficiency must be one of {', '.join(PROFICIENCIES)}"
            )
        return v

    @field_validator("source")
    @classmethod
    def _validate_source(cls, v: str) -> str:
        if v not in SOURCES:
            raise ValueError(f"source must be one of {', '.join(SOURCES)}")
        return v


class SkillCreate(SkillBase):
    pass


class SkillUpdate(SkillBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)


class SkillResponse(SkillBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    created_at: date


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    technologies: Optional[List[str]] = Field(default=None)
    role: Optional[str] = Field(default=None, max_length=100)
    outcomes: Optional[str] = Field(default=None, max_length=2000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    source: str = Field(default="USER_CONFIRMED")

    @field_validator("source")
    @classmethod
    def _validate_source(cls, v: str) -> str:
        if v not in SOURCES:
            raise ValueError(f"source must be one of {', '.join(SOURCES)}")
        return v

    @model_validator(mode="after")
    def _check_dates(self) -> "ProjectBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    created_at: date


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------


class ExperienceBase(BaseModel):
    organization: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    achievements: Optional[str] = Field(default=None, max_length=2000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    source: str = Field(default="USER_CONFIRMED")

    @field_validator("source")
    @classmethod
    def _validate_source(cls, v: str) -> str:
        if v not in SOURCES:
            raise ValueError(f"source must be one of {', '.join(SOURCES)}")
        return v

    @model_validator(mode="after")
    def _check_dates(self) -> "ExperienceBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceUpdate(ExperienceBase):
    organization: Optional[str] = Field(default=None, min_length=1, max_length=200)
    role: Optional[str] = Field(default=None, min_length=1, max_length=200)


class ExperienceResponse(ExperienceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    created_at: date


# ---------------------------------------------------------------------------
# CareerGoal
# ---------------------------------------------------------------------------


class CareerGoalBase(BaseModel):
    target_role: str = Field(..., min_length=1, max_length=200)
    target_industry: Optional[str] = Field(default=None, max_length=100)
    target_domain: Optional[str] = Field(default=None, max_length=100)
    goal_description: Optional[str] = Field(default=None, max_length=1000)
    priority: int = Field(default=1, ge=1)


class CareerGoalCreate(CareerGoalBase):
    pass


class CareerGoalUpdate(CareerGoalBase):
    target_role: Optional[str] = Field(default=None, min_length=1, max_length=200)


class CareerGoalResponse(CareerGoalBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    created_at: date


# ---------------------------------------------------------------------------
# Composite: full profile with children
# ---------------------------------------------------------------------------


class ProfileDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    full_name: Optional[str] = None
    headline: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    profile_status: str
    created_at: date
    updated_at: date

    education: List[EducationResponse] = []
    skills: List[SkillResponse] = []
    projects: List[ProjectResponse] = []
    experience: List[ExperienceResponse] = []
    career_goals: List[CareerGoalResponse] = []


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ValidationErrorDetail(BaseModel):
    field: str
    code: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    errors: List[ValidationErrorDetail] = []
    warnings: List[ValidationErrorDetail] = []


# ---------------------------------------------------------------------------
# Resume extraction
# ---------------------------------------------------------------------------


class ResumeExtractResponse(BaseModel):
    extracted_text: str
    file_name: str
    content_type: str
    size_bytes: int
    character_count: int
    word_count: int


# ---------------------------------------------------------------------------
# Profile draft (resume-derived, not yet confirmed)
# ---------------------------------------------------------------------------


class ExtractionMetadata(BaseModel):
    source_type: str  # "RESUME_PDF" | "RESUME_DOCX" | "RESUME_TXT" | "MANUAL"
    source_file_name: Optional[str] = None
    extraction_warnings: List[str] = []


class ProfileDraft(BaseModel):
    """A structured profile draft produced from a resume or manual input.

    The draft is NOT automatically persisted as confirmed user data. It is
    presented for review before the user confirms it.
    """

    profile: ProfileCreate
    education: List[EducationCreate] = []
    skills: List[SkillCreate] = []
    projects: List[ProjectCreate] = []
    experience: List[ExperienceCreate] = []
    career_goals: List[CareerGoalCreate] = []
    extraction_metadata: ExtractionMetadata
