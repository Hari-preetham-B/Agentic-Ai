"""Profile extraction boundary.

Turns raw resume text into a structured ``ProfileDraft`` for user review.

Two layers, both producing Pydantic-validated output:

1. ``ResumeProfileExtractor`` - deterministic, section-based parsing. It needs
   no LLM or network access and never invents content: anything it cannot read
   with confidence is left out and reported in ``extraction_warnings``.
2. ``LLMAssistedProfileExtractor`` - when a real LLM provider is configured, the
   model proposes a structured profile which is validated item by item. Any
   failure (no key, bad JSON, schema mismatch) falls back to layer 1, and the
   draft warnings say which path produced the result.

Extracted skills never carry a proficiency level: the resume does not state
one, and levels drive deterministic scoring, so the user sets them in review.
The rest of the application depends on the ``ProfileExtractor`` protocol only.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, List, Optional, Protocol

from pydantic import BaseModel, Field, ValidationError

from app.schemas.profile import (
    CareerGoalCreate,
    EducationCreate,
    ExperienceCreate,
    ExtractionMetadata,
    ProfileCreate,
    ProfileDraft,
    ProjectCreate,
    SkillCreate,
)

SOURCE = "DOCUMENT_EXTRACTED"


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


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

# Canonical names match the curated career reference data so extracted skills
# line up with the deterministic skill-matching engine.
_CANONICAL_SKILLS = [
    "Python", "SQL", "JavaScript", "TypeScript", "Java", "C++", "C", "C#", "Go",
    "Rust", "R", "React", "Next.js", "Node.js", "HTML", "CSS", "Tailwind CSS",
    "Flask", "FastAPI", "Django", "Spring Boot", "REST API", "GraphQL",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Pandas", "NumPy",
    "scikit-learn", "TensorFlow", "PyTorch", "Keras", "OpenCV", "YOLO",
    "Machine Learning", "Deep Learning", "Computer Vision",
    "Natural Language Processing", "Large Language Models", "Prompt Engineering",
    "Retrieval-Augmented Generation", "LangChain", "LangGraph", "Statistics",
    "Data Analysis", "Data Visualization", "Excel", "Tableau", "Power BI",
    "Git", "GitHub", "Linux", "Docker", "Kubernetes", "AWS", "Azure",
    "Google Cloud", "CI/CD", "Terraform", "Network Security", "Cryptography",
    "Arduino", "Raspberry Pi", "Embedded Systems",
]

_ALIASES = {
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "cv": "Computer Vision",
    "nlp": "Natural Language Processing",
    "llm": "Large Language Models",
    "llms": "Large Language Models",
    "rag": "Retrieval-Augmented Generation",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "js": "JavaScript",
    "ts": "TypeScript",
    "reactjs": "React",
    "react.js": "React",
    "nextjs": "Next.js",
    "nodejs": "Node.js",
    "node": "Node.js",
    "rest": "REST API",
    "rest apis": "REST API",
    "restful apis": "REST API",
    "restful api": "REST API",
    "amazon web services": "AWS",
    "gcp": "Google Cloud",
    "k8s": "Kubernetes",
    "postgres": "PostgreSQL",
    "powerbi": "Power BI",
    "power-bi": "Power BI",
    "ms excel": "Excel",
    "microsoft excel": "Excel",
    "tailwind": "Tailwind CSS",
    "cpp": "C++",
    "yolov8": "YOLO",
    "ci cd": "CI/CD",
}

_CANON_LOOKUP = {s.lower(): s for s in _CANONICAL_SKILLS}
_CANON_LOOKUP.update(_ALIASES)

# Too ambiguous to count when found in running prose (only inside skill lists).
_AMBIGUOUS_IN_PROSE = {"c", "r", "go", "node", "rest", "cv", "dl", "ml", "js", "ts"}

_CAREER_TITLES = [
    "Machine Learning Engineer", "AI Engineer", "Data Scientist", "Data Analyst",
    "Software Engineer", "Cybersecurity Analyst", "Cloud / DevOps Engineer",
    "DevOps Engineer", "Cloud Engineer", "Product Analyst",
]

_SECTION_HEADERS = {
    "education": ["education", "academic background", "academics", "qualifications",
                  "educational qualifications", "academic qualifications"],
    "skills": ["skills", "technical skills", "core skills", "key skills",
               "competencies", "expertise", "technologies", "tech stack",
               "skills & tools", "skills and tools"],
    "projects": ["projects", "academic projects", "personal projects",
                 "key projects", "project experience", "selected projects"],
    "experience": ["experience", "work experience", "professional experience",
                   "employment", "employment history", "internships",
                   "internship experience", "work history"],
    "objective": ["objective", "career objective", "summary", "professional summary",
                  "profile", "about me", "about", "career goal", "goal"],
    "other": ["certifications", "certificates", "achievements", "awards",
              "interests", "hobbies", "languages", "references", "publications",
              "extracurricular", "extracurricular activities", "activities",
              "declaration", "courses", "honors", "positions of responsibility",
              "volunteering", "links"],
}
_HEADER_LOOKUP = {
    h: section for section, hs in _SECTION_HEADERS.items() for h in hs
}

_BULLET = re.compile(r"^\s*(?:[-\u2022\u25cf\u25aa\u2013\u2014*\u00b7>]+|\d+[.)])\s+")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
_URL = re.compile(r"(?:https?://|www\.|linkedin\.com|github\.com)\S+", re.I)
_YEAR = r"(?:19|20)\d{2}"
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_DATE_TOKEN = re.compile(
    rf"(?:(?P<mon>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+)?(?P<year>{_YEAR})",
    re.I,
)
_MONTH_NAME = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
_RANGE = re.compile(
    rf"(?P<start>(?:{_MONTH_NAME}\.?,?\s+)?{_YEAR})\s*(?:-|\u2013|\u2014|to)\s*"
    rf"(?P<end>(?:{_MONTH_NAME}\.?,?\s+)?(?:{_YEAR}|present|current|ongoing|now))",
    re.I,
)
_DEGREE = re.compile(
    r"\b(b\.?\s?e\.?|b\.?\s?tech\.?|m\.?\s?tech\.?|m\.?\s?e\.?|b\.?\s?sc\.?|m\.?\s?sc\.?|"
    r"b\.?\s?c\.?\s?a\.?|m\.?\s?c\.?\s?a\.?|mba|ph\.?\s?d\.?|bachelor(?:'s)?(?: of [a-z]+)?|"
    r"master(?:'s)?(?: of [a-z]+)?|diploma|pre[- ]?university|higher secondary|"
    r"intermediate|ssc|hsc|class (?:x|xii|10|12)|10th|12th)(?![\w])",
    re.I,
)
_INSTITUTION = re.compile(
    r"\b(institute|university|college|school|academy|iit|nit|iiit|polytechnic|"
    r"vidyalaya|campus)\b",
    re.I,
)
_ROLE_WORDS = re.compile(
    r"\b(intern(?:ship)?|engineer|developer|analyst|trainee|associate|manager|lead|"
    r"researcher|research|assistant|scientist|consultant|volunteer|member|"
    r"coordinator|designer|architect|executive|apprentice|fellow|head|captain)\b",
    re.I,
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip(" \t|-:,;\u2022")


def _canon_skill(raw: str) -> Optional[str]:
    token = _clean(raw).strip(".,;()[]")
    if not token or len(token) > 40 or len(token.split()) > 4:
        return None
    key = token.lower()
    if key in _CANON_LOOKUP:
        return _CANON_LOOKUP[key]
    # Keep unfamiliar-but-plausible tokens as written (the user reviews them).
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9+#./ &-]*", token):
        return token
    return None


def _scan_vocabulary(text: str) -> List[str]:
    """Return canonical skills mentioned anywhere in ``text`` (whole words)."""
    found: List[str] = []
    lowered = text.lower()
    for key, canon in _CANON_LOOKUP.items():
        if key in _AMBIGUOUS_IN_PROSE:
            continue
        if re.search(rf"(?<![\w+#]){re.escape(key)}(?![\w+#])", lowered):
            if canon not in found:
                found.append(canon)
    return found


def _to_date(token: str) -> Optional[date]:
    m = _DATE_TOKEN.search(token)
    if not m:
        return None
    month = _MONTHS.get((m.group("mon") or "")[:3].lower(), 1)
    try:
        return date(int(m.group("year")), month, 1)
    except ValueError:
        return None


def _parse_range(text: str) -> tuple[Optional[date], Optional[date], bool]:
    m = _RANGE.search(text)
    if not m:
        return None, None, False
    start = _to_date(m.group("start"))
    end_raw = m.group("end")
    current = bool(re.search(r"present|current|ongoing|now", end_raw, re.I))
    end = None if current else _to_date(end_raw)
    if start and end and end < start:
        return None, None, current
    return start, end, current


def _strip_dates(text: str) -> str:
    text = _RANGE.sub("", text)
    text = _DATE_TOKEN.sub("", text)
    return _clean(re.sub(r"[()\[\]]", " ", text))


def _is_bullet(line: str) -> bool:
    return bool(_BULLET.match(line))


def _unbullet(line: str) -> str:
    return _clean(_BULLET.sub("", line))


# ---------------------------------------------------------------------------
# Deterministic extractor
# ---------------------------------------------------------------------------


class ResumeProfileExtractor:
    """Deterministic, section-based resume parser (no LLM, no network)."""

    async def extract(
        self,
        document_text: str,
        *,
        source_type: str,
        source_file_name: Optional[str] = None,
    ) -> ProfileDraft:
        text = (document_text or "").replace("\r\n", "\n").replace("\r", "\n")
        warnings: List[str] = []
        if not text.strip():
            warnings.append(
                "No text could be extracted. Scanned or image-only resumes are not "
                "supported (OCR is out of scope); enter your details manually."
            )
            return ProfileDraft(
                profile=ProfileCreate(profile_status="DRAFT"),
                extraction_metadata=ExtractionMetadata(
                    source_type=source_type,
                    source_file_name=source_file_name,
                    extraction_warnings=warnings,
                ),
            )

        header_lines, sections = self._split_sections(text)
        profile = self._profile(header_lines, sections, text)

        education = self._education(sections.get("education", []), warnings)
        skills = self._skills(sections.get("skills", []), text)
        projects = self._projects(sections.get("projects", []))
        experience = self._experience(sections.get("experience", []), warnings)
        goals = self._goals(sections.get("objective", []))

        if not profile.full_name:
            warnings.append("Could not identify your name; please enter it.")
        if not education:
            warnings.append("No education entries were detected; please add them.")
        if not skills:
            warnings.append("No skills were detected; please add your skills.")
        else:
            warnings.append(
                "Skill proficiency is not stated on resumes; set a level for each "
                "skill before confirming."
            )
        if not goals:
            warnings.append("No career goal was detected; add a target role.")

        return ProfileDraft(
            profile=profile,
            education=education,
            skills=skills,
            projects=projects,
            experience=experience,
            career_goals=goals,
            extraction_metadata=ExtractionMetadata(
                source_type=source_type,
                source_file_name=source_file_name,
                extraction_warnings=warnings,
            ),
        )

    # -- structure -----------------------------------------------------

    def _split_sections(self, text: str) -> tuple[List[str], dict[str, List[str]]]:
        header_lines: List[str] = []
        sections: dict[str, List[str]] = {}
        current: Optional[str] = None
        for raw in text.split("\n"):
            line = raw.strip()
            if not line:
                continue
            matched, remainder = self._match_header(line)
            if matched:
                current = matched
                sections.setdefault(current, [])
                if remainder:
                    sections[current].append(remainder)
                continue
            if current is None:
                header_lines.append(line)
            else:
                sections[current].append(line)
        return header_lines, sections

    @staticmethod
    def _match_header(line: str) -> tuple[Optional[str], str]:
        bare = re.sub(r"[#*_=\-:|\u2022]+", " ", line).strip().lower()
        bare = re.sub(r"\s+", " ", bare)
        if bare in _HEADER_LOOKUP:
            return _HEADER_LOOKUP[bare], ""
        # Inline form: "Skills: Python, SQL"
        m = re.match(r"^([A-Za-z &]{3,40}?)\s*[:\u2013\u2014-]\s+(.+)$", line)
        if m and m.group(1).strip().lower() in _HEADER_LOOKUP:
            return _HEADER_LOOKUP[m.group(1).strip().lower()], m.group(2).strip()
        return None, ""

    # -- profile -------------------------------------------------------

    def _profile(self, header: List[str], sections, text: str) -> ProfileCreate:
        email = _EMAIL.search(text)
        phone = None
        for line in header[:8]:
            candidate = _PHONE.search(_EMAIL.sub("", line))
            if candidate and 10 <= sum(ch.isdigit() for ch in candidate.group(0)) <= 15:
                phone = _clean(candidate.group(0))
                break

        full_name = None
        name_index = -1
        for i, line in enumerate(header[:6]):
            if _EMAIL.search(line) or _URL.search(line):
                continue
            words = line.split()
            if 1 <= len(words) <= 6 and not any(ch.isdigit() for ch in line):
                full_name = _clean(line)[:200]
                name_index = i
                break

        headline = None
        if name_index >= 0:
            for line in header[name_index + 1: name_index + 4]:
                if _EMAIL.search(line) or _URL.search(line) or _PHONE.search(line):
                    continue
                if 3 <= len(line) <= 120:
                    headline = _clean(line)[:300]
                    break

        summary_lines = sections.get("objective", [])
        summary = _clean(" ".join(_unbullet(l) for l in summary_lines))[:2000] or None

        return ProfileCreate(
            full_name=full_name,
            headline=headline,
            email=email.group(0)[:200] if email else None,
            phone=phone,
            location=None,
            summary=summary,
            profile_status="DRAFT",
        )

    # -- education -----------------------------------------------------

    def _education(self, lines: List[str], warnings: List[str]) -> List[EducationCreate]:
        entries: List[dict[str, Any]] = []
        for raw in lines:
            line = _unbullet(raw)
            if not line:
                continue
            degree_match = _DEGREE.search(line)
            has_degree = bool(degree_match)
            # "Pre-University" is a qualification, not an institution name.
            without_degree = line.replace(degree_match.group(0), " ") if degree_match else line
            has_inst = bool(_INSTITUTION.search(without_degree))
            has_year = bool(re.search(_YEAR, line))
            if not (has_inst or has_degree or has_year):
                if entries and len(line) < 200:
                    entries[-1].setdefault("notes", []).append(line)
                continue
            current = entries[-1] if entries else None
            starts_new = (
                current is None
                or (has_inst and current.get("institution"))
                or (has_degree and current.get("degree") and not has_inst)
            )
            if starts_new:
                current = {}
                entries.append(current)
            if has_inst and not current.get("institution"):
                current["institution"] = line
            if has_degree and not current.get("degree"):
                current["degree_line"] = line
                current["degree"] = _DEGREE.search(line).group(0)
            if has_year and "dates" not in current:
                current["dates"] = line

        result: List[EducationCreate] = []
        for e in entries:
            institution = e.get("institution")
            if not institution:
                continue  # never fabricate an institution
            start, end, _ = _parse_range(e.get("dates", institution))
            if end is None and not start:
                years = re.findall(_YEAR, e.get("dates", ""))
                if years:
                    end = date(int(years[-1]), 1, 1)
            inst_text = _strip_dates(institution)
            degree = field = None
            if e.get("degree"):
                dl = e["degree_line"]
                token = _DEGREE.search(dl).group(0)
                degree = _clean(token).rstrip(".")
                rest = _strip_dates(dl.replace(token, "", 1))
                rest = rest.strip(" ,-\u2013\u2014:")
                rest = re.sub(r"^(?:in|of)\s+", "", rest, flags=re.I)
                if _INSTITUTION.search(rest):
                    rest = ""
                field = _clean(rest)[:200] or None
                if institution == dl:
                    inst_text = _strip_dates(dl.replace(token, "", 1))
            inst_text = _clean(
                re.sub(r"\b(?:cgpa|gpa|percentage)\b.*$", "", inst_text, flags=re.I)
            )
            if not inst_text:
                continue
            try:
                result.append(EducationCreate(
                    institution=inst_text[:200], degree=degree, field_of_study=field,
                    start_date=start, end_date=end,
                    description=_clean(" ".join(e.get("notes", [])))[:2000] or None,
                ))
            except ValidationError:
                warnings.append(
                    f"Skipped an education entry that could not be read: {inst_text[:60]}"
                )
        return result

    # -- skills --------------------------------------------------------

    def _skills(self, lines: List[str], full_text: str) -> List[SkillCreate]:
        found: dict[str, SkillCreate] = {}

        def add(name: Optional[str], category: Optional[str] = None) -> None:
            if not name or name.lower() in found:
                return
            found[name.lower()] = SkillCreate(
                name=name[:100], category=category, proficiency=None,
                years_experience=None, source=SOURCE,
            )

        for raw in lines:
            line = _unbullet(raw)
            category = None
            m = re.match(r"^([A-Za-z &/]{2,30})\s*:\s*(.+)$", line)
            if m:
                category = _clean(m.group(1))[:100]
                line = m.group(2)
            for part in re.split(r"[,;|\u2022\u00b7]|\s{2,}|\s/\s", line):
                add(_canon_skill(part), category)
        # Skills named elsewhere (projects, experience) that match the curated
        # vocabulary are also reported, so nothing the resume evidences is lost.
        for canon in _scan_vocabulary(full_text):
            add(canon)
        return list(found.values())[:60]

    # -- projects ------------------------------------------------------

    def _projects(self, lines: List[str]) -> List[ProjectCreate]:
        result: List[ProjectCreate] = []
        for head, body in self._blocks(lines):
            name, rest = self._split_title(head)
            blob = " ".join([rest] + body)
            techs = self._technologies(blob + " " + head)
            desc = _clean(" ".join([rest] + body))[:2000] or None
            start, end, _ = _parse_range(head)
            name = _strip_dates(name)[:200]
            if not name:
                continue
            try:
                result.append(ProjectCreate(
                    name=name, description=desc, technologies=techs or None,
                    start_date=start, end_date=end, source=SOURCE,
                ))
            except ValidationError:
                continue
        return result[:15]

    @staticmethod
    def _technologies(text: str) -> List[str]:
        techs: List[str] = []
        m = re.search(
            r"(?:tech(?:nologies|nology)?|tools?|stack|built with|using)\s*[:\-]\s*([^.\n]+)",
            text, re.I,
        )
        if m:
            for part in re.split(r"[,;|/]", m.group(1)):
                canon = _canon_skill(part)
                if canon and canon not in techs:
                    techs.append(canon)
        for canon in _scan_vocabulary(text):
            if canon not in techs:
                techs.append(canon)
        return techs[:15]

    # -- experience ----------------------------------------------------

    def _experience(self, lines: List[str], warnings: List[str]) -> List[ExperienceCreate]:
        result: List[ExperienceCreate] = []
        for head, body in self._blocks(lines):
            start, end, current = _parse_range(head)
            title = _strip_dates(head)
            org, role = self._org_role(title)
            if not org:
                continue
            if role is None:
                role = "Role to be confirmed"
                warnings.append(f"Role for '{org[:40]}' was not clear; please review.")
            desc = _clean(" ".join(body))[:2000] or None
            try:
                result.append(ExperienceCreate(
                    organization=org[:200], role=role[:200], description=desc,
                    start_date=start, end_date=end, is_current=current, source=SOURCE,
                ))
            except ValidationError:
                continue
        return result[:15]

    @staticmethod
    def _org_role(title: str) -> tuple[Optional[str], Optional[str]]:
        title = _clean(title)
        if not title:
            return None, None
        parts = [
            _clean(p)
            for p in re.split(
                r"\s+(?:at|@)\s+|\s+[\u2013\u2014-]\s+|\s*\|\s*|,\s+", title
            )
            if _clean(p)
        ][:3]
        if not parts:
            return None, None
        if len(parts) == 1:
            if _ROLE_WORDS.search(parts[0]):
                return None, None  # a role with no organisation: do not guess one
            return parts[0], None
        a, b = parts[0], parts[1]
        a_role, b_role = bool(_ROLE_WORDS.search(a)), bool(_ROLE_WORDS.search(b))
        if a_role and not b_role:
            return b, a
        return a, b

    # -- goals ---------------------------------------------------------

    def _goals(self, lines: List[str]) -> List[CareerGoalCreate]:
        objective = _clean(" ".join(_unbullet(l) for l in lines))
        if not objective:
            return []
        for title in _CAREER_TITLES:
            if re.search(rf"\b{re.escape(title)}\b", objective, re.I):
                return [CareerGoalCreate(
                    target_role=title, goal_description=objective[:1000], priority=1,
                )]
        m = re.search(
            r"(?:seeking|aspiring|looking for|aim(?:ing)? to (?:become|be)|as)\s+(?:an?\s+)?"
            r"([A-Z][A-Za-z/&+ -]{3,50}?)(?:\s+(?:role|position|opportunit\w+|intern\w*)|[.,;]|$)",
            objective,
        )
        if m:
            return [CareerGoalCreate(
                target_role=_clean(m.group(1))[:200],
                goal_description=objective[:1000], priority=1,
            )]
        return []

    # -- generic blocks / titles ---------------------------------------

    @staticmethod
    def _blocks(lines: List[str]) -> List[tuple[str, List[str]]]:
        """Group section lines into (heading, body) entries.

        A non-bullet line starts a new entry; bullet lines and lowercase-start
        continuation lines belong to the current entry.
        """
        blocks: List[tuple[str, List[str]]] = []
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            if not blocks:
                blocks.append((_unbullet(line), []))
            elif _is_bullet(line):
                blocks[-1][1].append(_unbullet(line))
            elif line[:1].islower() or blocks[-1][0].endswith((",", "-", "and")):
                blocks[-1][1].append(_clean(line))
            else:
                blocks.append((_clean(line), []))
        return blocks

    @staticmethod
    def _split_title(head: str) -> tuple[str, str]:
        m = re.match(r"^(.{3,90}?)\s*(?:\s[\u2013\u2014-]\s|:\s|\s\|\s)\s*(.+)$", head)
        if m:
            return _clean(m.group(1)), _clean(m.group(2))
        return _clean(head), ""


# ---------------------------------------------------------------------------
# Optional LLM-assisted layer
# ---------------------------------------------------------------------------


class _LLMEducation(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None


class _LLMSkill(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None


class _LLMProject(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)


class _LLMExperience(BaseModel):
    organization: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    is_current: bool = False


class _LLMGoal(BaseModel):
    target_role: Optional[str] = None
    goal_description: Optional[str] = None


class LLMResumeProfile(BaseModel):
    """Lenient model the LLM fills in; validated again into strict schemas."""

    full_name: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    education: List[_LLMEducation] = Field(default_factory=list)
    skills: List[_LLMSkill] = Field(default_factory=list)
    projects: List[_LLMProject] = Field(default_factory=list)
    experience: List[_LLMExperience] = Field(default_factory=list)
    career_goals: List[_LLMGoal] = Field(default_factory=list)


_LLM_INSTRUCTIONS = (
    "Extract a structured student profile from the resume text. Use ONLY facts "
    "present in the text; never invent employers, dates, degrees or skills. "
    "Leave a field null or omit an item when unsure. Do not infer skill levels. "
    "Return JSON matching the schema."
)


class LLMAssistedProfileExtractor:
    """Uses a configured LLM to structure a resume, validated and merged.

    Contact details (email/phone) always come from the deterministic parser.
    Falls back to the deterministic draft on any failure.
    """

    def __init__(
        self, llm_provider: Any, fallback: Optional[ResumeProfileExtractor] = None
    ) -> None:
        self.llm = llm_provider
        self.fallback = fallback or ResumeProfileExtractor()

    async def extract(
        self,
        document_text: str,
        *,
        source_type: str,
        source_file_name: Optional[str] = None,
    ) -> ProfileDraft:
        base = await self.fallback.extract(
            document_text, source_type=source_type, source_file_name=source_file_name
        )
        if not (document_text or "").strip():
            return base
        try:
            parsed = await self._ask(document_text)
            return self._merge(base, parsed)
        except Exception as exc:  # noqa: BLE001 - any LLM failure -> deterministic draft
            base.extraction_metadata.extraction_warnings.append(
                f"LLM structuring unavailable ({type(exc).__name__}); used the "
                "deterministic parser instead."
            )
            return base

    async def _ask(self, text: str) -> LLMResumeProfile:
        messages = [
            {"role": "system", "content": _LLM_INSTRUCTIONS},
            {"role": "user", "content": f"Resume text:\n\n{text[:12000]}"},
        ]
        response = await self.llm.generate(messages, response_schema=LLMResumeProfile)
        data = getattr(response, "structured_output", None)
        if data is None:
            data = json.loads(getattr(response, "content", "") or "")
        return LLMResumeProfile.model_validate(data)

    def _merge(self, base: ProfileDraft, parsed: LLMResumeProfile) -> ProfileDraft:
        warnings = list(base.extraction_metadata.extraction_warnings)
        profile = base.profile.model_copy(update={
            "full_name": parsed.full_name or base.profile.full_name,
            "headline": parsed.headline or base.profile.headline,
            "summary": parsed.summary or base.profile.summary,
        })

        education: List[EducationCreate] = []
        for e in parsed.education:
            if not e.institution:
                continue
            try:
                education.append(EducationCreate(
                    institution=e.institution[:200], degree=e.degree,
                    field_of_study=e.field_of_study,
                    start_date=date(e.start_year, 1, 1) if e.start_year else None,
                    end_date=date(e.end_year, 1, 1) if e.end_year else None,
                ))
            except (ValidationError, ValueError):
                continue

        skills: dict[str, SkillCreate] = {}
        for s in parsed.skills:
            name = _canon_skill(s.name or "")
            if name and name.lower() not in skills:
                skills[name.lower()] = SkillCreate(
                    name=name, category=s.category, proficiency=None, source=SOURCE)
        for s in base.skills:  # keep deterministic finds the model missed
            skills.setdefault(s.name.lower(), s)

        projects: List[ProjectCreate] = []
        for p in parsed.projects:
            if not p.name:
                continue
            try:
                projects.append(ProjectCreate(
                    name=p.name[:200], description=p.description or None,
                    technologies=p.technologies[:15] or None, source=SOURCE))
            except ValidationError:
                continue

        experience: List[ExperienceCreate] = []
        for x in parsed.experience:
            if not (x.organization and x.role):
                continue
            try:
                experience.append(ExperienceCreate(
                    organization=x.organization[:200], role=x.role[:200],
                    description=x.description, is_current=x.is_current, source=SOURCE))
            except ValidationError:
                continue

        goals: List[CareerGoalCreate] = []
        for g in parsed.career_goals:
            if g.target_role:
                goals.append(CareerGoalCreate(
                    target_role=g.target_role[:200],
                    goal_description=g.goal_description, priority=len(goals) + 1))

        warnings.append(
            "Structured with the configured LLM; review every field before confirming."
        )
        return ProfileDraft(
            profile=profile,
            education=education or base.education,
            skills=list(skills.values())[:60],
            projects=projects or base.projects,
            experience=experience or base.experience,
            career_goals=goals or base.career_goals,
            extraction_metadata=base.extraction_metadata.model_copy(
                update={"extraction_warnings": warnings}),
        )


# Backwards-compatible alias for the old stub's name.
MockProfileExtractor = ResumeProfileExtractor

# Module-level deterministic default instance.
profile_extractor = ResumeProfileExtractor()


def build_profile_extractor() -> ProfileExtractor:
    """Return the LLM-assisted extractor when a real provider is configured."""
    try:
        from app.core.providers import create_llm_provider

        provider = create_llm_provider()
        if getattr(provider, "provider_name", "fake") != "fake":
            return LLMAssistedProfileExtractor(provider)
    except Exception:  # noqa: BLE001 - missing key etc. -> deterministic only
        pass
    return profile_extractor
