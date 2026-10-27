"""Agent output schemas.

Agent outputs use Pydantic schemas so results are never unvalidated arbitrary
JSON. These schemas are shared between agents, the orchestrator, and the API.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProfileSummary(BaseModel):
    """Deterministic profile summary produced by the Profile Agent.

    Only information present in the retrieved profile is reported. Missing
    information is listed explicitly rather than fabricated.
    """

    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="UUID of the summarized profile.")
    overview: str = Field(..., description="Plain-language summary of the profile.")
    strengths: list[str] = Field(
        default_factory=list, description="Observed strengths from the profile."
    )
    notable_skills: list[str] = Field(
        default_factory=list, description="Skills explicitly present in the profile."
    )
    experience_highlights: list[str] = Field(
        default_factory=list, description="Highlights from work/project experience."
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Information that is absent or ambiguous in the profile.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Provider-neutral metadata."
    )


class CapabilityOutput(BaseModel):
    """Generic wrapper for structured agent output."""

    model_config = ConfigDict(frozen=True)

    capability: str
    output: dict[str, Any]
    agent_name: str


class SkillMatchDetail(BaseModel):
    """A single skill comparison result."""

    model_config = ConfigDict(frozen=True)

    skill_name: str
    category: str | None = None
    importance: str
    user_level: str | None = None
    required_level: str | None = None
    status: str  # MATCHED / PARTIAL / MISSING
    score: float
    reason: str


class CareerAnalysis(BaseModel):
    """Typed output from the Career Agent."""

    model_config = ConfigDict(frozen=True)

    career_id: str
    career_title: str
    fit_score: float
    fit_summary: str
    strengths: list[str] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    recommended_focus: list[str] = Field(default_factory=list)
    relevant_projects: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillGapAnalysis(BaseModel):
    """Typed output from the Skill Gap Agent."""

    model_config = ConfigDict(frozen=True)

    career_id: str
    career_title: str
    overall_score: float
    priority_gaps: list[str] = Field(default_factory=list)
    matched_strengths: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "ProfileSummary",
    "CapabilityOutput",
    "SkillMatchDetail",
    "CareerAnalysis",
    "SkillGapAnalysis",
]
