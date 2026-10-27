"""Pydantic schemas for career knowledge API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CareerSkillSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_name: str
    category: str | None = None
    importance: str
    minimum_level: str | None = None
    description: str | None = None


class CareerToolSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_name: str
    category: str | None = None
    importance: str


class CareerProjectSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_type: str
    description: str
    skills_demonstrated: list[str] | None = None
    difficulty: str | None = None


class CareerSourceSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    publisher: str
    url: str | None = None
    source_type: str
    published_at: str | None = None
    reliability: str


class CareerResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    slug: str
    title: str
    domain: str
    summary: str | None = None
    description: str | None = None
    education_expectations: dict | None = None
    experience_expectations: dict | None = None
    skills: list[CareerSkillSchema] = Field(default_factory=list)
    tools: list[CareerToolSchema] = Field(default_factory=list)
    projects: list[CareerProjectSchema] = Field(default_factory=list)
    sources: list[CareerSourceSchema] = Field(default_factory=list)


class CareerListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    careers: list[CareerResponse]


class CareerRequirementsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    career_id: str
    slug: str
    title: str
    domain: str
    skills: list[CareerSkillSchema] = Field(default_factory=list)
    tools: list[CareerToolSchema] = Field(default_factory=list)
    projects: list[CareerProjectSchema] = Field(default_factory=list)
    sources: list[CareerSourceSchema] = Field(default_factory=list)


class CareerRecommendationItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    career_id: str
    career_title: str
    career_domain: str
    fit_score: float
    matched_core_skills: list[str] = Field(default_factory=list)
    top_gaps: list[str] = Field(default_factory=list)
    reason: str


class CareerRecommendationsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    recommendations: list[CareerRecommendationItem]


class CareerRecommendationsRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str
    limit: int = Field(default=5, ge=1, le=10)


__all__ = [
    "CareerSkillSchema",
    "CareerToolSchema",
    "CareerProjectSchema",
    "CareerSourceSchema",
    "CareerResponse",
    "CareerListResponse",
    "CareerRequirementsResponse",
    "CareerRecommendationItem",
    "CareerRecommendationsResponse",
    "CareerRecommendationsRequest",
]
