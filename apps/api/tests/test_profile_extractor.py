"""Tests for the resume profile extractor (deterministic + LLM-assisted)."""

import pytest

from app.services.profile_extractor import (
    LLMAssistedProfileExtractor,
    LLMResumeProfile,
    ResumeProfileExtractor,
)

RESUME_A = """Hari Preetham
AI/ML Engineering Student
hari@example.com | +91 98765 43210 | github.com/hari

Career Objective
Aspiring Machine Learning Engineer seeking an internship in applied AI.

Education
CMR Institute of Technology, Bengaluru
B.E. Artificial Intelligence and Machine Learning, 2023 - 2027
Sri Chaitanya PU College
Pre-University, 2021 - 2023

Skills
Languages: Python, SQL, JavaScript
ML: Machine Learning, Deep Learning, PyTorch, scikit-learn, OpenCV
Tools: Git, Docker, Linux

Projects
Crowd Panic Detection - Real-time panic scoring from video
- Built tracking and optical flow pipeline
- Technologies: Python, OpenCV, Flask
Fire and Smoke Detection
- YOLOv8 model trained on D-Fire dataset

Experience
Machine Learning Intern - SmartBridge, Jun 2024 - Aug 2024
- Built a classification model
InAmigos Foundation - Volunteer, 2023 - Present
"""

RESUME_B = """Jane Doe
jane@doe.org
SKILLS: Python, SQL, Excel
EDUCATION
University of Mysore - B.Sc. Statistics 2020-2023
"""


@pytest.mark.asyncio
async def test_full_resume_is_structured_and_valid():
    draft = await ResumeProfileExtractor().extract(RESUME_A, source_type="RESUME_TXT")
    assert draft.profile.full_name == "Hari Preetham"
    assert draft.profile.email == "hari@example.com"
    assert draft.profile.phone and "98765" in draft.profile.phone
    assert draft.profile.profile_status == "DRAFT"

    insts = [e.institution for e in draft.education]
    assert any("CMR Institute of Technology" in i for i in insts)
    cmr = next(e for e in draft.education if "CMR" in e.institution)
    assert cmr.start_date.year == 2023 and cmr.end_date.year == 2027
    assert cmr.degree and "B.E" in cmr.degree

    names = {s.name for s in draft.skills}
    assert {"Python", "SQL", "Machine Learning", "PyTorch", "scikit-learn", "Docker"} <= names
    assert all(s.proficiency is None for s in draft.skills)  # never inferred
    assert all(s.source == "DOCUMENT_EXTRACTED" for s in draft.skills)

    pnames = [p.name for p in draft.projects]
    assert "Crowd Panic Detection" in pnames
    crowd = next(p for p in draft.projects if p.name == "Crowd Panic Detection")
    assert "OpenCV" in (crowd.technologies or [])
    assert all(p.source == "DOCUMENT_EXTRACTED" for p in draft.projects)

    orgs = {x.organization: x for x in draft.experience}
    assert "SmartBridge" in orgs and orgs["SmartBridge"].role == "Machine Learning Intern"
    assert "InAmigos Foundation" in orgs and orgs["InAmigos Foundation"].is_current

    assert draft.career_goals and draft.career_goals[0].target_role == "Machine Learning Engineer"


@pytest.mark.asyncio
async def test_inline_section_headers_and_minimal_resume():
    draft = await ResumeProfileExtractor().extract(RESUME_B, source_type="RESUME_TXT")
    assert draft.profile.full_name == "Jane Doe"
    assert {"Python", "SQL", "Excel"} <= {s.name for s in draft.skills}
    assert draft.education and "Mysore" in draft.education[0].institution
    # Missing sections are reported, never fabricated.
    assert draft.projects == [] and draft.experience == []
    assert any("career goal" in w.lower() for w in draft.extraction_metadata.extraction_warnings)


@pytest.mark.asyncio
async def test_empty_text_gives_warning_not_error():
    draft = await ResumeProfileExtractor().extract("   ", source_type="RESUME_PDF")
    assert draft.education == [] and draft.skills == []
    assert any("No text" in w for w in draft.extraction_metadata.extraction_warnings)


@pytest.mark.asyncio
async def test_no_placeholder_items_are_ever_emitted():
    text = "Some Name\nEducation\nProjects\nExperience\n"
    draft = await ResumeProfileExtractor().extract(text, source_type="RESUME_TXT")
    assert draft.education == [] and draft.projects == [] and draft.experience == []


class _Resp:
    def __init__(self, structured=None, content=""):
        self.structured_output = structured
        self.content = content


class _StubLLM:
    provider_name = "stub"

    def __init__(self, response=None, error=None):
        self.response, self.error = response, error

    async def generate(self, messages, **kwargs):
        if self.error:
            raise self.error
        return self.response


@pytest.mark.asyncio
async def test_llm_result_is_validated_and_merged():
    payload = LLMResumeProfile(
        full_name="Hari Preetham",
        education=[{"institution": "CMR Institute of Technology", "degree": "B.E.", "start_year": 2023, "end_year": 2027},
                   {"institution": None}],
        skills=[{"name": "Python"}, {"name": "x" * 90}],
        experience=[{"organization": "SmartBridge", "role": "Intern"}, {"organization": "NoRole"}],
    ).model_dump()
    ex = LLMAssistedProfileExtractor(_StubLLM(_Resp(structured=payload)))
    draft = await ex.extract(RESUME_A, source_type="RESUME_TXT")
    assert draft.education[0].end_date.year == 2027
    assert [x.organization for x in draft.experience] == ["SmartBridge"]  # invalid item dropped
    assert "x" * 90 not in {s.name for s in draft.skills}
    assert all(s.proficiency is None for s in draft.skills)
    assert draft.profile.email == "hari@example.com"  # contact details stay deterministic
    assert any("LLM" in w for w in draft.extraction_metadata.extraction_warnings)


@pytest.mark.asyncio
@pytest.mark.parametrize("llm", [
    _StubLLM(error=RuntimeError("quota")),
    _StubLLM(_Resp(structured=None, content="not json")),
    _StubLLM(_Resp(structured={"education": "oops"})),
])
async def test_llm_failure_falls_back_to_deterministic(llm):
    draft = await LLMAssistedProfileExtractor(llm).extract(RESUME_A, source_type="RESUME_TXT")
    assert draft.profile.full_name == "Hari Preetham"
    assert draft.skills and draft.education
    assert any("deterministic parser" in w for w in draft.extraction_metadata.extraction_warnings)
