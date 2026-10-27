"""Deterministic career-fit service.

Computes a career fit score and summary from a profile, career requirements,
and a SkillMatchResult. The numerical score is computed deterministically —
the LLM may explain it but never override it.
"""

from __future__ import annotations

from typing import Any

from app.services.skill_matching import SkillMatchResult


class CareerFitResult:
    """Deterministic career fit output."""

    def __init__(
        self,
        *,
        career_id: str,
        career_title: str,
        fit_score: float,
        fit_summary: str,
        strengths: list[str],
        gaps: list[str],
        methodology: str,
    ) -> None:
        self.career_id = career_id
        self.career_title = career_title
        self.fit_score = fit_score
        self.fit_summary = fit_summary
        self.strengths = strengths
        self.gaps = gaps
        self.methodology = methodology

    def model_dump(self) -> dict:
        return {
            "career_id": self.career_id,
            "career_title": self.career_title,
            "fit_score": round(self.fit_score, 4),
            "fit_summary": self.fit_summary,
            "strengths": self.strengths,
            "gaps": self.gaps,
            "methodology": self.methodology,
        }


def compute_career_fit(
    *,
    career_id: str,
    career_title: str,
    match_result: SkillMatchResult,
) -> CareerFitResult:
    """Compute deterministic career fit from a skill match result.

    The fit score is derived directly from the deterministic skill match
    overall score. Strengths and gaps are derived from matched/missing skills.
    """
    matched = match_result.matched
    missing = match_result.missing
    partial = match_result.partial

    overall_score = match_result.overall_score

    strengths = [
        f"{m['skill_name']} ({m['importance']}) — {m['reason']}"
        for m in matched[:5]
    ]
    if not strengths:
        strengths.append("No strongly matched core skills identified.")

    gaps = [
        f"{m['skill_name']} ({m['importance']}) — {m['reason']}"
        for m in missing[:5]
    ]
    if partial:
        gaps.append(
            f"{len(partial)} skill(s) partially matched — consider "
            "increasing proficiency."
        )
    if not missing and not partial:
        gaps.append("No significant gaps identified.")

    if overall_score >= 0.8:
        fit_summary = (
            "Strong fit. Your profile aligns well with this career's "
            "core requirements."
        )
    elif overall_score >= 0.5:
        fit_summary = (
            "Moderate fit. Several core skills are present, but notable "
            "gaps remain before full alignment."
        )
    elif overall_score > 0:
        fit_summary = (
            "Limited fit. Only a few relevant skills are present; "
            "significant development needed."
        )
    else:
        fit_summary = "No match. None of the career's core skills appear in your profile."

    methodology = (
        "Fit score is the SkillMatchResult overall score (weighted by "
        "skill importance: CORE=1.0, IMPORTANT=0.7, SUPPORTING=0.4). "
        "Strengths are top matched skills; gaps are top missing skills."
    )

    return CareerFitResult(
        career_id=career_id,
        career_title=career_title,
        fit_score=overall_score,
        fit_summary=fit_summary,
        strengths=strengths,
        gaps=gaps,
        methodology=methodology,
    )
