"""
V1 API Router Aggregator.
"""

# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from backend.api.v1.endpoints.resume import router as resume_router
from backend.api.v1.endpoints.candidate import router as candidate_router
from backend.api.v1.endpoints.interview import router as interview_router
from backend.api.v1.endpoints.analytics import router as analytics_router
from backend.api.v1.endpoints.transfer_coaching import router as transfer_coaching_router
from backend.api.v1.endpoints.experiments import router as experiments_router
from backend.api.v1.endpoints.research import router as research_router
from backend.api.v1.endpoints.roadmap import router as roadmap_router
from backend.api.v1.endpoints.chat import router as chat_router
from backend.api.v1.endpoints.auth import router as auth_router
from backend.api.v1.endpoints.roles import router as roles_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(roles_router)
api_router.include_router(candidate_router)
api_router.include_router(resume_router)
api_router.include_router(interview_router)
api_router.include_router(analytics_router)
api_router.include_router(transfer_coaching_router)
api_router.include_router(experiments_router)
api_router.include_router(research_router)
api_router.include_router(roadmap_router)
api_router.include_router(chat_router)

