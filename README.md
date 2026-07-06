<p align="center">
  <img src="frontend/src/assets/readbase-logo.svg" alt="Readbase logo" width="120" />
</p>

<h1 align="center">Readbase</h1>

Readbase is a workspace-centric knowledge assistant that indexes your code
repositories and connected SaaS tools so teams can ask questions and get
grounded answers backed by their own source material.

## Overview

Readbase connects to the systems your team already works in — GitHub, GitLab,
Bitbucket, Jira, Linear, Confluence, Notion, and Slack — indexes the content
into a vector store, and exposes a chat experience that grounds every answer
in retrieved context.

- **Workspace-scoped**: each workspace holds its own repos, connectors, members, and chat history.
- **Retrieval-augmented answers**: source files and connector content are chunked, embedded, and retrieved at query time.
- **Multiple connectors**: bring docs, issues, and discussions from across your toolchain into one index.
- **CLI and web**: drive Readbase from the browser UI or script it from the command line.

## Architecture

| Layer    | Stack                                                        |
|----------|--------------------------------------------------------------|
| Backend  | Python, FastAPI, SQLAlchemy, Alembic, ChromaDB, Uvicorn      |
| Frontend | React 19, TypeScript, Vite                                   |
| Database | PostgreSQL (via `psycopg`) or SQLite for local development   |
| Auth     | OIDC single sign-on, sessions, CSRF protection, rate limiting|

The backend follows a layered structure under `src/backend/`:

- `api/` — FastAPI routes and request/response schemas
- `application/services/` — business logic, connectors, auth, and sync schedulers
- `infrastructure/` — database models, storage, and the answer/retrieval pipeline
- `config/` — environment loading and application settings

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 20+ with npm
- PostgreSQL (or use the default SQLite for local development)

### Install dependencies

```bash
pip install -r requirements.txt
cd frontend && npm install
```

### Configure

Readbase reads a `.env` file at the project root on startup. Common variables:

| Variable                   | Description                                              |
|----------------------------|----------------------------------------------------------|
| `DATABASE_URL`             | SQLAlchemy database URL (defaults to local SQLite)       |
| `READBASE_DATA_DIR`        | Where indexes, repos, and Chroma data live              |
| `READBASE_DEPLOYMENT_MODE` | `saas` (default) or `customer`                           |
| `READBASE_SSL_CERTFILE`    | Optional path to a TLS cert for HTTPS                    |
| `READBASE_SSL_KEYFILE`     | Optional path to a TLS key for HTTPS                     |

### Run

From the project root:

```bash
python3 server.py
```

This builds the frontend and starts the FastAPI app at `http://127.0.0.1:8000`.

## CLI

The CLI (`src/cli.py`) offers quick indexing and Q&A without the UI:

```bash
# Index a GitHub repo or local directory
python3 -m src.cli index <github-url-or-path>

# Start an interactive Q&A session against an indexed repo
python3 -m src.cli ask

# Manage workspaces
python3 -m src.cli create <name>
python3 -m src.cli space <name> -del
```

## Testing

```bash
python3 -m pytest
```

## Project structure

```
readbase/
├── server.py                 # FastAPI app + frontend build entrypoint
├── src/
│   ├── cli.py                # Command-line interface
│   └── backend/
│       ├── api/              # Routes, schemas, security middleware
│       ├── application/      # Services, connectors, auth
│       ├── infrastructure/   # Database, storage, retrieval/generation
│       └── config/           # Settings and environment loading
├── alembic/                  # Database migrations
├── frontend/                 # React + Vite SPA
├── tests/                    # Test suite
└── requirements.txt
```

## License

Proprietary. All rights reserved.
