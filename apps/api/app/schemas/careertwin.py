"""CareerTwin unified state models.

These Pydantic models represent the unified CareerTwin state — a structured
aggregation over profile, career, skill-gap, learning, interview, and evidence
data. They are NOT database models; they are computed views.

Source-of-truth hierarchy:
1. User-confirmed profile data
2. User-confirmed edits
3. Uploaded/documented information
4. Deterministic derived calculations
5. Evidence-backed external information
6. Interview performance signals
7. Agent inference
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Source classification
# ---------------------------------------------------------------------------

SourceType = Literal[
    "CONFIRMED",
    "DOCUMENTED",
    "DERIVED",
    "EVIDENCE_BACKED",
    "PERFORMANCE_SIGNAL",
    "INFERRED",
]


# ---------------------------------------------------------------------------
# CareerTwin state components
# ---------------------------------------------------------------------------


class CareerTwinSkill(BaseModel):
    """A skill in the CareerTwin state with source classification."""

    model_config = ConfigDict(frozen=True)

    name: str
    category: str | None = None
    proficiency: str | None = None
    source: SourceType = "CONFIRMED"
    years_experience: float | None = None


class CareerTwinCareerFit(BaseModel):
    """Career fit analysis within CareerTwin state."""

    model_config = ConfigDict(frozen=True)

    career_id: str
    career_title: str
    fit_score: float
    readiness_level: str  # NOT_READY, EARLY, DEVELOPING, COMPETITIVE, STRONG
    strongest_areas: list[str] = Field(default_factory=list)
    weakest_areas: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    rationale: str = ""


class CareerTwinSkillGap(BaseModel):
    """A skill gap within CareerTwin state."""

    model_config = ConfigDict(frozen=True)

    skill_name: str
    importance: str
    current_level: str | None = None
    required_level: str | None = None
    status: str  # MATCHED, PARTIAL, MISSING
    priority: str | None = None  # P0, P1, P2


class CareerTwinRoadmapSummary(BaseModel):
    """Roadmap summary within CareerTwin state."""

    model_config = ConfigDict(frozen=True)

    roadmap_id: str | None = None
    total_skills: int = 0
    p0_count: int = 0
    p1_count: int = 0
    p2_count: int = 0
    total_estimated_hours: float = 0.0
    status: str = "NONE"
    generated_at: str | None = None
    stale: bool = False


class CareerTwinInterviewSummary(BaseModel):
    """Interview performance summary within CareerTwin state."""

    model_config = ConfigDict(frozen=True)

    sessions_count: int = 0
    latest_overall_score: float | None = None
    skill_performance: list[dict[str, Any]] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommended_skills: list[str] = Field(default_factory=list)
    last_interview_at: str | None = None


class CareerTwinEvidenceSummary(BaseModel):
    """Evidence summary within CareerTwin state."""

    model_config = ConfigDict(frozen=True)

    total_claims: int = 0
    supported_count: int = 0
    inferred_count: int = 0
    uncertain_count: int = 0
    contradicted_count: int = 0
    last_verified_at: str | None = None


class CareerTwinInsight(BaseModel):
    """A cross-system insight in the CareerTwin state."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: str
    severity: str  # INFO, WARNING, CRITICAL
    title: str
    reason: str
    affected_entity: str | None = None
    affected_skill: str | None = None
    affected_career: str | None = None
    source_signals: list[str] = Field(default_factory=list)
    recommended_action: str | None = None
    classification: SourceType = "DERIVED"


class CareerTwinConflict(BaseModel):
    """A cross-system conflict in the CareerTwin state."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: str
    severity: str
    title: str
    description: str
    affected_entity: str | None = None
    affected_skill: str | None = None
    source_a: str | None = None
    source_b: str | None = None
    resolution: str | None = None


class CareerTwinStaleState(BaseModel):
    """Freshness information for derived state."""

    model_config = ConfigDict(frozen=True)

    component: str
    generated_at: str | None = None
    source_updated_at: str | None = None
    is_stale: bool = False
    reason: str | None = None


# ---------------------------------------------------------------------------
# Unified CareerTwin state
# ---------------------------------------------------------------------------


class CareerTwinNarrative(BaseModel):
    """Typed narrative output from the CareerTwin Agent's LLM layer.

    All fields are generated by the LLM for explanation purposes only.
    They do NOT affect any deterministic scores, readiness, or state.
    """

    model_config = ConfigDict(frozen=True)

    summary: str = Field(..., description="Personalized CareerTwin summary.")
    current_position: str = Field(
        ..., description="Concise explanation of current career position."
    )
    key_strengths: list[str] = Field(
        default_factory=list, description="Key strengths identified."
    )
    priority_gaps: list[str] = Field(
        default_factory=list, description="Priority skill gaps."
    )
    recommended_next_actions: list[str] = Field(
        default_factory=list, description="Recommended next actions."
    )
    interview_observation: str = Field(
        default="", description="Observation about interview performance."
    )
    roadmap_observation: str = Field(
        default="", description="Observation about roadmap progress."
    )


class CareerTwinState(BaseModel):
    """Unified CareerTwin state — a structured aggregation over all systems."""

    model_config = ConfigDict(frozen=True)

    # Profile summary
    profile_id: str
    profile_name: str | None = None
    profile_status: str = "DRAFT"
    headline: str | None = None

    # Education
    education: list[dict[str, Any]] = Field(default_factory=list)

    # Experience
    experience: list[dict[str, Any]] = Field(default_factory=list)

    # Projects
    projects: list[dict[str, Any]] = Field(default_factory=list)

    # Confirmed skills (user-confirmed)
    confirmed_skills: list[CareerTwinSkill] = Field(default_factory=list)

    # Documented skills (extracted from documents)
    documented_skills: list[CareerTwinSkill] = Field(default_factory=list)

    # Target careers
    target_careers: list[str] = Field(default_factory=list)
    active_target_career: str | None = None

    # Career fit
    career_fit: CareerTwinCareerFit | None = None

    # Skill gaps
    skill_gaps: list[CareerTwinSkillGap] = Field(default_factory=list)

    # Roadmap
    roadmap_summary: CareerTwinRoadmapSummary = Field(
        default_factory=CareerTwinRoadmapSummary
    )

    # Interview performance
    interview_summary: CareerTwinInterviewSummary = Field(
        default_factory=CareerTwinInterviewSummary
    )

    # Evidence
    evidence_summary: CareerTwinEvidenceSummary = Field(
        default_factory=CareerTwinEvidenceSummary
    )

    # Cross-system insights
    insights: list[CareerTwinInsight] = Field(default_factory=list)

    # Conflicts
    conflicts: list[CareerTwinConflict] = Field(default_factory=list)

    # Stale state
    stale_components: list[CareerTwinStaleState] = Field(default_factory=list)

    # Readiness
    readiness_level: str = "NOT_READY"
    readiness_score: float = 0.0

    # Last updated
    last_updated_at: str | None = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class CareerTwinInsightsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    insights: list[CareerTwinInsight]


class CareerTwinConflictsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    conflicts: list[CareerTwinConflict]


class CareerTwinReadinessResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    readiness_level: str
    readiness_score: float
    rationale: str
    blockers: list[str] = Field(default_factory=list)


class CareerTwinStaleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    stale_components: list[CareerTwinStaleState]


class CareerTwinRefreshRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str
    force: bool = False


class CareerTwinRefreshResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    refreshed_components: list[str]
    unchanged_components: list[str]
    message: str


__all__ = [
    "CareerTwinCareerFit",
    "CareerTwinConflict",
    "CareerTwinConflictsResponse",
    "CareerTwinEvidenceSummary",
    "CareerTwinInsight",
    "CareerTwinInsightsResponse",
    "CareerTwinInterviewSummary",
    "CareerTwinReadinessResponse",
    "CareerTwinRoadmapSummary",
    "CareerTwinSkill",
    "CareerTwinSkillGap",
    "CareerTwinStaleResponse",
    "CareerTwinStaleState",
    "CareerTwinNarrative",
    "CareerTwinState",
    "CareerTwinRefreshRequest",
    "CareerTwinRefreshResponse",
    "SourceType",
]
