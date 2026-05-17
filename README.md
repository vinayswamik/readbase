# Readbase

Readbase is a small codebase Q&A prototype. Paste a GitHub repository URL, let the app clone and index it locally, then ask questions against retrieved code snippets instead of sending an entire repository to an LLM.

## What This First Step Includes

- GitHub repo cloning with `git clone --depth 1`
- Source-file discovery with common generated/vendor folders skipped
- Line-based chunking for code and documentation
- FastAPI backend served by uvicorn
- ChromaDB-backed local retrieval stored in `.readbase/chroma`
- Optional LLM synthesis via `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`
- React + TypeScript browser UI for indexing a repo and asking questions
- Clear UI -> API routes -> backend services -> storage/provider boundaries

## Architecture

```text
React UI / local CLI
    |
    v
API routes and adapters
src/backend/api/*
    |
    v
Backend services
src/backend/application/services/*
    |
    v
Storage and provider logic
src/backend/infrastructure/*
.readbase/ or READBASE_DATA_DIR
Anthropic API
```

- `frontend/` contains frontend-only code and talks to `/api/*`.
- `server.py` assembles the FastAPI app and serves the built frontend.
- `src/backend/api/` owns HTTP request/response schemas and route handlers.
- `src/backend/application/services/` owns use cases shared by API routes and CLI.
- `src/backend/infrastructure/ingestion/` owns repository cloning, file discovery, and chunking.
- `src/backend/infrastructure/retrieval/` owns ChromaDB indexing and search.
- `src/backend/infrastructure/generation/` owns answer generation and LLM provider calls.
- `src/backend/config/` owns runtime paths and tunable settings.

## Source Map

```text
src/
  backend/
    api/                       FastAPI schemas, error mapping, route controllers
    application/
      services/                Use-case layer shared by API routes and CLI
    infrastructure/
      ingestion/               Git clone, source file filtering, chunk creation
      retrieval/               ChromaDB persistence, embedding, search
      generation/              Retrieval-only answers and Anthropic synthesis
    config/                    Environment loading, storage paths, constants
  cli.py                       Local command-line adapter
```

## Setup

```bash
python3 -m venv .venv
pip install -r requirements.txt
pip install -e .
```

## Run

```bash
cd frontend
npm install
npm run build
cd ..
python server.py
```

Then open `http://127.0.0.1:8000`.

## CLI

1) Index a repository from GitHub URL or local path:

```bash
readbase index "<github-url / local-path>"
```

2) Start CLI Q&A:

```bash
readbase ask
```

- `readbase ask` shows available indexes, asks you to choose one by number, then opens a question loop.
- Exit Q&A with `exit` or `quit`.
- Optional: `readbase ask --repo-id <repo_id>`.

## Test

```bash
python -m unittest discover -s tests
```

## Frontend

The frontend is a self-contained Vite React + TypeScript app under `frontend/`.
The Python server serves the production build from `frontend/dist`.

```bash
cd frontend
npm install
npm run build
```

## Optional LLM Answers

Create a `.env` file:

```bash
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_MODEL=your_model_name
READBASE_DATA_DIR=.readbase
```

If either Anthropic value is missing, the app still works in retrieval-only mode and returns the most relevant snippets with citations.

## Next Small Steps

1. Add incremental indexing for repo updates.
2. Add hybrid retrieval that combines Chroma semantic search with exact symbol/path matches.
3. Add branch selection and private repo support.
4. Add answer quality evaluation on known codebase questions.
