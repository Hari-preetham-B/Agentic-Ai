"""Deterministic skill normalization.

Maps variant skill spellings to canonical skill names. This is intentionally
small and explainable — not a full ontology. Unknown skills pass through
unchanged so they can still be matched exactly when they appear in career
requirements.

The normalization map is keyed by lowercase, punctuation-stripped skill
names. The value is the canonical skill name used throughout CareerTwin.
"""

from __future__ import annotations

import re
from typing import Any


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Canonical -> list of aliases
_SKILL_ALIASES: dict[str, list[str]] = {
    "Python": ["python", "python 3", "python3", "python programming", "py"],
    "JavaScript": ["javascript", "js", "ecmascript"],
    "TypeScript": ["typescript", "ts"],
    "Java": ["java"],
    "SQL": ["sql", "structured query language"],
    "NoSQL": ["nosql", "no sql"],
    "MongoDB": ["mongodb", "mongo"],
    "PostgreSQL": ["postgresql", "postgres", "postgres sql"],
    "MySQL": ["mysql", "my sql"],
    "Redis": ["redis"],
    "Git": ["git", "version control"],
    "Docker": ["docker", "containerization"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure", "microsoft azure"],
    "GCP": ["gcp", "google cloud", "google cloud platform"],
    "React": ["react", "react.js", "reactjs"],
    "Vue": ["vue", "vue.js", "vuejs"],
    "Angular": ["angular", "angular.js"],
    "Node.js": ["node", "node.js", "nodejs"],
    "PyTorch": ["pytorch", "torch"],
    "TensorFlow": ["tensorflow", "tf"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy", "num py"],
    "Tableau": ["tableau"],
    "Power BI": ["power bi", "powerbi"],
    "Excel": ["excel", "microsoft excel"],
    "Linux": ["linux"],
    "REST API": ["rest api", "restful api", "rest"],
    "GraphQL": ["graphql"],
    "Machine Learning": ["machine learning", "ml"],
    "Deep Learning": ["deep learning", "dl"],
    "Natural Language Processing": ["nlp", "natural language processing"],
    "Computer Vision": ["computer vision", "cv"],
    "Prompt Engineering": ["prompt engineering", "prompting"],
    "Retrieval-Augmented Generation": ["rag", "retrieval-augmented generation"],
    "Data Visualization": ["data visualization", "dataviz"],
    "A/B Testing": ["ab testing", "a/b testing", "split testing"],
    "Statistics": ["statistics", "stats"],
    "Probability": ["probability"],
    "Linear Algebra": ["linear algebra"],
    "Calculus": ["calculus"],
}

# Build the reverse lookup: normalized alias -> canonical name
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in _SKILL_ALIASES.items():
    _ALIAS_TO_CANONICAL[_normalize(canonical)] = canonical
    for alias in aliases:
        _ALIAS_TO_CANONICAL[_normalize(alias)] = canonical


def normalize_skill(skill_name: str) -> str:
    """Return the canonical name for a skill, or the original if unknown."""
    key = _normalize(skill_name)
    return _ALIAS_TO_CANONICAL.get(key, skill_name.strip())


def normalize_skills(skill_names: list[str]) -> list[str]:
    """Normalize a list of skill names, preserving order and removing duplicates."""
    seen: set[str] = set()
    result: list[str] = []
    for name in skill_names:
        canonical = normalize_skill(name)
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result


def is_known_skill(skill_name: str) -> bool:
    """Return True if the skill name maps to a known canonical skill."""
    return _normalize(skill_name) in _ALIAS_TO_CANONICAL


def list_canonical_skills() -> list[str]:
    """Return all known canonical skill names."""
    return sorted({v for v in _ALIAS_TO_CANONICAL.values()})


__all__ = [
    "normalize_skill",
    "normalize_skills",
    "is_known_skill",
    "list_canonical_skills",
]
