"""Tests for career fit service."""

import pytest

from app.services.career_fit_service import compute_career_fit
from app.services.skill_matching import compute_skill_match


def make_match_result(
    overall_score: float,
    matched_count: int = 2,
    missing_count: int = 1,
    partial_count: int = 0,
) -> dict:
    """Create a mock SkillMatchResult-like dict."""
    matched = [
        {
            "skill_name": f"Skill {i}",
            "importance": "CORE",
            "user_level": "INTERMEDIATE",
            "required_level": "INTERMEDIATE",
            "status": "MATCHED",
            "score": 1.0,
            "reason": "Match",
        }
        for i in range(matched_count)
    ]
    missing = [
        {
            "skill_name": f"Missing {i}",
            "importance": "IMPORTANT",
            "user_level": None,
            "required_level": "INTERMEDIATE",
            "status": "MISSING",
            "score": 0.0,
            "reason": "Missing",
        }
        for i in range(missing_count)
    ]
    partial = [
        {
            "skill_name": f"Partial {i}",
            "importance": "SUPPORTING",
            "user_level": "BEGINNER",
            "required_level": "INTERMEDIATE",
            "status": "PARTIAL",
            "score": 0.5,
            "reason": "Partial",
        }
        for i in range(partial_count)
    ]

    from app.services.skill_matching import SkillMatchResult

    return SkillMatchResult(
        career_id="career-1",
        career_title="Test Career",
        matched=matched,
        partial=partial,
        missing=missing,
        overall_score=overall_score,
        methodology="test",
    )


def test_high_fit() -> None:
    """Test high fit score."""
    result = compute_career_fit(
        career_id="career-1",
        career_title="Test Career",
        match_result=make_match_result(0.9, matched_count=3, missing_count=0),
    )

    assert result.fit_score == 0.9
    assert "Strong fit" in result.fit_summary
    assert len(result.strengths) > 0


def test_moderate_fit() -> None:
    """Test moderate fit score."""
    result = compute_career_fit(
        career_id="career-1",
        career_title="Test Career",
        match_result=make_match_result(0.6, matched_count=2, missing_count=1),
    )

    assert result.fit_score == 0.6
    assert "Moderate fit" in result.fit_summary


def test_limited_fit() -> None:
    """Test limited fit score."""
    result = compute_career_fit(
        career_id="career-1",
        career_title="Test Career",
        match_result=make_match_result(0.2, matched_count=0, missing_count=3),
    )

    assert result.fit_score == 0.2
    assert "Limited fit" in result.fit_summary


def test_no_match() -> None:
    """Test no match score."""
    result = compute_career_fit(
        career_id="career-1",
        career_title="Test Career",
        match_result=make_match_result(0.0, matched_count=0, missing_count=3),
    )

    assert result.fit_score == 0.0
    assert "No match" in result.fit_summary


def test_strengths_and_gaps() -> None:
    """Test that strengths and gaps are populated."""
    result = compute_career_fit(
        career_id="career-1",
        career_title="Test Career",
        match_result=make_match_result(0.7, matched_count=2, missing_count=2),
    )

    assert len(result.strengths) > 0
    assert len(result.gaps) > 0


def test_methodology_is_set() -> None:
    """Test that methodology is set."""
    result = compute_career_fit(
        career_id="career-1",
        career_title="Test Career",
        match_result=make_match_result(0.5),
    )

    assert "weighted" in result.methodology.lower()


def test_model_dump() -> None:
    """Test model_dump serialization."""
    result = compute_career_fit(
        career_id="career-1",
        career_title="Test Career",
        match_result=make_match_result(0.5),
    )

    dumped = result.model_dump()
    assert dumped["career_id"] == "career-1"
    assert dumped["career_title"] == "Test Career"
    assert dumped["fit_score"] == 0.5
    assert "fit_summary" in dumped
    assert "strengths" in dumped
    assert "gaps" in dumped


__all__ = [
    "test_high_fit",
    "test_moderate_fit",
    "test_limited_fit",
    "test_no_match",
    "test_strengths_and_gaps",
    "test_methodology_is_set",
    "test_model_dump",
]
