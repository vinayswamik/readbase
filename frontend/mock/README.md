# Frontend-only mock API

UI development runs against a local contract mock server — no Python backend required.

## Browser navigation (mock mode)

URLs sync with the screen so **Back/Forward** work:

| URL | Screen |
|-----|--------|
| `/login` | Sign-in |
| `/workspaces` | Workspace list |
| `/workspaces/ws-alpha` | Workspace view |
| `/workspaces/ws-alpha` | Workspace graph |
| `/workspaces/ws-alpha?panel=sources` | Workspace + sources modal |

## Start

```bash
cd frontend
npm run dev:ui
```

Open http://127.0.0.1:5173

- **Mock API:** http://127.0.0.1:4010
- Yellow banner confirms mock mode

## Screen-by-screen workflow

1. Pick the next screen (login → workspaces → workspace → invites → graph → connectors → chat).
2. Edit mock data in `fixtures.json` for that screen's API responses.
3. If a route is missing, add a handler in `server.mjs` (match OpenAPI paths from `../../openapi.json`).
4. Build UI until the screen feels right.
5. Implement the real backend route later; switch env to reconnect.

## Mock data

- `fixtures.json` — seed workspaces, invites, graph, repos, connector states
- Restart `npm run dev:ui` after fixture edits (in-memory store loads on boot)

## Auth & OAuth in mock mode

- **Login:** click sign-in → calls `POST /api/auth/mock-login` (no OIDC redirect)
- **Connectors:** connect buttons call `POST /api/mock/connect/:connector` then reload

## Reconnect real backend

Copy the example and restart Vite:

```bash
cp .env.development.local.example .env.development.local
```

Or set:

```
VITE_MOCK_API=false
VITE_API_PROXY_TARGET=https://127.0.0.1:8000
```

Run `READBASE_SKIP_FRONTEND_BUILD=1 python3 server.py` from the repo root.
