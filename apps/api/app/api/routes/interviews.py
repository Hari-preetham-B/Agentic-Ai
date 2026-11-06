"""Interview API routes.

Endpoints:
- POST   /interviews              — create a session
- GET    /interviews/{session_id}  — get session state
- POST   /interviews/{session_id}/start — start the session
- GET    /interviews/{session_id}/next — get next question
- POST   /interviews/{session_id}/answers — submit an answer
- POST   /interviews/{session_id}/pause — pause
- POST   /interviews/{session_id}/resume — resume
- POST   /interviews/{session_id}/complete — complete
- GET    /interviews/{session_id}/results — get results
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependency import get_current_user
from app.core.auth.ownership import (
    require_owned_interview_session,
    require_owned_profile,
)
from app.core.auth.provider import AuthenticatedUser
from app.core.database import get_session
from app.services.interview_flow_service import InterviewFlowService
from app.services.interview_service import (
    InterviewCompletionService,
    InterviewSessionService,
)

router = APIRouter(tags=["interviews"])


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class CreateInterviewSessionRequest(BaseModel):
    profile_id: str = Field(..., description="Profile ID.")
    career_id: str | None = Field(default=None)
    mode: str = Field(default="MIXED")
    difficulty: str = Field(default="MEDIUM")
    target_question_count: int = Field(default=10, ge=1, le=50)


class InterviewSessionResponse(BaseModel):
    session_id: str
    profile_id: str
    career_id: str | None = None
    status: str
    mode: str
    difficulty: str
    started_at: str | None = None
    completed_at: str | None = None


class SubmitAnswerRequest(BaseModel):
    question_id: str = Field(..., description="Question ID.")
    answer_text: str = Field(..., min_length=1, description="Answer text.")


class SubmitAnswerResponse(BaseModel):
    turn_id: str
    session_id: str
    question_id: str
    evaluation_status: str
    score: float | None = None
    feedback: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    difficulty: str | None = None
    evaluator: str | None = None
    questions_answered: int = 0
    target_question_count: int = 0
    session_complete: bool = False


class NextQuestionResponse(BaseModel):
    question_id: str | None = None
    question_text: str | None = None
    question_type: str | None = None
    difficulty: str | None = None
    target_skills: list[str] = Field(default_factory=list)
    expected_competency: str | None = None
    no_more_questions: bool = False
    questions_answered: int = 0
    target_question_count: int = 0
    reason: str | None = None


class InterviewResultsResponse(BaseModel):
    session_id: str
    overall_score: float
    questions_attempted: int
    skill_performance: list[dict] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommended_skills: list[str] = Field(default_factory=list)
    difficulty_progression: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/interviews",
    response_model=InterviewSessionResponse,
    summary="Create an interview session",
)
async def create_interview(
    request: CreateInterviewSessionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InterviewSessionResponse:
    await require_owned_profile(session, request.profile_id, current_user.user_id)
    service = InterviewSessionService(session)
    interview_session = await service.create_session(
        profile_id=request.profile_id,
        career_id=request.career_id,
        mode=request.mode,
        difficulty=request.difficulty,
        target_question_count=request.target_question_count,
    )
    return InterviewSessionResponse(
        session_id=str(interview_session.id),
        profile_id=str(interview_session.profile_id),
        career_id=str(interview_session.career_id) if interview_session.career_id else None,
        status=interview_session.status,
        mode=interview_session.mode,
        difficulty=interview_session.difficulty,
        started_at=interview_session.started_at.isoformat() if interview_session.started_at else None,
        completed_at=interview_session.completed_at.isoformat() if interview_session.completed_at else None,
    )


@router.get(
    "/interviews",
    response_model=list[InterviewSessionResponse],
    summary="List the current user's interview sessions",
)
async def list_interviews(
    profile_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[InterviewSessionResponse]:
    await require_owned_profile(session, profile_id, current_user.user_id)
    flow = InterviewFlowService(session)
    sessions = await flow.list_sessions(profile_id)
    return [
        InterviewSessionResponse(
            session_id=str(s.id),
            profile_id=str(s.profile_id),
            career_id=str(s.career_id) if s.career_id else None,
            status=s.status,
            mode=s.mode,
            difficulty=s.difficulty,
            started_at=s.started_at.isoformat() if s.started_at else None,
            completed_at=s.completed_at.isoformat() if s.completed_at else None,
        )
        for s in sessions
    ]


@router.get(
    "/interviews/{session_id}",
    response_model=InterviewSessionResponse,
    summary="Get interview session state",
)
async def get_interview(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InterviewSessionResponse:
    interview_session = await require_owned_interview_session(
        session, session_id, current_user.user_id
    )
    return InterviewSessionResponse(
        session_id=str(interview_session.id),
        profile_id=str(interview_session.profile_id),
        career_id=str(interview_session.career_id) if interview_session.career_id else None,
        status=interview_session.status,
        mode=interview_session.mode,
        difficulty=interview_session.difficulty,
        started_at=interview_session.started_at.isoformat() if interview_session.started_at else None,
        completed_at=interview_session.completed_at.isoformat() if interview_session.completed_at else None,
    )


@router.post(
    "/interviews/{session_id}/start",
    response_model=InterviewSessionResponse,
    summary="Start an interview session",
)
async def start_interview(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InterviewSessionResponse:
    await require_owned_interview_session(session, session_id, current_user.user_id)
    service = InterviewSessionService(session)
    try:
        interview_session = await service.start_session(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    return InterviewSessionResponse(
        session_id=str(interview_session.id),
        profile_id=str(interview_session.profile_id),
        career_id=str(interview_session.career_id) if interview_session.career_id else None,
        status=interview_session.status,
        mode=interview_session.mode,
        difficulty=interview_session.difficulty,
        started_at=interview_session.started_at.isoformat() if interview_session.started_at else None,
        completed_at=interview_session.completed_at.isoformat() if interview_session.completed_at else None,
    )


@router.post(
    "/interviews/{session_id}/pause",
    response_model=InterviewSessionResponse,
    summary="Pause an interview session",
)
async def pause_interview(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InterviewSessionResponse:
    await require_owned_interview_session(session, session_id, current_user.user_id)
    service = InterviewSessionService(session)
    try:
        interview_session = await service.pause_session(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    return InterviewSessionResponse(
        session_id=str(interview_session.id),
        profile_id=str(interview_session.profile_id),
        career_id=str(interview_session.career_id) if interview_session.career_id else None,
        status=interview_session.status,
        mode=interview_session.mode,
        difficulty=interview_session.difficulty,
        started_at=interview_session.started_at.isoformat() if interview_session.started_at else None,
        completed_at=interview_session.completed_at.isoformat() if interview_session.completed_at else None,
    )


@router.post(
    "/interviews/{session_id}/resume",
    response_model=InterviewSessionResponse,
    summary="Resume a paused interview session",
)
async def resume_interview(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InterviewSessionResponse:
    await require_owned_interview_session(session, session_id, current_user.user_id)
    service = InterviewSessionService(session)
    try:
        interview_session = await service.resume_session(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    return InterviewSessionResponse(
        session_id=str(interview_session.id),
        profile_id=str(interview_session.profile_id),
        career_id=str(interview_session.career_id) if interview_session.career_id else None,
        status=interview_session.status,
        mode=interview_session.mode,
        difficulty=interview_session.difficulty,
        started_at=interview_session.started_at.isoformat() if interview_session.started_at else None,
        completed_at=interview_session.completed_at.isoformat() if interview_session.completed_at else None,
    )


@router.post(
    "/interviews/{session_id}/complete",
    response_model=InterviewSessionResponse,
    summary="Complete an interview session",
)
async def complete_interview(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InterviewSessionResponse:
    await require_owned_interview_session(session, session_id, current_user.user_id)
    service = InterviewSessionService(session)
    try:
        interview_session = await service.complete_session(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    return InterviewSessionResponse(
        session_id=str(interview_session.id),
        profile_id=str(interview_session.profile_id),
        career_id=str(interview_session.career_id) if interview_session.career_id else None,
        status=interview_session.status,
        mode=interview_session.mode,
        difficulty=interview_session.difficulty,
        started_at=interview_session.started_at.isoformat() if interview_session.started_at else None,
        completed_at=interview_session.completed_at.isoformat() if interview_session.completed_at else None,
    )


@router.get(
    "/interviews/{session_id}/next",
    response_model=NextQuestionResponse,
    summary="Get the next adaptive interview question",
)
async def get_next_question(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> NextQuestionResponse:
    await require_owned_interview_session(session, session_id, current_user.user_id)
    flow = InterviewFlowService(session)
    try:
        payload = await flow.get_next_question(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    return NextQuestionResponse(**payload)


@router.post(
    "/interviews/{session_id}/answers",
    response_model=SubmitAnswerResponse,
    summary="Submit an interview answer and receive an evaluation",
)
async def submit_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> SubmitAnswerResponse:
    await require_owned_interview_session(session, session_id, current_user.user_id)
    flow = InterviewFlowService(session)
    try:
        payload = await flow.submit_answer(
            session_id=session_id,
            question_id=request.question_id,
            answer_text=request.answer_text,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    return SubmitAnswerResponse(**payload)


@router.get(
    "/interviews/{session_id}/results",
    response_model=InterviewResultsResponse,
    summary="Get interview results",
)
async def get_interview_results(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InterviewResultsResponse:
    await require_owned_interview_session(session, session_id, current_user.user_id)
    service = InterviewCompletionService(session)
    try:
        summary = await service.generate_summary(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return InterviewResultsResponse(**summary)


__all__ = ["router"]
