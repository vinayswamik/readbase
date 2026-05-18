from __future__ import annotations

from fastapi import APIRouter

from src.backend.api.routes.auth import router as auth_router
from src.backend.api.routes.indexing import router as indexing_router
from src.backend.api.routes.questions import router as questions_router
from src.backend.api.routes.repos import router as repos_router
from src.backend.api.routes.workspaces import router as workspaces_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(workspaces_router)
api_router.include_router(repos_router)
api_router.include_router(indexing_router)
api_router.include_router(questions_router)
