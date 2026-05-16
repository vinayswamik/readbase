from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.answering.answerer import answer_question
from src.answering.retriever import index_exists, load_index, search
from src.repo_ingestion.repo_manager import RepoError, index_repo, list_indexes
from src.settings import DEFAULT_TOP_K

# Local dev bind address and where built UI assets live on disk.
HOST = "127.0.0.1"
PORT = 8000
STATIC_DIR = Path(__file__).resolve().parent / "static"

# FastAPI replaces the previous stdlib HTTP handler. The API contract stays the
# same so the TypeScript frontend does not need endpoint changes.
app = FastAPI(title="Readbase", version="0.2.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Pydantic models describe request bodies and give FastAPI automatic JSON parsing
# plus clear 422 errors when the client sends malformed data.
class IndexRequest(BaseModel):
    repo_url: str
    refresh: bool = False


class AskRequest(BaseModel):
    repo_id: str
    question: str
    top_k: int = DEFAULT_TOP_K


# Root route serves the browser UI. StaticFiles serves app.js/styles.css.
@app.get("/")
def root() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store"},
    )


# Sidebar uses this to show repositories that already have local indexes.
@app.get("/api/repos")
def repos() -> dict:
    return {"repos": list_indexes()}


# Clone/chunk/index a GitHub repository. RepoError becomes a 400 because it is
# caused by user input or git problems, not a server crash.
@app.post("/api/index")
def index_endpoint(payload: IndexRequest) -> dict:
    repo_url = payload.repo_url.strip()
    if not repo_url:
        raise HTTPException(status_code=400, detail="repo_url is required.")
    try:
        return index_repo(repo_url, refresh=payload.refresh)
    except RepoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Retrieve relevant code chunks from ChromaDB, then synthesize with Anthropic
# when configured. The response shape matches the previous server implementation.
@app.post("/api/ask")
def ask_endpoint(payload: AskRequest) -> dict:
    repo_id = payload.repo_id.strip()
    question = payload.question.strip()
    if not repo_id:
        raise HTTPException(status_code=400, detail="repo_id is required.")
    if not question:
        raise HTTPException(status_code=400, detail="question is required.")
    if not index_exists(repo_id):
        raise HTTPException(status_code=400, detail="Repository is not indexed yet.")

    index = load_index(repo_id)
    matches = search(index, question, top_k=payload.top_k)
    answer = answer_question(question, matches)
    return {
        "repo_id": repo_id,
        "question": question,
        "answer": answer["answer"],
        "mode": answer["mode"],
        "sources": answer["sources"],
    }


# CLI entry: `python server.py` starts uvicorn, the ASGI server FastAPI runs on.
def main() -> None:
    print(f"Readbase running at http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
