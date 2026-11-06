"""Learning roadmap service.

Orchestrates roadmap generation from profile, career, skill gaps, dependency
graph, and learning resource catalog.

Deterministic — same inputs produce the same roadmap. Regeneration replaces
the existing roadmap for a profile/career pair.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career import Career
from app.models.learning import (
    LearningResource,
    LearningResourceSkill,
    Roadmap,
    RoadmapItem,
    RoadmapResource,
    SkillDependency,
)
from app.models.profile import Profile, Skill
from app.services.career_knowledge_service import CareerKnowledgeService
from app.services.repositories import CareerRepository
from app.services.skill_dependency_service import SkillDependencyService
from app.services.skill_matching import compute_skill_match


class LearningRoadmapService:
    """Service for generating and managing learning roadmaps."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.career_repo = CareerRepository(session)
        self.dep_service = SkillDependencyService(session)

    async def generate_roadmap(
        self,
        *,
        profile_id: str,
        career_slug: str,
        profile_skills: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate a personalized learning roadmap.

        Pipeline:
        1. Retrieve career requirements.
        2. Compute skill gaps.
        3. Load dependency graph.
        4. Match learning resources to gaps.
        5. Calculate priorities.
        6. Sequence roadmap items.
        7. Persist roadmap.
        """
        # Step 1: Get career.
        career_service = CareerKnowledgeService(self.session)
        career = await career_service.get_career(career_slug)
        if career is None:
            raise ValueError(f"Career not found: {career_slug}")

        career_id = career["id"]

        # Step 2: Get career skills for matching.
        career_skills = career.get("skills", [])
        match = compute_skill_match(
            career_id=career_id,
            career_title=career["title"],
            career_skills=career_skills,
            profile_skills=profile_skills,
        )

        # Step 3: Identify skills to learn (missing + partial).
        skills_to_learn = []
        for m in match.missing:
            skills_to_learn.append({
                "skill_name": m["skill_name"],
                "importance": m.get("importance", "SUPPORTING"),
                "current_proficiency": None,
                "gap_severity": 1.0,
            })
        for m in match.partial:
            skills_to_learn.append({
                "skill_name": m["skill_name"],
                "importance": m.get("importance", "SUPPORTING"),
                "current_proficiency": m.get("user_level"),
                "gap_severity": 0.5,
            })

        # Step 4: Load dependency graph.
        deps = await self.dep_service.get_all_dependencies()
        graph = self.dep_service.build_graph(deps)

        # Step 5: Get known skills.
        known_skills = {normalize(s.get("name", "")) for s in profile_skills}

        # Step 6: Calculate downstream counts and priorities.
        from app.services.roadmap_priority_engine import RoadmapPriorityEngine
        priority_engine = RoadmapPriorityEngine()

        # Build priority map.
        priority_map = {}
        downstream_counts = {}
        for item in skills_to_learn:
            skill = item["skill_name"]
            dc = priority_engine.calculate_downstream_count(skill, graph)
            downstream_counts[skill] = dc
            priority = priority_engine.calculate_priority(
                skill_name=skill,
                importance=item["importance"],
                current_proficiency=item["current_proficiency"],
                gap_severity=item["gap_severity"],
                downstream_count=dc,
                total_skills=len(skills_to_learn),
                estimated_hours=None,
            )
            priority_map[skill] = priority

        # Step 7: Sequence.
        from app.services.roadmap_sequence_engine import RoadmapSequenceEngine
        seq_engine = RoadmapSequenceEngine()
        skill_names = [item["skill_name"] for item in skills_to_learn]
        ordered = seq_engine.sequence(
            skills_to_learn=skill_names,
            graph=graph,
            known_skills=known_skills,
            priority_map=priority_map,
        )

        # Step 8: Load learning resources.
        resources = await self._load_resources()
        resource_mappings = await self._load_resource_skill_mappings()

        # Step 9: Build roadmap items.
        from app.services.learning_resource_matcher import LearningResourceMatcher
        matcher = LearningResourceMatcher(self.session)

        roadmap_items = []
        for seq, skill in enumerate(ordered):
            # Find skill importance from career skills.
            importance = "SUPPORTING"
            for cs in career_skills:
                if cs.get("skill_name") == skill:
                    importance = cs.get("importance", "SUPPORTING")
                    break

            # Find current proficiency.
            current_prof = None
            for ps in profile_skills:
                if normalize(ps.get("name", "")) == normalize(skill):
                    current_prof = ps.get("proficiency")
                    break

            # Match resources.
            skill_resources = matcher.rank_resources(
                skill_name=skill,
                current_proficiency=current_prof,
                resources=resources,
                resource_skill_mappings=resource_mappings,
            )

            # Missing prerequisites.
            missing_prereqs = seq_engine.get_missing_prerequisites(
                skill, graph, known_skills
            )

            # Estimated hours.
            est_hours = None
            if skill_resources:
                est_hours = sum(
                    r.get("estimated_hours", 0) or 0 for r in skill_resources[:3]
                )

            roadmap_items.append({
                "skill_name": skill,
                "priority": priority_map.get(skill, "P2"),
                "sequence_order": seq,
                "status": "PENDING",
                "rationale": (
                    f"Gap identified: {skill} is "
                    f"{'missing' if current_prof is None else 'partially matched'} "
                    f"in your profile. Career importance: {importance}. "
                    f"Downstream skills unlocked: {downstream_counts.get(skill, 0)}."
                ),
                "estimated_hours": est_hours,
                "current_proficiency": current_prof,
                "target_proficiency": "INTERMEDIATE",
                "prerequisites": missing_prereqs,
                "resources": skill_resources[:3],
            })

        # Step 10: Persist roadmap.
        roadmap = await self._persist_roadmap(
            profile_id=profile_id,
            career_id=career_id,
            items=roadmap_items,
            resources_list=resources,
        )

        return {
            "roadmap_id": str(roadmap.id),
            "profile_id": profile_id,
            "career_id": career_id,
            "career_title": career["title"],
            "items": roadmap_items,
            "summary": {
                "total_skills": len(roadmap_items),
                "p0_count": sum(1 for i in roadmap_items if i["priority"] == "P0"),
                "p1_count": sum(1 for i in roadmap_items if i["priority"] == "P1"),
                "p2_count": sum(1 for i in roadmap_items if i["priority"] == "P2"),
                "total_estimated_hours": sum(
                    i.get("estimated_hours", 0) or 0 for i in roadmap_items
                ),
            },
        }

    async def get_latest_roadmap(
        self, profile_id: str
    ) -> dict[str, Any] | None:
        """Retrieve the most recently generated roadmap for a profile."""
        result = await self.session.execute(
            select(Roadmap)
            .where(Roadmap.profile_id == uuid.UUID(profile_id))
            .order_by(Roadmap.generated_at.desc())
            .limit(1)
        )
        roadmap = result.scalar_one_or_none()
        if roadmap is None:
            return None
        return await self.get_roadmap(str(roadmap.id))

    async def get_roadmap(self, roadmap_id: str) -> dict[str, Any] | None:
        """Retrieve a roadmap by ID."""
        result = await self.session.execute(
            select(Roadmap).where(Roadmap.id == uuid.UUID(roadmap_id))
        )
        roadmap = result.scalar_one_or_none()
        if roadmap is None:
            return None

        items_result = await self.session.execute(
            select(RoadmapItem)
            .where(RoadmapItem.roadmap_id == roadmap.id)
            .order_by(RoadmapItem.sequence_order)
        )
        items = items_result.scalars().all()

        item_list = []
        for item in items:
            resources_result = await self.session.execute(
                select(RoadmapResource, LearningResource)
                .join(LearningResource, RoadmapResource.resource_id == LearningResource.id)
                .where(RoadmapResource.roadmap_item_id == item.id)
                .order_by(RoadmapResource.sequence_order)
            )
            resources = [
                {
                    "id": str(r.id),
                    "title": res.title,
                    "provider": res.provider,
                    "resource_type": res.resource_type,
                    "url": res.url,
                    "difficulty": res.difficulty,
                    "estimated_hours": res.estimated_hours,
                    "relevance_score": rr.relevance_score,
                }
                for rr, res in resources_result.all()
            ]

            item_list.append({
                "id": str(item.id),
                "skill_name": item.skill_name,
                "priority": item.priority,
                "sequence_order": item.sequence_order,
                "status": item.status,
                "rationale": item.rationale,
                "estimated_hours": item.estimated_hours,
                "current_proficiency": item.current_proficiency,
                "target_proficiency": item.target_proficiency,
                "prerequisites": item.prerequisites,
                "resources": resources,
            })

        return {
            "roadmap_id": str(roadmap.id),
            "profile_id": str(roadmap.profile_id),
            "career_id": str(roadmap.career_id) if roadmap.career_id else None,
            "status": roadmap.status,
            "generated_at": roadmap.generated_at.isoformat(),
            "items": item_list,
        }

    async def regenerate_roadmap(
        self,
        *,
        roadmap_id: str,
        profile_id: str,
        career_slug: str,
        profile_skills: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Regenerate a roadmap, replacing the existing one."""
        # Delete old roadmap (cascade handles items and resources).
        old = await self.session.execute(
            select(Roadmap).where(Roadmap.id == uuid.UUID(roadmap_id))
        )
        old_roadmap = old.scalar_one_or_none()
        if old_roadmap:
            await self.session.delete(old_roadmap)
            await self.session.commit()

        # Generate new.
        return await self.generate_roadmap(
            profile_id=profile_id,
            career_slug=career_slug,
            profile_skills=profile_skills,
        )

    async def _load_resources(self) -> list[dict[str, Any]]:
        """Load all learning resources from the database."""
        result = await self.session.execute(select(LearningResource))
        resources = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "title": r.title,
                "provider": r.provider,
                "resource_type": r.resource_type,
                "url": r.url,
                "description": r.description,
                "difficulty": r.difficulty,
                "estimated_hours": r.estimated_hours,
            }
            for r in resources
        ]

    async def _load_resource_skill_mappings(self) -> list[dict[str, Any]]:
        """Load all resource-skill mappings."""
        result = await self.session.execute(select(LearningResourceSkill))
        mappings = result.scalars().all()
        return [
            {
                "resource_id": str(m.resource_id),
                "skill_name": m.skill_name,
                "relevance_score": m.relevance_score,
                "coverage_type": m.coverage_type,
            }
            for m in mappings
        ]

    async def _persist_roadmap(
        self,
        *,
        profile_id: str,
        career_id: str,
        items: list[dict[str, Any]],
        resources_list: list[dict[str, Any]],
    ) -> Roadmap:
        """Persist a roadmap and its items to the database."""
        roadmap = Roadmap(
            profile_id=uuid.UUID(profile_id),
            career_id=uuid.UUID(career_id),
            status="GENERATED",
            metadata_={"item_count": len(items)},
        )
        self.session.add(roadmap)
        await self.session.flush()

        for item in items:
            roadmap_item = RoadmapItem(
                roadmap_id=roadmap.id,
                skill_name=item["skill_name"],
                priority=item["priority"],
                sequence_order=item["sequence_order"],
                status=item["status"],
                rationale=item["rationale"],
                estimated_hours=item.get("estimated_hours"),
                current_proficiency=item.get("current_proficiency"),
                target_proficiency=item.get("target_proficiency"),
                prerequisites=item.get("prerequisites", []),
            )
            self.session.add(roadmap_item)
            await self.session.flush()

            for res in item.get("resources", []):
                rr = RoadmapResource(
                    roadmap_item_id=roadmap_item.id,
                    resource_id=uuid.UUID(res["id"]),
                    relevance_score=res.get("match_score"),
                    sequence_order=0,
                )
                self.session.add(rr)

        await self.session.commit()
        await self.session.refresh(roadmap)
        return roadmap


def normalize(text: str) -> str:
    """Simple skill name normalization for matching."""
    return text.strip().lower()


__all__ = ["LearningRoadmapService", "normalize"]
