"""Profile extraction boundary.

The ProfileExtractor abstraction turns raw document text into a structured
ProfileDraft. This phase provides a deterministic mock implementation that is
clearly marked temporary. The future Profile Agent will replace or orchestrate
this capability.

The rest of the application depends on this abstraction, not on any LLM SDK.
"""

import re
from typing import List, Optional, Protocol

from app.schemas.profile import (
    CareerGoalCreate,
    EducationCreate,
    ExperienceCreate,
    ExtractionMetadata,
    ProfileCreate,
    ProfileDraft,
    SkillCreate,
)


class ProfileExtractor(Protocol):
    """Protocol for extracting a structured profile draft from document text."""

    async def extract(
        self,
        document_text: str,
        *,
        source_type: str,
        source_file_name: Optional[str] = None,
    ) -> ProfileDraft:
        """Extract a ProfileDraft from raw document text."""
        ...


class MockProfileExtractor:
    """Temporary deterministic implementation of ProfileExtractor.

    This performs lightweight keyword/section-based extraction suitable for
    development and testing. It is intentionally naive and clearly temporary;
    it does NOT use an LLM. The future Profile Agent replaces this.
    """

    _SECTION_HEADERS = {
        "education": ["education", "academic background", "qualifications"],
        "skills": ["skills", "technical skills", "competencies", "expertise"],
        "projects": ["projects", "project experience", "key projects"],
        "experience": [
            "experience",
            "work experience",
            "employment",
            "professional experience",
        ],
        "career_goals": ["objective", "career objective", "goal", "summary"],
    }

    async def extract(
        self,
        document_text: str,
        *,
        source_type: str,
        source_file_name: Optional[str] = None,
    ) -> ProfileDraft:
        text = document_text or ""
        warnings: List[str] = []

        if not text.strip():
            warnings.append("No text was extracted from the document.")

        # Very lightweight name guess: first non-empty line that looks like a name.
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        full_name = lines[0] if lines else None

        profile = ProfileCreate(
            full_name=full_name,
            headline=None,
            email=None,
            phone=None,
            location=None,
            summary=None,
            profile_status="DRAFT",
        )

        education = self._extract_section(text, "education")
        skills = self._extract_skills(text)
        projects = self._extract_section(text, "projects")
        experience = self._extract_section(text, "experience")
        career_goals = self._extract_objective(text)

        return ProfileDraft(
            profile=profile,
            education=education,
            skills=skills,
            projects=projects,
            experience=experience,
            career_goals=career_goals,
            extraction_metadata=ExtractionMetadata(
                source_type=source_type,
                source_file_name=source_file_name,
                extraction_warnings=warnings,
            ),
        )

    def _extract_section(self, text: str, section: str):
        """Lightweight section extraction (placeholder quality)."""
        headers = self._SECTION_HEADERS.get(section, [])
        pattern = "|".join(re.escape(h) for h in headers)
        items = []
        # Split on section header occurrences; capture following block until
        # the next known header.
        if re.search(pattern, text, flags=re.IGNORECASE):
            # Found a section marker; record a single placeholder item so the
            # structure is exercised without fabricating content.
            items.append(
                {
                    "name": f"Extracted {section[:-1] if section.endswith('s') else section}",
                    "note": "Auto-extracted placeholder — review before confirming.",
                }
            )
        return items

    def _extract_skills(self, text: str) -> List[SkillCreate]:
        skills: List[SkillCreate] = []
        if re.search(r"\bpython\b", text, flags=re.IGNORECASE):
            skills.append(
                SkillCreate(
                    name="Python",
                    category="Programming",
                    proficiency=None,
                    years_experience=None,
                    source="DOCUMENT_EXTRACTED",
                )
            )
        if re.search(r"\bsql\b", text, flags=re.IGNORECASE):
            skills.append(
                SkillCreate(
                    name="SQL",
                    category="Database",
                    proficiency=None,
                    years_experience=None,
                    source="DOCUMENT_EXTRACTED",
                )
            )
        return skills

    def _extract_objective(self, text: str) -> List[CareerGoalCreate]:
        goals: List[CareerGoalCreate] = []
        if re.search(r"\b(objective|goal|seeking|looking for)\b", text, flags=re.IGNORECASE):
            goals.append(
                CareerGoalCreate(
                    target_role="To be confirmed",
                    target_industry=None,
                    target_domain=None,
                    goal_description="Review and confirm your career goal.",
                    priority=1,
                )
            )
        return goals


# Module-level default instance used by the API layer. This can be swapped for
# the real Profile Agent implementation in a later phase.
profile_extractor = MockProfileExtractor()
