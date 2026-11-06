"""Adaptive interview flow service.

Implements the question/answer loop that sits on top of the deterministic
interview state machine:

    session state -> next question selection -> answer evaluation ->
    skill performance update -> difficulty adaptation -> completion

Question selection and difficulty progression are deterministic. Answer
evaluation uses the configured LLM provider when a real provider is available;
otherwise it falls back to a deterministic, observable-signal evaluator so the
product remains fully demonstrable without an LLM API key. The evaluator used
for each turn is recorded on the turn metadata and is never presented as an
LLM evaluation when it is not one.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import FakeLLMProvider, LLMProvider
from app.models.career import CareerSkill
from app.models.interview import (
    InterviewEvaluation,
    InterviewQuestion,
    InterviewQuestionSkill,
    InterviewSession,
    InterviewTurn,
)
from app.models.profile import Skill
from app.services.interview_service import (
    AdaptiveQuestionSelector,
    InterviewDifficultyEngine,
    InterviewEvaluationService,
    InterviewSkillPerformanceService,
)

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "it", "this", "that", "as",
    "at", "by", "from", "you", "your", "we", "they", "i", "my", "how",
    "what", "why", "when", "which", "would", "could", "should", "can",
}


def _tokens(text: str) -> list[str]:
    return [
        t for t in re.findall(r"[a-zA-Z0-9+#.]+", text.lower())
        if t and t not in _STOPWORDS
    ]


def evaluate_deterministically(
    *,
    question_text: str,
    answer_text: str,
    target_skills: list[str],
) -> dict[str, Any]:
    """Evaluate an answer from observable textual signals.

    This is a transparent fallback evaluator, not an LLM judgement. It scores
    four dimensions: coverage of the question's target skills, depth (length),
    clarity (sentence structure), and reasoning (explicit connective markers).
    """
    answer = answer_text.strip()
    answer_tokens = _tokens(answer)
    question_tokens = set(_tokens(question_text))
    word_count = len(answer_tokens)
    sentences = [s for s in re.split(r"[.!?]+", answer) if s.strip()]
    sentence_count = max(1, len(sentences))
    avg_sentence_words = word_count / sentence_count

    answer_lower = answer.lower()
    matched_skills = [
        s for s in target_skills if s and s.lower() in answer_lower
    ]
    skill_coverage = (
        len(matched_skills) / len(target_skills) if target_skills else 0.0
    )
    overlap = (
        len(set(answer_tokens) & question_tokens) / len(question_tokens)
        if question_tokens
        else 0.0
    )

    if word_count == 0:
        correctness = 0.0
        depth = 0.0
        clarity = 0.0
        reasoning = 0.0
    else:
        correctness = min(
            1.0, 0.20 + 0.55 * skill_coverage + 0.25 * min(1.0, overlap)
        )
        depth = min(1.0, 0.15 + word_count / 120.0)
        # Clear, moderately sized sentences score best.
        if avg_sentence_words <= 40:
            clarity = 0.85 if sentence_count >= 2 else 0.65
        else:
            clarity = max(0.35, 0.85 - (avg_sentence_words - 40) / 100.0)
        markers = (
            "because", "therefore", "however", "first", "then", "finally",
            "for example", "for instance", "trade-off", "tradeoff", "result",
            "which means", "so that", "in order to", "steps",
        )
        marker_hits = sum(1 for m in markers if m in answer_lower)
        numbers = 1 if re.search(r"\b\d+", answer) else 0
        reasoning = min(1.0, 0.25 + 0.12 * marker_hits + 0.15 * numbers)

    overall = (
        0.45 * correctness
        + 0.25 * depth
        + 0.15 * clarity
        + 0.15 * reasoning
    )

    strengths: list[str] = []
    weaknesses: list[str] = []
    if skill_coverage >= 0.5:
        strengths.append(
            "Mentions the relevant concepts: " + ", ".join(matched_skills[:4])
        )
    elif target_skills:
        weaknesses.append(
            "Several target concepts are not addressed: "
            + ", ".join(s for s in target_skills[:3] if s not in matched_skills)
        )
    if word_count >= 60:
        strengths.append("Provides a developed, detailed answer.")
    elif word_count < 20:
        weaknesses.append("Answer is brief; add reasoning and concrete detail.")
    if sentence_count >= 2:
        strengths.append("Structured into multiple sentences.")
    if any(m in answer_lower for m in ("because", "therefore", "trade-off")):
        strengths.append("Explains reasoning rather than only stating facts.")
    else:
        weaknesses.append("Make trade-offs and reasoning explicit.")
    if re.search(r"\b\d+", answer):
        strengths.append("Uses concrete figures or specifics.")
    if not weaknesses:
        weaknesses.append(
            "Add a concrete example from your own project experience."
        )

    feedback = (
        "Deterministic evaluation based on answer coverage, depth, clarity and "
        f"reasoning signals (score {overall:.0%}). "
        + ("Strengths: " + "; ".join(strengths[:2]) + ". " if strengths else "")
        + ("Improve: " + "; ".join(weaknesses[:2]) + "." if weaknesses else "")
    )

    return {
        "overall_score": round(overall, 4),
        "correctness_score": round(correctness, 4),
        "depth_score": round(depth, 4),
        "clarity_score": round(clarity, 4),
        "reasoning_score": round(reasoning, 4),
        "strengths": strengths[:4],
        "weaknesses": weaknesses[:4],
        "feedback": feedback,
        "evaluator": "deterministic_heuristic",
    }


class InterviewFlowService:
    """Coordinate the adaptive interview question/answer loop."""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.session = session
        self.llm_provider = llm_provider
        self.selector = AdaptiveQuestionSelector()
        self.difficulty_engine = InterviewDifficultyEngine()

    # ------------------------------------------------------------------
    # Session listing
    # ------------------------------------------------------------------

    async def list_sessions(self, profile_id: str) -> list[InterviewSession]:
        result = await self.session.execute(
            select(InterviewSession)
            .where(InterviewSession.profile_id == uuid.UUID(str(profile_id)))
            .order_by(InterviewSession.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Question selection
    # ------------------------------------------------------------------

    async def get_next_question(self, session_id: str) -> dict[str, Any]:
        interview = await self._get_session(session_id)
        if interview.status != "ACTIVE":
            raise ValueError(
                f"Session must be ACTIVE to request questions (is {interview.status})."
            )

        target_count = self._target_count(interview)
        turns = await self._turns(session_id)
        answered = [t for t in turns if t.submitted_at is not None]
        if len(answered) >= target_count:
            return {
                "question_id": None,
                "question_text": None,
                "question_type": None,
                "difficulty": None,
                "target_skills": [],
                "no_more_questions": True,
                "questions_answered": len(answered),
                "target_question_count": target_count,
            }

        # Reuse an outstanding pending question rather than skipping it.
        pending = next((t for t in turns if t.submitted_at is None), None)
        if pending is not None:
            question = await self._get_question(pending.question_id)
            if question is not None:
                return await self._question_payload(
                    question, pending, answered, target_count
                )

        questions = await self._load_question_bank(interview)
        if not questions:
            return {
                "question_id": None,
                "question_text": None,
                "question_type": None,
                "difficulty": None,
                "target_skills": [],
                "no_more_questions": True,
                "questions_answered": len(answered),
                "target_question_count": target_count,
                "reason": "The question bank is empty. Seed reference data first.",
            }

        asked_ids = {str(t.question_id) for t in turns}
        asked_types = [
            t.metadata_.get("question_type", "")
            for t in turns
            if t.metadata_
        ]
        recent_scores = [t.score for t in answered if t.score is not None]
        skill_gaps = await self._skill_gaps(interview, questions)
        coverage: dict[str, int] = {}
        for t in turns:
            for skill_name in (t.metadata_ or {}).get("skill_names", []):
                coverage[skill_name] = coverage.get(skill_name, 0) + 1

        selected = self.selector.select_next_question(
            candidate_questions=questions,
            skill_gaps=skill_gaps,
            skill_coverage=coverage,
            asked_question_ids=asked_ids,
            recent_difficulty=interview.difficulty,
            recent_scores=recent_scores,
            interview_mode=interview.mode,
            asked_types=asked_types,
        )
        if selected is None:
            return {
                "question_id": None,
                "question_text": None,
                "question_type": None,
                "difficulty": None,
                "target_skills": [],
                "no_more_questions": True,
                "questions_answered": len(answered),
                "target_question_count": target_count,
            }

        turn = InterviewTurn(
            session_id=interview.id,
            question_id=uuid.UUID(str(selected["id"])),
            sequence_order=len(turns),
            difficulty=interview.difficulty,
            evaluation_status="PENDING",
            metadata_={
                "question_type": selected.get("question_type"),
                "skill_names": selected.get("skill_names", []),
                "selection_score": selected.get("selection_score"),
            },
        )
        self.session.add(turn)
        interview.current_question_id = uuid.UUID(str(selected["id"]))
        await self.session.commit()
        await self.session.refresh(turn)

        question = await self._get_question(turn.question_id)
        if question is None:
            raise ValueError("Selected question could not be loaded.")
        return await self._question_payload(
            question, turn, answered, target_count
        )

    # ------------------------------------------------------------------
    # Answer submission and evaluation
    # ------------------------------------------------------------------

    async def submit_answer(
        self,
        *,
        session_id: str,
        question_id: str,
        answer_text: str,
    ) -> dict[str, Any]:
        interview = await self._get_session(session_id)
        if interview.status != "ACTIVE":
            raise ValueError(
                f"Session must be ACTIVE to submit answers (is {interview.status})."
            )
        if not answer_text.strip():
            raise ValueError("Answer text cannot be empty.")

        qid = uuid.UUID(str(question_id))
        question = await self._get_question(qid)
        if question is None:
            raise ValueError("Question not found.")

        turns = await self._turns(session_id)
        turn = next(
            (t for t in turns if t.question_id == qid and t.submitted_at is None),
            None,
        )
        if turn is None:
            existing = next((t for t in turns if t.question_id == qid), None)
            if existing is not None and existing.submitted_at is not None:
                raise ValueError("This question has already been answered.")
            turn = InterviewTurn(
                session_id=interview.id,
                question_id=qid,
                sequence_order=len(turns),
                difficulty=interview.difficulty,
                evaluation_status="PENDING",
                metadata_={"question_type": question.question_type},
            )
            self.session.add(turn)
            await self.session.flush()

        skill_names = [
            mapping.skill_name for mapping in question.skill_mappings
        ]
        evaluation, evaluator = await self._evaluate(
            question=question,
            answer_text=answer_text,
            skill_names=skill_names,
        )

        turn.answer_text = answer_text[:20000]
        turn.submitted_at = datetime.now(timezone.utc)
        turn.score = evaluation["overall_score"]
        turn.difficulty = interview.difficulty
        turn.evaluation_status = "COMPLETED"
        turn.metadata_ = {
            **(turn.metadata_ or {}),
            "skill_names": skill_names,
            "question_type": question.question_type,
            "evaluator": evaluator,
        }
        self.session.add(
            InterviewEvaluation(
                turn_id=turn.id,
                overall_score=evaluation["overall_score"],
                correctness_score=evaluation["correctness_score"],
                depth_score=evaluation["depth_score"],
                clarity_score=evaluation["clarity_score"],
                reasoning_score=evaluation["reasoning_score"],
                strengths=evaluation.get("strengths", []),
                weaknesses=evaluation.get("weaknesses", []),
                feedback=evaluation.get("feedback", ""),
            )
        )

        # Update per-skill performance deterministically.
        performance = InterviewSkillPerformanceService(self.session)
        for skill_name in skill_names[:3]:
            await performance.update_skill_performance(
                session_id=str(interview.id),
                skill_name=skill_name,
                new_score=evaluation["overall_score"],
            )

        # Adapt difficulty from the rolling window of answered scores.
        answered_scores = [
            t.score for t in turns if t.submitted_at is not None and t.score is not None
        ]
        answered_scores.append(evaluation["overall_score"])
        interview.difficulty = self.difficulty_engine.adjust_difficulty(
            current_difficulty=interview.difficulty,
            recent_scores=answered_scores,
        )
        interview.current_question_id = None
        target_count = self._target_count(interview)
        answered_count = len(answered_scores)

        await self.session.commit()
        await self.session.refresh(turn)

        return {
            "turn_id": str(turn.id),
            "session_id": str(interview.id),
            "question_id": str(qid),
            "evaluation_status": turn.evaluation_status,
            "score": evaluation["overall_score"],
            "feedback": evaluation.get("feedback"),
            "strengths": evaluation.get("strengths", []),
            "weaknesses": evaluation.get("weaknesses", []),
            "difficulty": interview.difficulty,
            "evaluator": evaluator,
            "questions_answered": answered_count,
            "target_question_count": target_count,
            "session_complete": answered_count >= target_count,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _get_session(self, session_id: str) -> InterviewSession:
        result = await self.session.execute(
            select(InterviewSession).where(
                InterviewSession.id == uuid.UUID(str(session_id))
            )
        )
        interview = result.scalar_one_or_none()
        if interview is None:
            raise ValueError(f"Session not found: {session_id}")
        return interview

    async def _turns(self, session_id: str) -> list[InterviewTurn]:
        result = await self.session.execute(
            select(InterviewTurn)
            .where(InterviewTurn.session_id == uuid.UUID(str(session_id)))
            .order_by(InterviewTurn.sequence_order)
        )
        return list(result.scalars().all())

    async def _get_question(
        self, question_id: uuid.UUID
    ) -> InterviewQuestion | None:
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(InterviewQuestion)
            .where(InterviewQuestion.id == question_id)
            .options(selectinload(InterviewQuestion.skill_mappings))
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _target_count(interview: InterviewSession) -> int:
        metadata = interview.metadata_ or {}
        try:
            return max(1, int(metadata.get("target_question_count", 10)))
        except (TypeError, ValueError):
            return 10

    async def _load_question_bank(
        self, interview: InterviewSession
    ) -> list[dict[str, Any]]:
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(InterviewQuestion).options(
                selectinload(InterviewQuestion.skill_mappings)
            )
        )
        questions = list(result.scalars().all())
        bank: list[dict[str, Any]] = []
        for question in questions:
            # Career-specific questions take precedence, but untied curated
            # questions remain eligible for every career.
            if (
                question.career_id is not None
                and interview.career_id is not None
                and question.career_id != interview.career_id
            ):
                continue
            skill_names = [m.skill_name for m in question.skill_mappings]
            is_career_specific = question.career_id == interview.career_id
            bank.append(
                {
                    "id": str(question.id),
                    "question_text": question.question_text,
                    "question_type": question.question_type,
                    "difficulty": question.difficulty,
                    "expected_competency": question.expected_competency,
                    "skill_names": skill_names,
                    "career_importance": 0.8 if is_career_specific else 0.5,
                }
            )
        return bank

    async def _skill_gaps(
        self,
        interview: InterviewSession,
        questions: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Return per-skill gap severity in [0, 1] for question scoring."""
        gaps: dict[str, float] = {}
        if interview.career_id is not None:
            career_result = await self.session.execute(
                select(CareerSkill).where(
                    CareerSkill.career_id == interview.career_id
                )
            )
            requirements = list(career_result.scalars().all())
            profile_result = await self.session.execute(
                select(Skill).where(Skill.profile_id == interview.profile_id)
            )
            owned = {
                s.name.strip().lower(): (s.proficiency or "BEGINNER")
                for s in profile_result.scalars().all()
            }
            level_scores = {
                "BEGINNER": 0.25,
                "INTERMEDIATE": 0.5,
                "ADVANCED": 0.75,
                "EXPERT": 1.0,
            }
            for requirement in requirements:
                key = requirement.skill_name.strip().lower()
                current = level_scores.get(owned.get(key, "BEGINNER"), 0.25)
                gaps[requirement.skill_name] = max(0.0, 1.0 - current)
        if not gaps:
            # Without a target career, treat every question skill as equally
            # relevant. This keeps selection deterministic and diversified.
            for question in questions:
                for skill_name in question.get("skill_names", []):
                    gaps.setdefault(skill_name, 0.5)
        return gaps

    async def _question_payload(
        self,
        question: InterviewQuestion,
        turn: InterviewTurn,
        answered: list[InterviewTurn],
        target_count: int,
    ) -> dict[str, Any]:
        return {
            "question_id": str(question.id),
            "question_text": question.question_text,
            "question_type": question.question_type,
            "difficulty": turn.difficulty or question.difficulty,
            "target_skills": [m.skill_name for m in question.skill_mappings],
            "expected_competency": question.expected_competency,
            "no_more_questions": False,
            "questions_answered": len(answered),
            "target_question_count": target_count,
        }

    async def _evaluate(
        self,
        *,
        question: InterviewQuestion,
        answer_text: str,
        skill_names: list[str],
    ) -> tuple[dict[str, Any], str]:
        provider = self.llm_provider
        if provider is None:
            try:
                from app.core.providers import create_llm_provider

                provider = create_llm_provider()
            except Exception:
                provider = FakeLLMProvider()

        if isinstance(provider, FakeLLMProvider) or getattr(
            provider, "provider_name", ""
        ) == "fake":
            return (
                evaluate_deterministically(
                    question_text=question.question_text,
                    answer_text=answer_text,
                    target_skills=skill_names,
                ),
                "deterministic_heuristic",
            )

        service = InterviewEvaluationService(llm_provider=provider)
        result = await service.evaluate_answer(
            question_text=question.question_text,
            answer_text=answer_text,
            question_type=question.question_type,
            difficulty=question.difficulty,
            target_skills=skill_names,
        )
        if result.get("feedback", "").startswith("Evaluation unavailable"):
            return (
                evaluate_deterministically(
                    question_text=question.question_text,
                    answer_text=answer_text,
                    target_skills=skill_names,
                ),
                "deterministic_fallback",
            )
        return result, f"llm:{getattr(provider, 'provider_name', 'unknown')}"


__all__ = ["InterviewFlowService", "evaluate_deterministically"]
