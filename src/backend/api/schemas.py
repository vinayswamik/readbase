from __future__ import annotations

from pydantic import BaseModel

from src.backend.config.settings import DEFAULT_TOP_K


class IndexRequest(BaseModel):
    repo_url: str
    refresh: bool = False


class IndexedRepoResponse(BaseModel):
    repo_id: str
    workspace_id: str | None = None
    repo_url: str
    file_count: int
    chunk_count: int


class ReposResponse(BaseModel):
    repos: list[IndexedRepoResponse]


class AskRequest(BaseModel):
    repo_id: str
    question: str
    top_k: int = DEFAULT_TOP_K


class SourceMatchResponse(BaseModel):
    score: float
    id: str
    path: str
    start_line: int
    end_line: int
    text: str


class AskResponse(BaseModel):
    repo_id: str
    workspace_id: str | None = None
    question: str
    answer: str
    mode: str
    sources: list[SourceMatchResponse]


class AuthUserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str


class SessionResponse(BaseModel):
    authenticated: bool
    user: AuthUserResponse | None = None


class CreateWorkspaceRequest(BaseModel):
    name: str


class AddWorkspaceMemberRequest(BaseModel):
    email: str


class WorkspaceMemberResponse(BaseModel):
    email: str
    user_id: str | None = None
    added_at: str
    is_owner: bool


class WorkspaceMembersResponse(BaseModel):
    members: list[WorkspaceMemberResponse]


class WorkspaceResponse(BaseModel):
    workspace_id: str
    owner_user_id: str
    name: str
    created_at: str
    can_manage: bool


class WorkspacesResponse(BaseModel):
    workspaces: list[WorkspaceResponse]
