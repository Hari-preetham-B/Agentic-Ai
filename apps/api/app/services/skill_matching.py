"""Deterministic skill matching engine.

Compares CareerTwin profile skills against career requirements to produce
a structured SkillMatchResult. All scoring is deterministic — no LLM
involvement in score calculation.
"""

from __future__ import annotations

from typing import Any

from app.services.skill_normalization import normalize_skill

# Weights per career skill importance. Defined in one place.
_IMPORTANCE_WEIGHTS: dict[str, float] = {
    "CORE": 1.0,
    "IMPORTANT": 0.7,
    "SUPPORTING": 0.4,
}

# Proficiency score per level.
_PROFICIENCY_SCORES: dict[str, float] = {
    "BEGINNER": 0.25,
    "INTERMEDIATE": 0.5,
    "ADVANCED": 0.75,
    "EXPERT": 1.0,
}

# Minimum level required to count as a match for a given required level.
_LEVEL_SATISFIES: dict[str, set[str]] = {
    "BEGINNER": {"BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"},
    "INTERMEDIATE": {"INTERMEDIATE", "ADVANCED", "EXPERT"},
    "ADVANCED": {"ADVANCED", "EXPERT"},
    "EXPERT": {"EXPERT"},
}


class SkillMatchResult:
    """Deterministic comparison of profile skills vs career requirements."""

    def __init__(
        self,
        *,
        career_id: str,
        career_title: str,
        matched: list[dict],
        partial: list[dict],
        missing: list[dict],
        overall_score: float,
        methodology: str,
    ) -> None:
        self.career_id = career_id
        self.career_title = career_title
        self.matched = matched
        self.partial = partial
        self.missing = missing
        self.overall_score = overall_score
        self.methodology = methodology

    def model_dump(self) -> dict:
        return {
            "career_id": self.career_id,
            "career_title": self.career_title,
            "matched": self.matched,
            "partial": self.partial,
            "missing": self.missing,
            "overall_score": round(self.overall_score, 4),
            "methodology": self.methodology,
        }


def _proficiency_score(level: str | None) -> float:
    if level is None:
        return 0.0
    return _PROFICIENCY_SCORES.get(level.upper(), 0.0)


def _level_satisfies(user_level: str | None, required_level: str | None) -> bool:
    if required_level is None:
        return True
    if user_level is None:
        return False
    satisfied = _LEVEL_SATISFIES.get(required_level.upper(), set())
    return user_level.upper() in satisfied


def compute_skill_match(
    *,
    career_id: str,
    career_title: str,
    career_skills: list[dict],
    profile_skills: list[dict],
) -> SkillMatchResult:
    """Compute skill match between profile and career requirements.

    Args:
        career_id: Career ID.
        career_title: Career title.
        career_skills: List of dicts with keys: skill_name, category,
            importance, minimum_level.
        profile_skills: List of dicts with keys: name, proficiency,
            years_experience, source.

    Returns:
        SkillMatchResult with matched, partial, missing, and overall_score.
    """
    # Normalize profile skills into a lookup: canonical name -> best proficiency
    profile_lookup: dict[str, dict] = {}
    for ps in profile_skills:
        canon = normalize_skill(ps.get("name", ""))
        existing = profile_lookup.get(canon)
        if existing is None:
            profile_lookup[canon] = {
                "name": canon,
                "proficiency": ps.get("proficiency"),
                "years_experience": ps.get("years_experience"),
            }
        else:
            # Keep the highest proficiency if duplicate
            existing_level = (existing.get("proficiency") or "BEGINNER").upper()
            new_level = (ps.get("proficiency") or "BEGINNER").upper()
            if _PROFICIENCY_SCORES.get(new_level, 0) > _PROFICIENCY_SCORES.get(
                existing_level, 0
            ):
                existing["proficiency"] = ps.get("proficiency")
                existing["years_experience"] = ps.get(
                    "years_experience", existing.get("years_experience")
                )

    matched: list[dict] = []
    partial: list[dict] = []
    missing: list[dict] = []

    total_weight = 0.0
    earned_weight = 0.0

    for cs in career_skills:
        importance = cs.get("importance", "SUPPORTING")
        weight = _IMPORTANCE_WEIGHTS.get(importance.upper(), 0.4)
        total_weight += weight

        canon = normalize_skill(cs.get("skill_name", ""))
        required_level = cs.get("minimum_level")

        profile_entry = profile_lookup.get(canon)

        if profile_entry is None:
            # Skill not in profile at all
            missing.append(
                {
                    "skill_name": cs.get("skill_name", ""),
                    "category": cs.get("category"),
                    "importance": importance,
                    "user_level": None,
                    "required_level": required_level,
                    "status": "MISSING",
                    "score": 0.0,
                    "reason": "Skill not present in profile.",
                }
            )
            continue

        user_level = profile_entry.get("proficiency")
        satisfies_level = _level_satisfies(user_level, required_level)
        proficiency_score = _proficiency_score(user_level)

        if satisfies_level:
            # Fully matched: user meets or exceeds required level
            matched.append(
                {
                    "skill_name": cs.get("skill_name", ""),
                    "category": cs.get("category"),
                    "importance": importance,
                    "user_level": user_level,
                    "required_level": required_level,
                    "status": "MATCHED",
                    "score": weight,
                    "reason": (
                        f"User has {user_level or 'unspecified'} proficiency, "
                        f"meeting required {required_level or 'unspecified'}."
                    ),
                }
            )
            earned_weight += weight
        elif proficiency_score > 0:
            # Partial: user has some skill but below required level
            partial.append(
                {
                    "skill_name": cs.get("skill_name", ""),
                    "category": cs.get("category"),
                    "importance": importance,
                    "user_level": user_level,
                    "required_level": required_level,
                    "status": "PARTIAL",
                    "score": weight * proficiency_score,
                    "reason": (
                        f"User has {user_level} proficiency but role requires "
                        f"{required_level or 'unspecified'}."
                    ),
                }
            )
            earned_weight += weight * proficiency_score
        else:
            missing.append(
                {
                    "skill_name": cs.get("skill_name", ""),
                    "category": cs.get("category"),
                    "importance": importance,
                    "user_level": user_level,
                    "required_level": required_level,
                    "status": "MISSING",
                    "score": 0.0,
                    "reason": "Skill not present in profile.",
                }
            )

    overall_score = earned_weight / total_weight if total_weight > 0 else 0.0

    methodology = (
        "Deterministic weighted scoring. Each career skill carries an "
        "importance weight (CORE=1.0, IMPORTANT=0.7, SUPPORTING=0.4). "
        "A skill counts as MATCHED when the user's proficiency meets or "
        "exceeds the required minimum level; PARTIAL when the user has the "
        "skill below the required level; MISSING when absent. Overall score "
        "is the sum of earned weights divided by total possible weight."
    )

    return SkillMatchResult(
        career_id=career_id,
        career_title=career_title,
        matched=matched,
        partial=partial,
        missing=missing,
        overall_score=overall_score,
        methodology=methodology,
    )
