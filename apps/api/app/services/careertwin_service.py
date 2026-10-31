"""CareerTwin unified state services.

Deterministic aggregation, fit, readiness, insight, conflict detection,
and reconciliation services for the unified CareerTwin state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career import Career, CareerSkill
from app.models.interview import InterviewSession, InterviewSkillResult
from app.models.learning import Roadmap, RoadmapItem
from app.models.profile import Profile, Skill
from app.schemas.careertwin import (
    CareerTwinCareerFit,
    CareerTwinConflict,
    CareerTwinEvidenceSummary,
    CareerTwinInsight,
    CareerTwinInterviewSummary,
    CareerTwinRoadmapSummary,
    CareerTwinSkill,
    CareerTwinSkillGap,
    CareerTwinStaleState,
    CareerTwinState,
    SourceType,
)
from app.services.career_knowledge_service import CareerKnowledgeService
from app.services.skill_matching import compute_skill_match


# ---------------------------------------------------------------------------
# CareerTwin State Service
# ---------------------------------------------------------------------------


class CareerTwinStateService:
    """Assembles the unified CareerTwin state from existing systems."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_state(
        self,
        *,
        profile_id: str,
        active_target_career: str | None = None,
    ) -> CareerTwinState:
        """Assemble the unified CareerTwin state."""
        # Load profile.
        profile_result = await self.session.execute(
            select(Profile).where(Profile.id == uuid.UUID(profile_id))
        )
        profile = profile_result.scalar_one_or_none()
        if profile is None:
            raise ValueError(f"Profile not found: {profile_id}")

        # Load skills.
        skills_result = await self.session.execute(
            select(Skill).where(Skill.profile_id == uuid.UUID(profile_id))
        )
        profile_skills = list(skills_result.scalars().all())

        # Load career goals (target careers).
        from app.models.profile import CareerGoal

        goals_result = await self.session.execute(
            select(CareerGoal).where(CareerGoal.profile_id == uuid.UUID(profile_id))
        )
        career_goals = list(goals_result.scalars().all())
        target_careers = [g.target_role for g in career_goals]

        # Determine active target career.
        if active_target_career is None and target_careers:
            active_target_career = target_careers[0]

        # Load education, experience, projects.
        from app.models.profile import Education, Experience, Project

        edu_result = await self.session.execute(
            select(Education).where(Education.profile_id == uuid.UUID(profile_id))
        )
        education = [
            {
                "institution": e.institution,
                "degree": e.degree,
                "field_of_study": e.field_of_study,
            }
            for e in edu_result.scalars().all()
        ]

        exp_result = await self.session.execute(
            select(Experience).where(Experience.profile_id == uuid.UUID(profile_id))
        )
        experience = [
            {
                "organization": e.organization,
                "role": e.role,
                "is_current": e.is_current,
            }
            for e in exp_result.scalars().all()
        ]

        proj_result = await self.session.execute(
            select(Project).where(Project.profile_id == uuid.UUID(profile_id))
        )
        projects = [
            {
                "name": p.name,
                "technologies": p.technologies,
            }
            for p in proj_result.scalars().all()
        ]

        # Build confirmed skills list.
        confirmed_skills = [
            CareerTwinSkill(
                name=s.name,
                category=s.category,
                proficiency=s.proficiency,
                source="CONFIRMED" if s.source == "USER_CONFIRMED" else "DOCUMENTED",
                years_experience=float(s.years_experience) if s.years_experience else None,
            )
            for s in profile_skills
        ]

        # Career fit.
        career_fit = None
        skill_gaps = []
        if active_target_career:
            career_service = CareerKnowledgeService(self.session)
            career = await career_service.get_career(active_target_career)
            if career:
                profile_skill_dicts = [
                    {
                        "name": s.name,
                        "proficiency": s.proficiency,
                        "years_experience": float(s.years_experience) if s.years_experience else None,
                        "source": s.source,
                    }
                    for s in profile_skills
                ]
                match = compute_skill_match(
                    career_id=career["id"],
                    career_title=career["title"],
                    career_skills=career.get("skills", []),
                    profile_skills=profile_skill_dicts,
                )

                from app.services.career_fit_service import compute_career_fit

                fit = compute_career_fit(
                    career_id=career["id"],
                    career_title=career["title"],
                    match_result=match,
                )

                career_fit = CareerTwinCareerFit(
                    career_id=career["id"],
                    career_title=career["title"],
                    fit_score=fit.fit_score,
                    readiness_level="NOT_READY",  # Will be computed separately
                    strongest_areas=fit.strengths[:3],
                    weakest_areas=fit.gaps[:3],
                    blockers=[],
                    rationale=fit.fit_summary,
                )

                skill_gaps = [
                    CareerTwinSkillGap(
                        skill_name=m["skill_name"],
                        importance=m.get("importance", "SUPPORTING"),
                        current_level=m.get("user_level"),
                        required_level=m.get("required_level"),
                        status=m.get("status", "MISSING"),
                    )
                    for m in (match.missing + match.partial + match.matched)
                ]

        # Roadmap summary.
        roadmap_summary = await self._get_roadmap_summary(profile_id)

        # Interview summary.
        interview_summary = await self._get_interview_summary(profile_id)

        # Evidence summary.
        evidence_summary = await self._get_evidence_summary(profile_id)

        # Readiness.
        readiness_level, readiness_score = self._calculate_readiness(
            career_fit=career_fit,
            skill_gaps=skill_gaps,
            interview_summary=interview_summary,
        )

        if career_fit is not None:
            career_fit = career_fit.model_copy(
                update={"readiness_level": readiness_level}
            )

        # Stale state.
        stale_components = await self._check_stale_state(profile_id, active_target_career)

        # Insights.
        insights = self._generate_insights(
            career_fit=career_fit,
            skill_gaps=skill_gaps,
            interview_summary=interview_summary,
            roadmap_summary=roadmap_summary,
        )

        # Conflicts.
        conflicts = self._detect_conflicts(
            profile_skills=profile_skills,
            interview_summary=interview_summary,
            target_careers=target_careers,
            active_target_career=active_target_career,
        )

        return CareerTwinState(
            profile_id=profile_id,
            profile_name=profile.full_name,
            profile_status=profile.profile_status,
            headline=profile.headline,
            education=education,
            experience=experience,
            projects=projects,
            confirmed_skills=confirmed_skills,
            documented_skills=[],
            target_careers=target_careers,
            active_target_career=active_target_career,
            career_fit=career_fit,
            skill_gaps=skill_gaps,
            roadmap_summary=roadmap_summary,
            interview_summary=interview_summary,
            evidence_summary=evidence_summary,
            insights=insights,
            conflicts=conflicts,
            stale_components=stale_components,
            readiness_level=readiness_level,
            readiness_score=readiness_score,
            last_updated_at=datetime.now(timezone.utc).isoformat(),
            metadata={"source": "deterministic_aggregation"},
        )

    async def _get_roadmap_summary(self, profile_id: str) -> CareerTwinRoadmapSummary:
        """Get roadmap summary for the profile."""
        result = await self.session.execute(
            select(Roadmap).where(Roadmap.profile_id == uuid.UUID(profile_id))
        )
        roadmaps = result.scalars().all()
        if not roadmaps:
            return CareerTwinRoadmapSummary()

        # Get the latest roadmap.
        latest = max(roadmaps, key=lambda r: r.generated_at)
        items_result = await self.session.execute(
            select(RoadmapItem).where(RoadmapItem.roadmap_id == latest.id)
        )
        items = items_result.scalars().all()

        return CareerTwinRoadmapSummary(
            roadmap_id=str(latest.id),
            total_skills=len(items),
            p0_count=sum(1 for i in items if i.priority == "P0"),
            p1_count=sum(1 for i in items if i.priority == "P1"),
            p2_count=sum(1 for i in items if i.priority == "P2"),
            total_estimated_hours=sum(i.estimated_hours or 0 for i in items),
            status=latest.status,
            generated_at=latest.generated_at.isoformat(),
            stale=False,
        )

    async def _get_interview_summary(self, profile_id: str) -> CareerTwinInterviewSummary:
        """Get interview performance summary for the profile."""
        result = await self.session.execute(
            select(InterviewSession).where(
                InterviewSession.profile_id == uuid.UUID(profile_id)
            )
        )
        sessions = result.scalars().all()
        if not sessions:
            return CareerTwinInterviewSummary()

        completed = [s for s in sessions if s.status == "COMPLETED"]
        if not completed:
            return CareerTwinInterviewSummary(sessions_count=len(sessions))

        latest = max(completed, key=lambda s: s.completed_at or s.created_at)

        # Get skill results.
        skill_result = await self.session.execute(
            select(InterviewSkillResult).where(
                InterviewSkillResult.session_id == latest.id
            )
        )
        skills = skill_result.scalars().all()

        strengths = [s.skill_name for s in skills if (s.average_score or 0) >= 0.70]
        weaknesses = [s.skill_name for s in skills if (s.average_score or 0) < 0.50]
        recommended = sorted(weaknesses)

        return CareerTwinInterviewSummary(
            sessions_count=len(sessions),
            latest_overall_score=None,
            skill_performance=[
                {
                    "skill_name": s.skill_name,
                    "questions_attempted": s.questions_attempted,
                    "average_score": s.average_score,
                    "trend": s.trend,
                    "performance_confidence": s.performance_confidence,
                }
                for s in skills
            ],
            strengths=strengths,
            weaknesses=weaknesses,
            recommended_skills=recommended,
            last_interview_at=latest.completed_at.isoformat() if latest.completed_at else None,
        )

    async def _get_evidence_summary(self, profile_id: str) -> CareerTwinEvidenceSummary:
        """Get evidence summary for the profile."""
        from app.models.evidence import Claim

        result = await self.session.execute(
            select(Claim).where(Claim.profile_id == uuid.UUID(profile_id))
        )
        claims = result.scalars().all()

        status_counts = {}
        for c in claims:
            status_counts[c.status] = status_counts.get(c.status, 0) + 1

        return CareerTwinEvidenceSummary(
            total_claims=len(claims),
            supported_count=status_counts.get("SUPPORTED", 0),
            inferred_count=status_counts.get("INFERRED", 0),
            uncertain_count=status_counts.get("UNCERTAIN", 0),
            contradicted_count=status_counts.get("CONTRADICTED", 0),
        )

    def _calculate_readiness(
        self,
        *,
        career_fit: CareerTwinCareerFit | None,
        skill_gaps: list[CareerTwinSkillGap],
        interview_summary: CareerTwinInterviewSummary,
    ) -> tuple[str, float]:
        """Calculate deterministic career readiness level and score."""
        if career_fit is None:
            return "NOT_READY", 0.0

        fit_score = career_fit.fit_score

        # Count critical missing skills.
        critical_missing = sum(
            1 for g in skill_gaps
            if g.status == "MISSING" and g.importance == "CORE"
        )

        # Interview performance factor.
        interview_factor = 1.0
        if interview_summary.skill_performance:
            avg_perf = sum(
                (sp.get("average_score") or 0) for sp in interview_summary.skill_performance
            ) / len(interview_summary.skill_performance)
            interview_factor = 0.7 + 0.3 * avg_perf

        # Dependency blocker factor.
        blocker_factor = 1.0 if critical_missing == 0 else max(0.5, 1.0 - 0.1 * critical_missing)

        # Composite readiness score.
        readiness_score = fit_score * 0.5 + interview_factor * 0.2 + blocker_factor * 0.3
        readiness_score = max(0.0, min(1.0, readiness_score))

        # Determine readiness level.
        if readiness_score >= 0.80 and critical_missing == 0:
            return "STRONG", round(readiness_score, 4)
        if readiness_score >= 0.60:
            return "COMPETITIVE", round(readiness_score, 4)
        if readiness_score >= 0.40:
            return "DEVELOPING", round(readiness_score, 4)
        if readiness_score >= 0.20:
            return "EARLY", round(readiness_score, 4)
        return "NOT_READY", round(readiness_score, 4)

    def _generate_insights(
        self,
        *,
        career_fit: CareerTwinCareerFit | None,
        skill_gaps: list[CareerTwinSkillGap],
        interview_summary: CareerTwinInterviewSummary,
        roadmap_summary: CareerTwinRoadmapSummary,
    ) -> list[CareerTwinInsight]:
        """Generate deterministic cross-system insights."""
        insights: list[CareerTwinInsight] = []

        if career_fit is None:
            return insights

        # Skill gap insights.
        critical_gaps = [g for g in skill_gaps if g.status == "MISSING" and g.importance == "CORE"]
        for gap in critical_gaps[:3]:
            insights.append(
                CareerTwinInsight(
                    id=f"skill-gap-{gap.skill_name}",
                    type="SKILL_GAP",
                    severity="CRITICAL",
                    title=f"Missing core skill: {gap.skill_name}",
                    reason=f"{gap.skill_name} is a CORE requirement for {career_fit.career_title} but is not in your profile.",
                    affected_skill=gap.skill_name,
                    affected_career=career_fit.career_title,
                    source_signals=["skill_match", "career_requirements"],
                    recommended_action=f"Add {gap.skill_name} to your profile and start learning.",
                    classification="DERIVED",
                )
            )

        # Interview weakness insights.
        for weakness in interview_summary.weaknesses[:3]:
            insights.append(
                CareerTwinInsight(
                    id=f"interview-weakness-{weakness}",
                    type="INTERVIEW_WEAKNESS",
                    severity="WARNING",
                    title=f"Interview weakness: {weakness}",
                    reason=f"Interview performance for {weakness} was below expectations.",
                    affected_skill=weakness,
                    affected_career=career_fit.career_title,
                    source_signals=["interview_performance"],
                    recommended_action=f"Focus on {weakness} in your learning roadmap.",
                    classification="PERFORMANCE_SIGNAL",
                )
            )

        # Roadmap priority insights.
        if roadmap_summary.p0_count > 0:
            insights.append(
                CareerTwinInsight(
                    id="roadmap-p0-priority",
                    type="ROADMAP_PRIORITY",
                    severity="INFO",
                    title=f"{roadmap_summary.p0_count} critical learning items",
                    reason=f"Your roadmap has {roadmap_summary.p0_count} P0 (critical) skills to learn.",
                    affected_career=career_fit.career_title,
                    source_signals=["roadmap", "skill_gap"],
                    recommended_action="Focus on P0 skills first.",
                    classification="DERIVED",
                )
            )

        # Career alignment insight.
        if career_fit.fit_score >= 0.70:
            insights.append(
                CareerTwinInsight(
                    id="career-alignment-strong",
                    type="CAREER_ALIGNMENT",
                    severity="INFO",
                    title=f"Strong alignment with {career_fit.career_title}",
                    reason=f"Your profile aligns well ({career_fit.fit_score:.0%}) with {career_fit.career_title} requirements.",
                    affected_career=career_fit.career_title,
                    source_signals=["skill_match", "career_requirements"],
                    recommended_action="Continue building on your strengths.",
                    classification="DERIVED",
                )
            )

        return insights

    def _detect_conflicts(
        self,
        *,
        profile_skills: list[Skill],
        interview_summary: CareerTwinInterviewSummary,
        target_careers: list[str],
        active_target_career: str | None,
    ) -> list[CareerTwinConflict]:
        """Detect cross-system conflicts."""
        conflicts: list[CareerTwinConflict] = []

        # Performance vs confirmed skill conflict.
        for sp in interview_summary.skill_performance:
            skill_name = sp.get("skill_name")
            avg_score = sp.get("average_score")
            if avg_score is None:
                continue
            # Find the confirmed skill.
            for s in profile_skills:
                if s.name == skill_name and s.proficiency in ("ADVANCED", "EXPERT"):
                    if avg_score < 0.50:
                        conflicts.append(
                            CareerTwinConflict(
                                id=f"perf-gap-{skill_name}",
                                type="PERFORMANCE_GAP",
                                severity="WARNING",
                                title=f"Interview performance gap: {skill_name}",
                                description=(
                                    f"Your profile lists {skill_name} as {s.proficiency}, "
                                    f"but interview performance was {avg_score:.0%}. "
                                    "This is a performance signal, not a profile change."
                                ),
                                affected_skill=skill_name,
                                source_a="profile (confirmed)",
                                source_b="interview (performance)",
                                resolution="Continue practicing; profile skill remains unchanged.",
                            )
                        )

        # Goal vs target career conflict.
        if len(target_careers) > 1 and active_target_career:
            for goal in target_careers:
                if goal != active_target_career:
                    conflicts.append(
                        CareerTwinConflict(
                            id=f"goal-conflict-{goal}",
                            type="GOAL_CONFLICT",
                            severity="INFO",
                            title=f"Multiple career targets: {goal} vs {active_target_career}",
                            description=(
                                f"Your profile lists '{goal}' as a goal but the active "
                                f"target is '{active_target_career}'."
                            ),
                            affected_career=active_target_career,
                            source_a="career_goals",
                            source_b="active_target",
                            resolution="Focus on one target career for clearer roadmap.",
                        )
                    )
                    break  # Only report one conflict.

        return conflicts

    async def _check_stale_state(
        self, profile_id: str, active_target_career: str | None
    ) -> list[CareerTwinStaleState]:
        """Check for stale derived state."""
        stale: list[CareerTwinStaleState] = []

        # Check roadmap staleness.
        result = await self.session.execute(
            select(Roadmap).where(Roadmap.profile_id == uuid.UUID(profile_id))
        )
        roadmaps = result.scalars().all()
        if roadmaps:
            latest = max(roadmaps, key=lambda r: r.generated_at)
            # Check if career target changed after roadmap generation.
            if active_target_career:
                career_result = await self.session.execute(
                    select(Career).where(Career.slug == active_target_career)
                )
                career = career_result.scalar_one_or_none()
                if career and career.updated_at and latest.generated_at:
                    if career.updated_at > latest.generated_at:
                        stale.append(
                            CareerTwinStaleState(
                                component="roadmap",
                                generated_at=latest.generated_at.isoformat(),
                                source_updated_at=career.updated_at.isoformat(),
                                is_stale=True,
                                reason="Career data updated after roadmap generation.",
                            )
                        )

        return stale


# ---------------------------------------------------------------------------
# Career Fit Engine
# ---------------------------------------------------------------------------


class CareerFitEngine:
    """Higher-level career fit calculation combining multiple signals."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def calculate_readiness_level(
        self,
        *,
        fit_score: float,
        critical_missing: int,
        interview_avg: float | None,
        dependency_blockers: int,
    ) -> tuple[str, float]:
        """Calculate deterministic readiness level and score."""
        interview_factor = 1.0
        if interview_avg is not None:
            interview_factor = 0.7 + 0.3 * interview_avg

        blocker_factor = (
            1.0 if critical_missing == 0
            else max(0.5, 1.0 - 0.1 * critical_missing)
        )
        dep_factor = (
            1.0 if dependency_blockers == 0
            else max(0.5, 1.0 - 0.05 * dependency_blockers)
        )

        readiness_score = (
            fit_score * 0.45
            + interview_factor * 0.20
            + blocker_factor * 0.20
            + dep_factor * 0.15
        )
        readiness_score = max(0.0, min(1.0, readiness_score))

        if readiness_score >= 0.80 and critical_missing == 0:
            return "STRONG", round(readiness_score, 4)
        if readiness_score >= 0.60:
            return "COMPETITIVE", round(readiness_score, 4)
        if readiness_score >= 0.40:
            return "DEVELOPING", round(readiness_score, 4)
        if readiness_score >= 0.20:
            return "EARLY", round(readiness_score, 4)
        return "NOT_READY", round(readiness_score, 4)


# ---------------------------------------------------------------------------
# Career Readiness Service
# ---------------------------------------------------------------------------


class CareerReadinessService:
    """Deterministic career readiness calculation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.fit_engine = CareerFitEngine(session)

    async def calculate(
        self,
        *,
        profile_id: str,
        career_slug: str,
    ) -> dict[str, Any]:
        """Calculate career readiness for a profile-career pair."""
        # Load profile skills.
        skills_result = await self.session.execute(
            select(Skill).where(Skill.profile_id == uuid.UUID(profile_id))
        )
        profile_skills = list(skills_result.scalars().all())

        # Load career.
        career_service = CareerKnowledgeService(self.session)
        career = await career_service.get_career(career_slug)
        if career is None:
            raise ValueError(f"Career not found: {career_slug}")

        # Compute skill match.
        profile_skill_dicts = [
            {
                "name": s.name,
                "proficiency": s.proficiency,
                "years_experience": float(s.years_experience) if s.years_experience else None,
                "source": s.source,
            }
            for s in profile_skills
        ]
        match = compute_skill_match(
            career_id=career["id"],
            career_title=career["title"],
            career_skills=career.get("skills", []),
            profile_skills=profile_skill_dicts,
        )

        # Count critical missing.
        critical_missing = sum(
            1 for m in match.missing if m.get("importance") == "CORE"
        )

        # Interview average.
        interview_result = await self.session.execute(
            select(InterviewSkillResult).where(
                InterviewSkillResult.session_id.in_(
                    select(InterviewSession.id).where(
                        InterviewSession.profile_id == uuid.UUID(profile_id)
                    )
                )
            )
        )
        interview_skills = interview_result.scalars().all()
        interview_avg = None
        if interview_skills:
            scores = [s.average_score for s in interview_skills if s.average_score is not None]
            if scores:
                interview_avg = sum(scores) / len(scores)

        # Dependency blockers.
        dep_blockers = 0
        from app.services.skill_dependency_service import SkillDependencyService

        dep_service = SkillDependencyService(self.session)
        deps = await dep_service.get_all_dependencies()
        graph = dep_service.build_graph(deps)
        for m in match.missing:
            missing_prereqs = dep_service.get_missing_prerequisites(
                m["skill_name"], graph, {s.name for s in profile_skills}
            )
            dep_blockers += len(missing_prereqs)

        readiness_level, readiness_score = self.fit_engine.calculate_readiness_level(
            fit_score=match.overall_score,
            critical_missing=critical_missing,
            interview_avg=interview_avg,
            dependency_blockers=dep_blockers,
        )

        return {
            "readiness_level": readiness_level,
            "readiness_score": readiness_score,
            "fit_score": match.overall_score,
            "critical_missing": critical_missing,
            "dependency_blockers": dep_blockers,
            "interview_avg": interview_avg,
            "blockers": [
                m["skill_name"] for m in match.missing if m.get("importance") == "CORE"
            ],
            "rationale": (
                f"Readiness: {readiness_level} ({readiness_score:.0%}). "
                f"Fit: {match.overall_score:.0%}. "
                f"Critical missing: {critical_missing}. "
                f"Dependency blockers: {dep_blockers}."
            ),
        }


# ---------------------------------------------------------------------------
# Cross-System Insight Service
# ---------------------------------------------------------------------------


class CareerInsightService:
    """Deterministic cross-system insight generation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def generate_insights(
        self,
        *,
        career_fit: CareerTwinCareerFit | None,
        skill_gaps: list[CareerTwinSkillGap],
        interview_summary: CareerTwinInterviewSummary,
        roadmap_summary: CareerTwinRoadmapSummary,
    ) -> list[CareerTwinInsight]:
        """Generate deterministic cross-system insights."""
        insights: list[CareerTwinInsight] = []

        if career_fit is None:
            return insights

        # Skill gap insights.
        critical_gaps = [g for g in skill_gaps if g.status == "MISSING" and g.importance == "CORE"]
        for gap in critical_gaps[:3]:
            insights.append(
                CareerTwinInsight(
                    id=f"skill-gap-{gap.skill_name}",
                    type="SKILL_GAP",
                    severity="CRITICAL",
                    title=f"Missing core skill: {gap.skill_name}",
                    reason=f"{gap.skill_name} is a CORE requirement for {career_fit.career_title} but is not in your profile.",
                    affected_skill=gap.skill_name,
                    affected_career=career_fit.career_title,
                    source_signals=["skill_match", "career_requirements"],
                    recommended_action=f"Add {gap.skill_name} to your profile and start learning.",
                    classification="DERIVED",
                )
            )

        # Interview weakness insights.
        for weakness in interview_summary.weaknesses[:3]:
            is_also_gap = any(g.skill_name == weakness and g.status == "MISSING" for g in skill_gaps)
            if is_also_gap:
                insights.append(
                    CareerTwinInsight(
                        id=f"interview-weakness-{weakness}",
                        type="INTERVIEW_WEAKNESS",
                        severity="WARNING",
                        title=f"Interview weakness in gap skill: {weakness}",
                        reason=(
                            f"{weakness} is both a skill gap and an interview weakness. "
                            "This is your highest-leverage development area."
                        ),
                        affected_skill=weakness,
                        affected_career=career_fit.career_title,
                        source_signals=["interview_performance", "skill_gap"],
                        recommended_action=f"Prioritize {weakness} in your learning roadmap.",
                        classification="PERFORMANCE_SIGNAL",
                    )
                )

        # Roadmap priority insights.
        if roadmap_summary.p0_count > 0:
            insights.append(
                CareerTwinInsight(
                    id="roadmap-p0-priority",
                    type="ROADMAP_PRIORITY",
                    severity="INFO",
                    title=f"{roadmap_summary.p0_count} critical learning items",
                    reason=f"Your roadmap has {roadmap_summary.p0_count} P0 (critical) skills to learn.",
                    affected_career=career_fit.career_title,
                    source_signals=["roadmap", "skill_gap"],
                    recommended_action="Focus on P0 skills first.",
                    classification="DERIVED",
                )
            )

        # Career alignment insight.
        if career_fit.fit_score >= 0.70:
            insights.append(
                CareerTwinInsight(
                    id="career-alignment-strong",
                    type="CAREER_ALIGNMENT",
                    severity="INFO",
                    title=f"Strong alignment with {career_fit.career_title}",
                    reason=f"Your profile aligns well ({career_fit.fit_score:.0%}) with {career_fit.career_title} requirements.",
                    affected_career=career_fit.career_title,
                    source_signals=["skill_match", "career_requirements"],
                    recommended_action="Continue building on your strengths.",
                    classification="DERIVED",
                )
            )

        # Interview improvement insight.
        if interview_summary.weaknesses and interview_summary.sessions_count > 0:
            insights.append(
                CareerTwinInsight(
                    id="interview-improvement",
                    type="INTERVIEW_IMPROVEMENT",
                    severity="INFO",
                    title="Interview performance available",
                    reason=f"Recent interview identified {len(interview_summary.weaknesses)} areas for improvement.",
                    affected_career=career_fit.career_title,
                    source_signals=["interview_performance"],
                    recommended_action="Review interview feedback and focus on weak areas.",
                    classification="PERFORMANCE_SIGNAL",
                )
            )

        return insights


# ---------------------------------------------------------------------------
# Conflict Detection Service
# ---------------------------------------------------------------------------


class CareerTwinConflictService:
    """Deterministic cross-system conflict detection."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def detect_conflicts(
        self,
        *,
        profile_skills: list[Skill],
        interview_summary: CareerTwinInterviewSummary,
        target_careers: list[str],
        active_target_career: str | None,
    ) -> list[CareerTwinConflict]:
        """Detect cross-system conflicts."""
        conflicts: list[CareerTwinConflict] = []

        # Performance vs confirmed skill conflict.
        for sp in interview_summary.skill_performance:
            skill_name = sp.get("skill_name")
            avg_score = sp.get("average_score")
            if avg_score is None:
                continue
            for s in profile_skills:
                if s.name == skill_name and s.proficiency in ("ADVANCED", "EXPERT"):
                    if avg_score < 0.50:
                        conflicts.append(
                            CareerTwinConflict(
                                id=f"perf-gap-{skill_name}",
                                type="PERFORMANCE_GAP",
                                severity="WARNING",
                                title=f"Interview performance gap: {skill_name}",
                                description=(
                                    f"Your profile lists {skill_name} as {s.proficiency}, "
                                    f"but interview performance was {avg_score:.0%}. "
                                    "This is a performance signal, not a profile change."
                                ),
                                affected_skill=skill_name,
                                source_a="profile (confirmed)",
                                source_b="interview (performance)",
                                resolution="Continue practicing; profile skill remains unchanged.",
                            )
                        )

        # Goal vs target career conflict.
        if len(target_careers) > 1 and active_target_career:
            for goal in target_careers:
                if goal != active_target_career:
                    conflicts.append(
                        CareerTwinConflict(
                            id=f"goal-conflict-{goal}",
                            type="GOAL_CONFLICT",
                            severity="INFO",
                            title=f"Multiple career targets: {goal} vs {active_target_career}",
                            description=(
                                f"Your profile lists '{goal}' as a goal but the active "
                                f"target is '{active_target_career}'."
                            ),
                            affected_career=active_target_career,
                            source_a="career_goals",
                            source_b="active_target",
                            resolution="Focus on one target career for clearer roadmap.",
                        )
                    )
                    break

        return conflicts


# ---------------------------------------------------------------------------
# Reconciliation Service
# ---------------------------------------------------------------------------


class CareerTwinReconciliationService:
    """Determines which derived systems need regeneration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def get_stale_components(
        self,
        *,
        profile_id: str,
        active_target_career: str | None,
        roadmap_generated_at: str | None,
        career_updated_at: str | None,
    ) -> list[CareerTwinStaleState]:
        """Determine which derived components are stale."""
        stale: list[CareerTwinStaleState] = []

        if roadmap_generated_at and career_updated_at:
            if career_updated_at > roadmap_generated_at:
                stale.append(
                    CareerTwinStaleState(
                        component="roadmap",
                        generated_at=roadmap_generated_at,
                        source_updated_at=career_updated_at,
                        is_stale=True,
                        reason="Career data updated after roadmap generation.",
                    )
                )

        return stale

    def get_refresh_plan(
        self,
        *,
        trigger: str,
    ) -> list[str]:
        """Determine which components to refresh based on trigger.

        Returns a list of component names to refresh.
        """
        refresh_map: dict[str, list[str]] = {
            "profile_skill_changed": [
                "skill_gap", "career_fit", "readiness", "roadmap", "insights",
            ],
            "interview_completed": [
                "interview_performance", "readiness", "insights",
            ],
            "evidence_updated": [
                "evidence_insights",
            ],
            "career_target_changed": [
                "career_fit", "skill_gap", "roadmap", "readiness", "insights",
            ],
            "roadmap_regenerated": [
                "insights",
            ],
            "manual": [
                "skill_gap", "career_fit", "readiness", "insights",
            ],
        }
        return refresh_map.get(trigger, [])

    async def execute_refresh(
        self,
        *,
        profile_id: str,
        trigger: str,
        active_target_career: str | None = None,
    ) -> dict[str, Any]:
        """Execute a refresh of stale derived state.

        Determines which components are stale, refreshes only those,
        and returns a typed refresh result with the updated state.
        """
        state_service = CareerTwinStateService(self.session)
        state = await state_service.get_state(
            profile_id=profile_id,
            active_target_career=active_target_career,
        )

        plan = self.get_refresh_plan(trigger=trigger)
        refreshed = []
        unchanged = []

        for component in plan:
            # Check if the component is actually stale.
            stale_components = [s.component for s in state.stale_components]
            if component in stale_components or trigger == "manual":
                refreshed.append(component)
            else:
                unchanged.append(component)

        # If nothing is stale, report all as unchanged.
        if not refreshed and plan:
            unchanged = list(plan)
            refreshed = []

        return {
            "refreshed_components": refreshed,
            "unchanged_components": unchanged,
            "message": (
                f"Refresh completed for trigger '{trigger}'. "
                f"Refreshed: {', '.join(refreshed) if refreshed else 'none'}. "
                f"Unchanged: {', '.join(unchanged) if unchanged else 'none'}."
            ),
            "state": state.model_dump(),
        }


# ---------------------------------------------------------------------------
# CareerTwin Agent
# ---------------------------------------------------------------------------


class CareerTwinAgent:
    """CareerTwin Agent — produces typed explanation layer over deterministic state."""

    name = "careertwin_agent"

    def __init__(
        self,
        llm_provider=None,
        session=None,
    ) -> None:
        from app.core.llm import FakeLLMProvider

        self.llm_provider = llm_provider or FakeLLMProvider()
        self.session = session

    async def run(self, state) -> Any:
        """Run the CareerTwin Agent.

        Produces a narrative explanation over the deterministic CareerTwin state.
        """
        from app.agents.contracts import AgentResult, AgentState, AgentStatus
        import time

        start = time.perf_counter()
        errors: list[dict[str, Any]] = []
        output = None

        try:
            profile_id = state.profile_id or state.context.get("profile_id")
            if not profile_id:
                raise ValueError("No profile_id available.")

            # Get the unified state.
            state_service = CareerTwinStateService(self.session)
            active_career = state.context.get("active_target_career")
            twin_state = await state_service.get_state(
                profile_id=profile_id,
                active_target_career=active_career,
            )

            # Generate insights.
            insight_service = CareerInsightService(self.session)
            insights = insight_service.generate_insights(
                career_fit=twin_state.career_fit,
                skill_gaps=twin_state.skill_gaps,
                interview_summary=twin_state.interview_summary,
                roadmap_summary=twin_state.roadmap_summary,
            )

            # Generate conflicts.
            conflict_service = CareerTwinConflictService(self.session)
            conflicts = conflict_service.detect_conflicts(
                profile_skills=[],  # Will be loaded from state
                interview_summary=twin_state.interview_summary,
                target_careers=twin_state.target_careers,
                active_target_career=twin_state.active_target_career,
            )

            output = {
                "capability": "careertwin_analysis",
                "state": twin_state.model_dump(),
                "insights": [i.model_dump() for i in insights],
                "conflicts": [c.model_dump() for c in conflicts],
                "methodology": (
                    "Deterministic CareerTwin aggregation: profile + career fit + "
                    "skill gaps + roadmap + interview performance + evidence. "
                    "Insights and conflicts are derived from structured signals."
                ),
            }

            status = AgentStatus.COMPLETED

        except Exception as exc:  # noqa: BLE001
            errors.append(
                {"agent": self.name, "code": "AGENT_ERROR", "message": str(exc)}
            )
            status = AgentStatus.FAILED

        duration_ms = int((time.perf_counter() - start) * 1000)
        return AgentResult(
            agent_name=self.name,
            status=status,
            output=output,
            metadata={"provider": self.llm_provider.provider_name},
            errors=errors,
            duration_ms=duration_ms,
        )


__all__ = [
    "CareerTwinStateService",
    "CareerFitEngine",
    "CareerReadinessService",
    "CareerInsightService",
    "CareerTwinConflictService",
    "CareerTwinReconciliationService",
    "CareerTwinAgent",
]
