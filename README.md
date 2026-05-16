# Readbase

Readbase is a small codebase Q&A prototype. Paste a GitHub repository URL, let the app clone and index it locally, then ask questions against retrieved code snippets instead of sending an entire repository to an LLM.

## What This First Step Includes

- GitHub repo cloning with `git clone --depth 1`
- Source-file discovery with common generated/vendor folders skipped
- Line-based chunking for code and documentation
- FastAPI backend served by uvicorn
- ChromaDB-backed local retrieval stored in `.readbase/chroma`
- Optional LLM synthesis via `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`
- A simple browser UI for indexing a repo and asking questions

## Setup

```bash
python3 -m venv .venv
pip install -r requirements.txt
pip install -e .
```

## Run

```bash
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

The browser source lives in `frontend/app.ts`. The Python server serves the compiled file at `static/app.js`.

```bash
npm install
npm run build:frontend
```

## Optional LLM Answers

Create a `.env` file:

```bash
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_MODEL=your_model_name
```

If either value is missing, the app still works in retrieval-only mode and returns the most relevant snippets with citations.

## Next Small Steps

1. Add incremental indexing for repo updates.
2. Add hybrid retrieval that combines Chroma semantic search with exact symbol/path matches.
3. Add branch selection and private repo support.
4. Add answer quality evaluation on known codebase questions.
