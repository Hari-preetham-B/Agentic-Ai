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


__all__ = ["ProfileSummary", "CapabilityOutput"]
