"""Tests for skill matching engine."""

import pytest

from app.services.skill_matching import compute_skill_match


def make_career_skill(skill_name: str, importance: str = "CORE", minimum_level: str | None = None) -> dict:
    return {
        "skill_name": skill_name,
        "category": "Test",
        "importance": importance,
        "minimum_level": minimum_level,
        "description": f"Test skill {skill_name}",
    }


def make_profile_skill(skill_name: str, proficiency: str | None = "INTERMEDIATE") -> dict:
    return {
        "name": skill_name,
        "proficiency": proficiency,
        "years_experience": 3.0,
        "source": "USER_CONFIRMED",
    }


def test_perfect_match() -> None:
    """Test when profile has all career skills at required level."""
    result = compute_skill_match(
        career_id="career-1",
        career_title="Test Career",
        career_skills=[
            make_career_skill("Python", "CORE", "INTERMEDIATE"),
            make_career_skill("SQL", "IMPORTANT", "BEGINNER"),
        ],
        profile_skills=[
            make_profile_skill("Python", "INTERMEDIATE"),
            make_profile_skill("SQL", "BEGINNER"),
        ],
    )

    assert result.overall_score > 0.9
    assert len(result.matched) == 2
    assert len(result.missing) == 0
    assert len(result.partial) == 0


def test_missing_skill() -> None:
    """Test when profile is missing a career skill."""
    result = compute_skill_match(
        career_id="career-1",
        career_title="Test Career",
        career_skills=[
            make_career_skill("Python", "CORE", "INTERMEDIATE"),
            make_career_skill("Java", "IMPORTANT", "BEGINNER"),
        ],
        profile_skills=[
            make_profile_skill("Python", "INTERMEDIATE"),
        ],
    )

    assert result.overall_score < 1.0
    assert len(result.matched) == 1
    assert len(result.missing) == 1
    assert result.missing[0]["skill_name"] == "Java"
    assert result.missing[0]["status"] == "MISSING"


def test_partial_match() -> None:
    """Test when profile has skill but below required level."""
    result = compute_skill_match(
        career_id="career-1",
        career_title="Test Career",
        career_skills=[
            make_career_skill("Python", "CORE", "ADVANCED"),
        ],
        profile_skills=[
            make_profile_skill("Python", "BEGINNER"),
        ],
    )

    assert len(result.partial) == 1
    assert result.partial[0]["skill_name"] == "Python"
    assert result.partial[0]["status"] == "PARTIAL"
    assert result.partial[0]["user_level"] == "BEGINNER"
    assert result.partial[0]["required_level"] == "ADVANCED"


def test_empty_profile() -> None:
    """Test with empty profile skills."""
    result = compute_skill_match(
        career_id="career-1",
        career_title="Test Career",
        career_skills=[
            make_career_skill("Python", "CORE", "INTERMEDIATE"),
        ],
        profile_skills=[],
    )

    assert result.overall_score == 0.0
    assert len(result.matched) == 0
    assert len(result.missing) == 1


def test_empty_career_skills() -> None:
    """Test with empty career skills."""
    result = compute_skill_match(
        career_id="career-1",
        career_title="Test Career",
        career_skills=[],
        profile_skills=[
            make_profile_skill("Python", "INTERMEDIATE"),
        ],
    )

    assert result.overall_score == 0.0
    assert len(result.matched) == 0
    assert len(result.missing) == 0


def test_importance_weighting() -> None:
    """Test that CORE skills weigh more than SUPPORTING skills."""
    # High score on supporting, missing core -> low overall
    result_core_missing = compute_skill_match(
        career_id="career-1",
        career_title="Test Career",
        career_skills=[
            make_career_skill("Python", "CORE", "INTERMEDIATE"),
            make_career_skill("Git", "SUPPORTING", "BEGINNER"),
        ],
        profile_skills=[
            make_profile_skill("Git", "INTERMEDIATE"),
        ],
    )

    # High score on core, missing supporting -> high overall
    result_core_matched = compute_skill_match(
        career_id="career-1",
        career_title="Test Career",
        career_skills=[
            make_career_skill("Python", "CORE", "INTERMEDIATE"),
            make_career_skill("Git", "SUPPORTING", "BEGINNER"),
        ],
        profile_skills=[
            make_profile_skill("Python", "INTERMEDIATE"),
        ],
    )

    assert result_core_matched.overall_score > result_core_missing.overall_score


def test_deterministic_score() -> None:
    """Test that the same inputs produce the same score."""
    result1 = compute_skill_match(
        career_id="career-1",
        career_title="Test Career",
        career_skills=[make_career_skill("Python", "CORE", "INTERMEDIATE")],
        profile_skills=[make_profile_skill("Python", "INTERMEDIATE")],
    )
    result2 = compute_skill_match(
        career_id="career-1",
        career_title="Test Career",
        career_skills=[make_career_skill("Python", "CORE", "INTERMEDIATE")],
        profile_skills=[make_profile_skill("Python", "INTERMEDIATE")],
    )

    assert result1.overall_score == result2.overall_score


def test_normalization_in_matching() -> None:
    """Test that skill normalization works in matching."""
    result = compute_skill_match(
        career_id="career-1",
        career_title="Test Career",
        career_skills=[
            make_career_skill("Python", "CORE", "INTERMEDIATE"),
        ],
        profile_skills=[
            make_profile_skill("python", "INTERMEDIATE"),  # lowercase
        ],
    )

    assert len(result.matched) == 1
    assert result.matched[0]["skill_name"] == "Python"


def test_methodology_is_set() -> None:
    """Test that methodology is set."""
    result = compute_skill_match(
        career_id="career-1",
        career_title="Test Career",
        career_skills=[make_career_skill("Python", "CORE", "INTERMEDIATE")],
        profile_skills=[make_profile_skill("Python", "INTERMEDIATE")],
    )

    assert "weighted" in result.methodology.lower()
    assert "CORE" in result.methodology


__all__ = [
    "test_perfect_match",
    "test_missing_skill",
    "test_partial_match",
    "test_empty_profile",
    "test_empty_career_skills",
    "test_importance_weighting",
    "test_deterministic_score",
    "test_normalization_in_matching",
    "test_methodology_is_set",
]
