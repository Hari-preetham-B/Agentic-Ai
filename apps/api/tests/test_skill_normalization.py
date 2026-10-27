"""Tests for skill normalization."""

import pytest

from app.services.skill_normalization import (
    is_known_skill,
    list_canonical_skills,
    normalize_skill,
    normalize_skills,
)


def test_normalize_skill_known() -> None:
    """Test normalizing a known skill with various spellings."""
    assert normalize_skill("Python") == "Python"
    assert normalize_skill("python") == "Python"
    assert normalize_skill("python 3") == "Python"
    assert normalize_skill("python3") == "Python"
    assert normalize_skill("PYTHON") == "Python"
    assert normalize_skill("  Python  ") == "Python"


def test_normalize_skill_javascript() -> None:
    """Test normalizing JavaScript variants."""
    assert normalize_skill("JavaScript") == "JavaScript"
    assert normalize_skill("javascript") == "JavaScript"
    assert normalize_skill("JS") == "JavaScript"
    assert normalize_skill("ECMASCRIPT") == "JavaScript"


def test_normalize_skill_unknown() -> None:
    """Test normalizing an unknown skill (passes through)."""
    assert normalize_skill("ObscureLanguage") == "ObscureLanguage"
    assert normalize_skill("FooBar") == "FooBar"


def test_normalize_skills_deduplicates() -> None:
    """Test that normalize_skills removes duplicates."""
    result = normalize_skills(["Python", "python", "JavaScript", "JS"])
    assert result == ["Python", "JavaScript"]


def test_normalize_skills_preserves_order() -> None:
    """Test that normalize_skills preserves first-seen order."""
    result = normalize_skills(["JavaScript", "Python", "JavaScript"])
    assert result == ["JavaScript", "Python"]


def test_is_known_skill() -> None:
    """Test is_known_skill."""
    assert is_known_skill("Python") is True
    assert is_known_skill("python") is True
    assert is_known_skill("JavaScript") is True
    assert is_known_skill("ObscureLanguage") is False


def test_list_canonical_skills() -> None:
    """Test listing canonical skills."""
    skills = list_canonical_skills()
    assert "Python" in skills
    assert "JavaScript" in skills
    assert "SQL" in skills
    assert len(skills) > 0
    # Should be sorted
    assert skills == sorted(skills)


__all__ = [
    "test_normalize_skill_known",
    "test_normalize_skill_javascript",
    "test_normalize_skill_unknown",
    "test_normalize_skills_deduplicates",
    "test_normalize_skills_preserves_order",
    "test_is_known_skill",
    "test_list_canonical_skills",
]
