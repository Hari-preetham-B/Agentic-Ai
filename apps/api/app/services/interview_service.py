"""Adaptive interview services.

Deterministic interview control: session state, question selection, difficulty
progression, skill performance aggregation, and completion logic.

LLMs may assist with question wording and answer evaluation, but all state
transitions, selection, scoring aggregation, and completion are deterministic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import (
    InterviewEvaluation,
    InterviewQuestion,
    InterviewQuestionSkill,
    InterviewSession,
    InterviewSkillResult,
    InterviewTurn,
)
from app.models.profile import Profile, Skill


# ---------------------------------------------------------------------------
# Session status transitions
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[str, set[str]] = {
    "CREATED": {"ACTIVE", "ABANDONED"},
    "ACTIVE": {"PAUSED", "COMPLETED", "ABANDONED"},
    "PAUSED": {"ACTIVE", "ABANDONED"},
    "COMPLETED": set(),
    "ABANDONED": set(),
}


class InterviewSessionService:
    """Manages interview session lifecycle with explicit state transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(
        self,
        *,
        profile_id: str,
        career_id: str | None = None,
        mode: str = "MIXED",
        difficulty: str = "MEDIUM",
        target_question_count: int = 10,
        metadata: dict[str, Any] | None = None,
    ) -> InterviewSession:
        """Create a new interview session in CREATED state."""
        session = InterviewSession(
            profile_id=uuid.UUID(profile_id),
            career_id=uuid.UUID(career_id) if career_id else None,
            status="CREATED",
            mode=mode,
            difficulty=difficulty,
            metadata_={
                "target_question_count": target_question_count,
                **(metadata or {}),
            },
        )
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def get_session(self, session_id: str) -> InterviewSession | None:
        result = await self.session.execute(
            select(InterviewSession).where(InterviewSession.id == uuid.UUID(session_id))
        )
        return result.scalar_one_or_none()

    async def start_session(self, session_id: str) -> InterviewSession:
        """Transition CREATED → ACTIVE."""
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        if session.status != "CREATED":
            raise ValueError(f"Cannot start session in status: {session.status}")
        session.status = "ACTIVE"
        session.started_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def pause_session(self, session_id: str) -> InterviewSession:
        """Transition ACTIVE → PAUSED."""
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        if session.status != "ACTIVE":
            raise ValueError(f"Cannot pause session in status: {session.status}")
        session.status = "PAUSED"
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def resume_session(self, session_id: str) -> InterviewSession:
        """Transition PAUSED → ACTIVE."""
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        if session.status != "PAUSED":
            raise ValueError(f"Cannot resume session in status: {session.status}")
        session.status = "ACTIVE"
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def complete_session(self, session_id: str) -> InterviewSession:
        """Transition ACTIVE → COMPLETED."""
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        if session.status not in ("ACTIVE", "PAUSED"):
            raise ValueError(f"Cannot complete session in status: {session.status}")
        session.status = "COMPLETED"
        session.completed_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def abandon_session(self, session_id: str) -> InterviewSession:
        """Transition → ABANDONED."""
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        if session.status in ("COMPLETED", "ABANDONED"):
            raise ValueError(f"Cannot abandon session in status: {session.status}")
        session.status = "ABANDONED"
        session.completed_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def validate_transition(self, from_status: str, to_status: str) -> bool:
        """Check if a transition is valid."""
        return to_status in VALID_TRANSITIONS.get(from_status, set())


# ---------------------------------------------------------------------------
# Difficulty engine
# ---------------------------------------------------------------------------

class InterviewDifficultyEngine:
    """Deterministic adaptive difficulty management."""

    # Thresholds for difficulty adjustment.
    INCREASE_THRESHOLD = 0.80
    DECREASE_THRESHOLD = 0.45
    ROLLING_WINDOW = 3

    DIFFICULTY_LEVELS = ["EASY", "MEDIUM", "HARD", "EXPERT"]
    LEVEL_INDEX = {"EASY": 0, "MEDIUM": 1, "HARD": 2, "EXPERT": 3}

    def adjust_difficulty(
        self,
        *,
        current_difficulty: str,
        recent_scores: list[float],
    ) -> str:
        """Adjust difficulty based on recent performance.

        Uses a rolling window of the last ROLLING_WINDOW scores.
        - If recent average >= INCREASE_THRESHOLD: increase difficulty
        - If recent average <= DECREASE_THRESHOLD: decrease difficulty
        - Otherwise: maintain current difficulty
        """
        if len(recent_scores) < self.ROLLING_WINDOW:
            return current_difficulty

        window = recent_scores[-self.ROLLING_WINDOW:]
        avg = sum(window) / len(window)

        current_idx = self.LEVEL_INDEX.get(current_difficulty, 1)

        if avg >= self.INCREASE_THRESHOLD:
            new_idx = min(current_idx + 1, len(self.DIFFICULTY_LEVELS) - 1)
        elif avg <= self.DECREASE_THRESHOLD:
            new_idx = max(current_idx - 1, 0)
        else:
            new_idx = current_idx

        return self.DIFFICULTY_LEVELS[new_idx]


# ---------------------------------------------------------------------------
# Adaptive question selector
# ---------------------------------------------------------------------------

class AdaptiveQuestionSelector:
    """Deterministic question selection for adaptive interviews."""

    # Weights for selection score components.
    _SKILL_NEED_WEIGHT = 0.35
    _CAREER_IMPORTANCE_WEIGHT = 0.25
    _COVERAGE_NEED_WEIGHT = 0.20
    _ADAPTATION_WEIGHT = 0.10
    _DIVERSITY_BONUS = 0.05
    _REPETITION_PENALTY = 0.50

    def select_next_question(
        self,
        *,
        candidate_questions: list[dict[str, Any]],
        skill_gaps: dict[str, float],
        skill_coverage: dict[str, int],
        asked_question_ids: set[str],
        recent_difficulty: str,
        recent_scores: list[float],
        interview_mode: str,
        asked_types: list[str],
    ) -> dict[str, Any] | None:
        """Select the next question deterministically.

        Returns the best candidate question dict, or None if no eligible
        questions remain.
        """
        if not candidate_questions:
            return None

        # Filter out already-asked questions.
        eligible = [
            q for q in candidate_questions
            if str(q.get("id")) not in asked_question_ids
        ]
        if not eligible:
            return None

        # Score each candidate.
        scored: list[tuple[float, dict[str, Any]]] = []
        for q in eligible:
            score = self._score_question(
                question=q,
                skill_gaps=skill_gaps,
                skill_coverage=skill_coverage,
                asked_types=asked_types,
                recent_difficulty=recent_difficulty,
                recent_scores=recent_scores,
            )
            scored.append((score, q))

        # Sort by score descending, then by question ID for determinism.
        scored.sort(key=lambda x: (-x[0], str(x[1].get("id", ""))))
        return scored[0][1] if scored else None

    def _score_question(
        self,
        *,
        question: dict[str, Any],
        skill_gaps: dict[str, float],
        skill_coverage: dict[str, int],
        asked_types: list[str],
        recent_difficulty: str,
        recent_scores: list[float],
    ) -> float:
        """Score a single question candidate."""
        # Skill need: how much the question's skills are needed.
        skill_names = question.get("skill_names", [])
        skill_need = 0.0
        for sn in skill_names:
            gap = skill_gaps.get(sn, 0.0)
            coverage = skill_coverage.get(sn, 0)
            # Higher need for skills with larger gaps and fewer questions.
            need = gap * (1.0 / (coverage + 1))
            skill_need += need
        if skill_names:
            skill_need /= len(skill_names)

        # Career importance: from question metadata.
        importance = question.get("career_importance", 0.5)

        # Coverage need: how many skills this question covers.
        coverage_need = len(skill_names) / 5.0  # normalize

        # Adaptation: match current difficulty.
        q_diff = question.get("difficulty", "MEDIUM")
        diff_match = 1.0 if q_diff == recent_difficulty else 0.5

        # Diversity bonus: prefer types not recently asked.
        q_type = question.get("question_type", "TECHNICAL")
        diversity = 0.0 if q_type in asked_types[-3:] else 1.0

        # Repetition penalty: check if similar skills were recently asked.
        repetition = 0.0
        if skill_names and asked_types:
            # Simple: if the same skill was asked in last 2 questions, penalize.
            pass  # Handled by asked_question_ids filter.

        score = (
            self._SKILL_NEED_WEIGHT * skill_need
            + self._CAREER_IMPORTANCE_WEIGHT * importance
            + self._COVERAGE_NEED_WEIGHT * coverage_need
            + self._ADAPTATION_WEIGHT * diff_match
            + self._DIVERSITY_BONUS * diversity
        )

        return round(score, 4)


# ---------------------------------------------------------------------------
# Interview evaluation
# ---------------------------------------------------------------------------

class InterviewEvaluationService:
    """Evaluates interview answers using LLM with structured output."""

    def __init__(self, llm_provider=None) -> None:
        from app.core.llm import FakeLLMProvider

        self.llm_provider = llm_provider or FakeLLMProvider()

    async def evaluate_answer(
        self,
        *,
        question_text: str,
        answer_text: str,
        question_type: str,
        difficulty: str,
        target_skills: list[str],
    ) -> dict[str, Any]:
        """Evaluate an answer and return structured scores.

        Returns a dict with overall_score, correctness_score, depth_score,
        clarity_score, reasoning_score, strengths, weaknesses, feedback.
        """
        from pydantic import BaseModel, ConfigDict, Field

        class EvaluationOutput(BaseModel):
            model_config = ConfigDict(frozen=True)
            overall_score: float = Field(ge=0.0, le=1.0)
            correctness_score: float = Field(ge=0.0, le=1.0)
            depth_score: float = Field(ge=0.0, le=1.0)
            clarity_score: float = Field(ge=0.0, le=1.0)
            reasoning_score: float = Field(ge=0.0, le=1.0)
            strengths: list[str] = Field(default_factory=list)
            weaknesses: list[str] = Field(default_factory=list)
            feedback: str = ""

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an interview evaluator. Evaluate the candidate's "
                    "answer to the interview question. Return a JSON object with "
                    "keys: overall_score, correctness_score, depth_score, "
                    "clarity_score, reasoning_score, strengths, weaknesses, "
                    "feedback. All scores must be between 0.0 and 1.0. "
                    "strengths and weaknesses must be arrays of strings."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question_text}\n"
                    f"Question type: {question_type}\n"
                    f"Difficulty: {difficulty}\n"
                    f"Target skills: {', '.join(target_skills)}\n"
                    f"Answer: {answer_text}"
                ),
            },
        ]

        try:
            response = await self.llm_provider.generate(
                messages, response_schema=EvaluationOutput
            )
            if response.structured_output:
                output = response.structured_output
                # Validate scores are in range.
                for key in ["overall_score", "correctness_score", "depth_score",
                            "clarity_score", "reasoning_score"]:
                    val = output.get(key, 0.0)
                    if not isinstance(val, (int, float)):
                        raise ValueError(f"Invalid score for {key}")
                    val = max(0.0, min(1.0, float(val)))
                    output[key] = val

                strengths = output.get("strengths", [])
                if not isinstance(strengths, list):
                    strengths = []
                weaknesses = output.get("weaknesses", [])
                if not isinstance(weaknesses, list):
                    weaknesses = []

                return {
                    "overall_score": output.get("overall_score", 0.0),
                    "correctness_score": output.get("correctness_score", 0.0),
                    "depth_score": output.get("depth_score", 0.0),
                    "clarity_score": output.get("clarity_score", 0.0),
                    "reasoning_score": output.get("reasoning_score", 0.0),
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "feedback": str(output.get("feedback", ""))[:2000],
                }
            else:
                raise ValueError("No structured output from LLM")
        except Exception:
            # Return a controlled failure result.
            return {
                "overall_score": 0.0,
                "correctness_score": 0.0,
                "depth_score": 0.0,
                "clarity_score": 0.0,
                "reasoning_score": 0.0,
                "strengths": [],
                "weaknesses": ["Evaluation failed — unable to assess answer"],
                "feedback": "Evaluation unavailable. Please try again.",
            }


# ---------------------------------------------------------------------------
# Skill performance aggregation
# ---------------------------------------------------------------------------

class InterviewSkillPerformanceService:
    """Deterministic skill performance aggregation from interview turns."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def update_skill_performance(
        self,
        *,
        session_id: str,
        skill_name: str,
        new_score: float,
    ) -> InterviewSkillResult:
        """Update skill performance after a new answer.

        Creates or updates the InterviewSkillResult for the skill.
        """
        result = await self.session.execute(
            select(InterviewSkillResult).where(
                InterviewSkillResult.session_id == uuid.UUID(session_id),
                InterviewSkillResult.skill_name == skill_name,
            )
        )
        skill_result = result.scalar_one_or_none()

        if skill_result is None:
            skill_result = InterviewSkillResult(
                session_id=uuid.UUID(session_id),
                skill_name=skill_name,
                questions_attempted=1,
                average_score=new_score,
                latest_score=new_score,
                trend="INSUFFICIENT_DATA",
                performance_confidence=self._calculate_confidence(1, new_score, new_score),
            )
            self.session.add(skill_result)
        else:
            old_avg = skill_result.average_score or 0.0
            old_count = skill_result.questions_attempted
            new_count = old_count + 1
            new_avg = (old_avg * old_count + new_score) / new_count

            skill_result.questions_attempted = new_count
            skill_result.average_score = new_avg
            skill_result.latest_score = new_score
            skill_result.trend = self._calculate_trend(old_avg, new_score)
            skill_result.performance_confidence = self._calculate_confidence(
                new_count, new_avg, new_score
            )

        await self.session.commit()
        await self.session.refresh(skill_result)
        return skill_result

    async def get_session_skill_results(
        self, session_id: str
    ) -> list[InterviewSkillResult]:
        """Get all skill results for a session."""
        result = await self.session.execute(
            select(InterviewSkillResult).where(
                InterviewSkillResult.session_id == uuid.UUID(session_id)
            )
        )
        return list(result.scalars().all())

    @staticmethod
    def _calculate_trend(old_avg: float, new_score: float) -> str:
        """Determine trend based on score change."""
        diff = new_score - old_avg
        if diff > 0.10:
            return "IMPROVING"
        if diff < -0.10:
            return "DECLINING"
        return "STABLE"

    @staticmethod
    def _calculate_confidence(
        count: int, avg: float, latest: float
    ) -> float:
        """Calculate performance confidence from observable factors.

        Factors:
        - Number of attempts (more = higher confidence)
        - Score consistency (lower variance = higher confidence)
        - Recency (latest score included)
        """
        attempt_factor = min(1.0, count / 5.0)
        # Simple consistency: if latest is close to average, higher confidence.
        consistency = 1.0 - min(1.0, abs(latest - avg))
        return round(0.5 * attempt_factor + 0.5 * consistency, 4)


# ---------------------------------------------------------------------------
# Interview completion
# ---------------------------------------------------------------------------

class InterviewCompletionService:
    """Deterministic interview completion logic."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def check_completion(
        self, session_id: str, target_count: int
    ) -> bool:
        """Check if the interview should be completed."""
        result = await self.session.execute(
            select(func.count(InterviewTurn.id)).where(
                InterviewTurn.session_id == uuid.UUID(session_id)
            )
        )
        count = result.scalar() or 0
        return count >= target_count

    async def generate_summary(
        self, session_id: str
    ) -> dict[str, Any]:
        """Generate a deterministic interview summary."""
        session_result = await self.session.execute(
            select(InterviewSession).where(
                InterviewSession.id == uuid.UUID(session_id)
            )
        )
        session = session_result.scalar_one_or_none()
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        turns_result = await self.session.execute(
            select(InterviewTurn).where(
                InterviewTurn.session_id == uuid.UUID(session_id)
            ).order_by(InterviewTurn.sequence_order)
        )
        turns = turns_result.scalars().all()

        skill_results = await self.session.execute(
            select(InterviewSkillResult).where(
                InterviewSkillResult.session_id == uuid.UUID(session_id)
            )
        )
        skills = skill_results.scalars().all()

        # Calculate overall score.
        scores = [t.score for t in turns if t.score is not None]
        overall = sum(scores) / len(scores) if scores else 0.0

        # Determine strengths and weaknesses.
        strengths = []
        weaknesses = []
        for sr in skills:
            if sr.average_score is not None:
                if sr.average_score >= 0.70:
                    strengths.append(sr.skill_name)
                elif sr.average_score < 0.50:
                    weaknesses.append(sr.skill_name)

        # Recommended skills to improve.
        recommended = sorted(weaknesses)

        return {
            "session_id": session_id,
            "overall_score": round(overall, 4),
            "questions_attempted": len(turns),
            "skill_performance": [
                {
                    "skill_name": sr.skill_name,
                    "questions_attempted": sr.questions_attempted,
                    "average_score": sr.average_score,
                    "latest_score": sr.latest_score,
                    "trend": sr.trend,
                    "performance_confidence": sr.performance_confidence,
                }
                for sr in skills
            ],
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommended_skills": recommended,
            "difficulty_progression": [t.difficulty for t in turns if t.difficulty],
        }


__all__ = [
    "InterviewSessionService",
    "InterviewDifficultyEngine",
    "AdaptiveQuestionSelector",
    "InterviewEvaluationService",
    "InterviewSkillPerformanceService",
    "InterviewCompletionService",
]
