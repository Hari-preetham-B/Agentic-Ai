"""Deterministic profile validation service.

Validation is application-logic, not agent logic. It checks structural
integrity and business rules before a profile can be confirmed.

Warnings do not block confirmation; errors do.
"""

from typing import List

from app.schemas.profile import (
    PROFICIENCIES,
    PROFILE_STATUSES,
    SOURCES,
    EducationCreate,
    ExperienceCreate,
    ProfileCreate,
    ProjectCreate,
    SkillCreate,
    ValidationErrorDetail,
    ValidationResult,
)


def _err(field: str, code: str, message: str) -> ValidationErrorDetail:
    return ValidationErrorDetail(field=field, code=code, message=message)


def validate_profile(profile: ProfileCreate) -> ValidationResult:
    """Validate top-level profile fields.

    Errors prevent confirmation; warnings are advisory.
    """
    errors: List[ValidationErrorDetail] = []
    warnings: List[ValidationErrorDetail] = []

    if not profile.full_name or not profile.full_name.strip():
        errors.append(_err("full_name", "REQUIRED", "Full name is required."))
    elif len(profile.full_name.strip()) < 2:
        errors.append(
            _err(
                "full_name",
                "TOO_SHORT",
                "Full name must be at least 2 characters.",
            )
        )

    if profile.email and "@" not in profile.email:
        errors.append(_err("email", "INVALID", "Email must contain an '@'."))

    if profile.profile_status not in PROFILE_STATUSES:
        errors.append(
            _err(
                "profile_status",
                "INVALID",
                f"profile_status must be one of {', '.join(PROFILE_STATUSES)}.",
            )
        )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_children(
    education: List[EducationCreate],
    skills: List[SkillCreate],
    projects: List[ProjectCreate],
    experience: List[ExperienceCreate],
    career_goals: List,
) -> ValidationResult:
    """Validate child record collections.

    Returns combined validation result across all child collections.
    """
    errors: List[ValidationErrorDetail] = []
    warnings: List[ValidationErrorDetail] = []

    # At least one of education, experience, or project is expected.
    if not education and not experience and not projects:
        warnings.append(
            _err(
                "background",
                "SUGGESTED",
                "Consider adding education, experience, or at least one project.",
            )
        )

    # At least one skill is required for a meaningful profile.
    if not skills:
        errors.append(
            _err(
                "skills",
                "REQUIRED",
                "At least one skill is required.",
            )
        )

    # At least one career goal is required before confirmation.
    if not career_goals:
        errors.append(
            _err(
                "career_goals",
                "REQUIRED",
                "At least one career goal is required before confirmation.",
            )
        )

    # Validate each skill.
    for idx, skill in enumerate(skills):
        field = f"skills[{idx}]"
        if not skill.name or not skill.name.strip():
            errors.append(_err(field, "REQUIRED", "Skill name is required."))
        elif skill.proficiency and skill.proficiency not in PROFICIENCIES:
            errors.append(
                _err(
                    field,
                    "INVALID",
                    f"proficiency must be one of {', '.join(PROFICIENCIES)}.",
                )
            )
        if skill.source not in SOURCES:
            errors.append(
                _err(
                    field,
                    "INVALID",
                    f"source must be one of {', '.join(SOURCES)}.",
                )
            )

    # Validate date ordering for education, projects, experience.
    for idx, edu in enumerate(education):
        field = f"education[{idx}]"
        if edu.start_date and edu.end_date and edu.end_date < edu.start_date:
            errors.append(
                _err(field, "INVALID_DATE", "end_date must not be before start_date.")
            )

    for idx, proj in enumerate(projects):
        field = f"projects[{idx}]"
        if proj.start_date and proj.end_date and proj.end_date < proj.start_date:
            errors.append(
                _err(field, "INVALID_DATE", "end_date must not be before start_date.")
            )

    for idx, exp in enumerate(experience):
        field = f"experience[{idx}]"
        if exp.start_date and exp.end_date and exp.end_date < exp.start_date:
            errors.append(
                _err(field, "INVALID_DATE", "end_date must not be before start_date.")
            )

    # Duplicate skill names (obvious duplicates).
    seen_skill_names = set()
    for idx, skill in enumerate(skills):
        key = skill.name.strip().lower()
        if key in seen_skill_names:
            errors.append(
                _err(
                    f"skills[{idx}]",
                    "DUPLICATE",
                    f"Duplicate skill '{skill.name}'.",
                )
            )
        seen_skill_names.add(key)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_for_confirmation(
    profile: ProfileCreate,
    education: List[EducationCreate],
    skills: List[SkillCreate],
    projects: List[ProjectCreate],
    experience: List[ExperienceCreate],
    career_goals: List,
) -> ValidationResult:
    """Run full validation required before a profile can be confirmed.

    Combines top-level and child validation. Errors block confirmation.
    """
    profile_result = validate_profile(profile)
    children_result = validate_children(
        education, skills, projects, experience, career_goals
    )

    errors = profile_result.errors + children_result.errors
    warnings = profile_result.warnings + children_result.warnings

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
