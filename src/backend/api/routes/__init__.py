from __future__ import annotations

from fastapi import APIRouter

from src.backend.api.routes.auth import router as auth_router
from src.backend.api.routes.bitbucket import router as bitbucket_router
from src.backend.api.routes.confluence import router as confluence_router
from src.backend.api.routes.health import router as health_router
from src.backend.api.routes.invites import router as invites_router
from src.backend.api.routes.github import router as github_router
from src.backend.api.routes.organizations import router as organizations_router
from src.backend.api.routes.gitlab import router as gitlab_router
from src.backend.api.routes.hierarchy_graph import router as hierarchy_graph_router
from src.backend.api.routes.indexing import router as indexing_router
from src.backend.api.routes.jira import router as jira_router
from src.backend.api.routes.linear import router as linear_router
from src.backend.api.routes.notion import router as notion_router
from src.backend.api.routes.notifications import router as notifications_router
from src.backend.api.routes.questions import router as questions_router
from src.backend.api.routes.repos import router as repos_router
from src.backend.api.routes.slack import router as slack_router
from src.backend.api.routes.teams import router as teams_router
from src.backend.api.routes.workspaces import router as workspaces_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(github_router)
api_router.include_router(bitbucket_router)
api_router.include_router(gitlab_router)
api_router.include_router(workspaces_router)
api_router.include_router(notifications_router)
api_router.include_router(invites_router)
api_router.include_router(organizations_router)
api_router.include_router(health_router)
api_router.include_router(hierarchy_graph_router)
api_router.include_router(jira_router)
api_router.include_router(slack_router)
api_router.include_router(teams_router)
api_router.include_router(linear_router)
api_router.include_router(confluence_router)
api_router.include_router(notion_router)
api_router.include_router(repos_router)
api_router.include_router(indexing_router)
api_router.include_router(questions_router)
