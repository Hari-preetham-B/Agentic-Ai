"""API route package."""

from app.api.routes.agent_runs import router as agent_runs_router
from app.api.routes.auth import router as auth_router
from app.api.routes.careers import router as careers_router
from app.api.routes.careertwin import router as careertwin_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.interviews import router as interviews_router
from app.api.routes.learning import router as learning_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.resume import router as resume_router

__all__ = [
    "agent_runs_router",
    "auth_router",
    "careers_router",
    "careertwin_router",
    "evidence_router",
    "interviews_router",
    "learning_router",
    "profiles_router",
    "resume_router",
]
