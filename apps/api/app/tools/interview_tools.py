"""Interview tools for agent execution.

Tools for adaptive interview operations. They use the service/repository
layer — never raw SQL or direct SQLAlchemy session manipulation.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.interview_service import (
    InterviewSessionService,
    InterviewCompletionService,
)
from app.tools import Tool


# ---------------------------------------------------------------------------
# create_interview_session tool
# ---------------------------------------------------------------------------


class CreateInterviewSessionInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="Profile ID.")
    career_id: str | None = Field(default=None)
    mode: str = Field(default="MIXED")
    difficulty: str = Field(default="MEDIUM")
    target_question_count: int = Field(default=10, ge=1, le=50)


class CreateInterviewSessionOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    profile_id: str
    career_id: str | None = None
    status: str
    mode: str
    difficulty: str


class CreateInterviewSessionTool(Tool[CreateInterviewSessionInput, CreateInterviewSessionOutput]):
    input_schema = CreateInterviewSessionInput
    output_schema = CreateInterviewSessionOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="create_interview_session",
            description="Create a new interview session.",
        )
        self._session = session

    async def _run(self, input_data: CreateInterviewSessionInput) -> dict[str, Any]:
        service = InterviewSessionService(self._session)
        session = await service.create_session(
            profile_id=input_data.profile_id,
            career_id=input_data.career_id,
            mode=input_data.mode,
            difficulty=input_data.difficulty,
            target_question_count=input_data.target_question_count,
        )
        return {
            "session_id": str(session.id),
            "profile_id": str(session.profile_id),
            "career_id": str(session.career_id) if session.career_id else None,
            "status": session.status,
            "mode": session.mode,
            "difficulty": session.difficulty,
        }


# ---------------------------------------------------------------------------
# get_interview_session tool
# ---------------------------------------------------------------------------


class GetInterviewSessionInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(..., description="Session ID.")


class GetInterviewSessionOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    profile_id: str
    career_id: str | None = None
    status: str
    mode: str
    difficulty: str
    started_at: str | None = None
    completed_at: str | None = None
    metadata: dict | None = None


class GetInterviewSessionTool(Tool[GetInterviewSessionInput, GetInterviewSessionOutput]):
    input_schema = GetInterviewSessionInput
    output_schema = GetInterviewSessionOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_interview_session",
            description="Get an interview session by ID.",
        )
        self._session = session

    async def _run(self, input_data: GetInterviewSessionInput) -> dict[str, Any]:
        service = InterviewSessionService(self._session)
        session = await service.get_session(input_data.session_id)
        if session is None:
            raise ValueError(f"Session not found: {input_data.session_id}")
        return {
            "session_id": str(session.id),
            "profile_id": str(session.profile_id),
            "career_id": str(session.career_id) if session.career_id else None,
            "status": session.status,
            "mode": session.mode,
            "difficulty": session.difficulty,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "metadata": session.metadata_,
        }


# ---------------------------------------------------------------------------
# get_next_interview_question tool
# ---------------------------------------------------------------------------


class GetNextInterviewQuestionInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(..., description="Session ID.")


class GetNextInterviewQuestionOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str | None = None
    question_text: str | None = None
    question_type: str | None = None
    difficulty: str | None = None
    target_skills: list[str] = Field(default_factory=list)
    no_more_questions: bool = False


class GetNextInterviewQuestionTool(
    Tool[GetNextInterviewQuestionInput, GetNextInterviewQuestionOutput]
):
    input_schema = GetNextInterviewQuestionInput
    output_schema = GetNextInterviewQuestionOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_next_interview_question",
            description="Get the next interview question for a session.",
        )
        self._session = session

    async def _run(self, input_data: GetNextInterviewQuestionInput) -> dict[str, Any]:
        # For now, return a placeholder indicating no more questions.
        # The full question selection logic will be implemented via the
        # AdaptiveQuestionSelector service.
        return {
            "question_id": None,
            "question_text": None,
            "question_type": None,
            "difficulty": None,
            "target_skills": [],
            "no_more_questions": True,
        }


# ---------------------------------------------------------------------------
# submit_interview_answer tool
# ---------------------------------------------------------------------------


class SubmitInterviewAnswerInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(..., description="Session ID.")
    question_id: str = Field(..., description="Question ID.")
    answer_text: str = Field(..., description="Answer text.")


class SubmitInterviewAnswerOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    turn_id: str
    session_id: str
    question_id: str
    evaluation_status: str
    score: float | None = None
    feedback: str | None = None


class SubmitInterviewAnswerTool(
    Tool[SubmitInterviewAnswerInput, SubmitInterviewAnswerOutput]
):
    input_schema = SubmitInterviewAnswerInput
    output_schema = SubmitInterviewAnswerOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="submit_interview_answer",
            description="Submit an interview answer and evaluate it.",
        )
        self._session = session

    async def _run(self, input_data: SubmitInterviewAnswerInput) -> dict[str, Any]:
        # Create a turn record.
        from app.models.interview import InterviewTurn
        from datetime import datetime, timezone

        turn = InterviewTurn(
            session_id=uuid.UUID(input_data.session_id),
            question_id=uuid.UUID(input_data.question_id),
            sequence_order=0,
            answer_text=input_data.answer_text,
            started_at=datetime.now(timezone.utc),
            submitted_at=datetime.now(timezone.utc),
            evaluation_status="PENDING",
        )
        self._session.add(turn)
        await self._session.commit()
        await self._session.refresh(turn)

        return {
            "turn_id": str(turn.id),
            "session_id": str(turn.session_id),
            "question_id": str(turn.question_id),
            "evaluation_status": turn.evaluation_status,
            "score": turn.score,
            "feedback": None,
        }


# ---------------------------------------------------------------------------
# evaluate_interview_answer tool
# ---------------------------------------------------------------------------


class EvaluateInterviewAnswerInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    turn_id: str = Field(..., description="Turn ID.")
    question_text: str = Field(..., description="Question text.")
    answer_text: str = Field(..., description="Answer text.")
    question_type: str = Field(default="TECHNICAL")
    difficulty: str = Field(default="MEDIUM")
    target_skills: list[str] = Field(default_factory=list)


class EvaluateInterviewAnswerOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    turn_id: str
    overall_score: float
    correctness_score: float
    depth_score: float
    clarity_score: float
    reasoning_score: float
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    feedback: str


class EvaluateInterviewAnswerTool(
    Tool[EvaluateInterviewAnswerInput, EvaluateInterviewAnswerOutput]
):
    input_schema = EvaluateInterviewAnswerInput
    output_schema = EvaluateInterviewAnswerOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="evaluate_interview_answer",
            description="Evaluate an interview answer using LLM.",
        )
        self._session = session

    async def _run(self, input_data: EvaluateInterviewAnswerInput) -> dict[str, Any]:
        from app.services.interview_service import InterviewEvaluationService
        from app.core.llm import FakeLLMProvider

        service = InterviewEvaluationService(llm_provider=FakeLLMProvider())
        evaluation = await service.evaluate_answer(
            question_text=input_data.question_text,
            answer_text=input_data.answer_text,
            question_type=input_data.question_type,
            difficulty=input_data.difficulty,
            target_skills=input_data.target_skills,
        )

        return {
            "turn_id": input_data.turn_id,
            **evaluation,
        }


# ---------------------------------------------------------------------------
# get_interview_results tool
# ---------------------------------------------------------------------------


class GetInterviewResultsInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(..., description="Session ID.")


class GetInterviewResultsOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    overall_score: float
    questions_attempted: int
    skill_performance: list[dict] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommended_skills: list[str] = Field(default_factory=list)
    difficulty_progression: list[str] = Field(default_factory=list)


class GetInterviewResultsTool(Tool[GetInterviewResultsInput, GetInterviewResultsOutput]):
    input_schema = GetInterviewResultsInput
    output_schema = GetInterviewResultsOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_interview_results",
            description="Get interview results and summary.",
        )
        self._session = session

    async def _run(self, input_data: GetInterviewResultsInput) -> dict[str, Any]:
        from app.services.interview_service import InterviewCompletionService

        service = InterviewCompletionService(self._session)
        summary = await service.generate_summary(input_data.session_id)
        return summary


__all__ = [
    "CreateInterviewSessionInput",
    "CreateInterviewSessionOutput",
    "CreateInterviewSessionTool",
    "GetInterviewSessionInput",
    "GetInterviewSessionOutput",
    "GetInterviewSessionTool",
    "GetNextInterviewQuestionInput",
    "GetNextInterviewQuestionOutput",
    "GetNextInterviewQuestionTool",
    "SubmitInterviewAnswerInput",
    "SubmitInterviewAnswerOutput",
    "SubmitInterviewAnswerTool",
    "EvaluateInterviewAnswerInput",
    "EvaluateInterviewAnswerOutput",
    "EvaluateInterviewAnswerTool",
    "GetInterviewResultsInput",
    "GetInterviewResultsOutput",
    "GetInterviewResultsTool",
    "build_create_interview_session_tool",
    "build_get_interview_session_tool",
    "build_get_next_interview_question_tool",
    "build_submit_interview_answer_tool",
    "build_evaluate_interview_answer_tool",
    "build_get_interview_results_tool",
]


def build_create_interview_session_tool(session: AsyncSession) -> CreateInterviewSessionTool:
    return CreateInterviewSessionTool(session)


def build_get_interview_session_tool(session: AsyncSession) -> GetInterviewSessionTool:
    return GetInterviewSessionTool(session)


def build_get_next_interview_question_tool(session: AsyncSession) -> GetNextInterviewQuestionTool:
    return GetNextInterviewQuestionTool(session)


def build_submit_interview_answer_tool(session: AsyncSession) -> SubmitInterviewAnswerTool:
    return SubmitInterviewAnswerTool(session)


def build_evaluate_interview_answer_tool(session: AsyncSession) -> EvaluateInterviewAnswerTool:
    return EvaluateInterviewAnswerTool(session)


def build_get_interview_results_tool(session: AsyncSession) -> GetInterviewResultsTool:
    return GetInterviewResultsTool(session)
