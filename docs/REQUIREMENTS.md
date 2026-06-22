# Readbase — Functional & Non-Functional Requirements

How to read this document:

- **Functional requirements (FR)** — what the system must *do* (features and behavior).
- **Non-functional requirements (NFR)** — how well it must do it (security, performance, deployment, etc.).

Status labels:

- **Now** — largely implemented in the codebase today.
- **Target** — agreed direction from product/architecture discussions; may not be built yet.

---

## Core principles

These rules tie functional and non-functional requirements together:

1. **Store once at org level** — one indexed copy per source, not per user.
2. **Gate at read** — permissions enforced at retrieval time, not by duplicating data per user.
3. **User OAuth still required** — for listing objects, syncing, and live permission checks.
4. **Customer owns infra in enterprise** — Readbase Inc ships software updates only; no customer data on Readbase servers.
5. **Workspace is the action center** — connect, subscribe, sync, and ask happen in workspace context.
6. **No admin for lifecycle** — when no users are subscribed to a source, archive/purge runs automatically.

---

# Functional requirements

## 1. Access & identity

| ID | Requirement | Status |
|----|-------------|--------|
| FR-A1 | User signs in to Readbase via web browser | Now |
| FR-A2 | Session persists across visits (login / logout) | Now |
| FR-A3 | Enterprise install uses company SSO (work email via OIDC / Entra / Okta) | Target |
| FR-A4 | SaaS uses Readbase-hosted login | Now / Target |
| FR-A5 | App login is separate from connector login | Now |
| FR-A6 | Any member can create or join a workspace (invite code / email) | Now |

## 2. Organization & deployment mode

| ID | Requirement | Status |
|----|-------------|--------|
| FR-O1 | **Enterprise (IaaS):** full app runs on customer infra; data never sent to Readbase Inc | Target |
| FR-O2 | **SaaS:** hosted at `www.readbase.com` for cloud users | Target |
| FR-O3 | **Enterprise URL:** e.g. `www.readbase.{company}.com` on customer DNS | Target |
| FR-O4 | Org has configurable storage root (local disk or S3) | Now |
| FR-O5 | Workspaces belong to an org | Now (partial) |
| FR-O6 | Software updates from Readbase Inc only; no data phone-home | Target |

## 3. Workspaces & collaboration

| ID | Requirement | Status |
|----|-------------|--------|
| FR-W1 | User creates a named workspace | Now |
| FR-W2 | User joins workspace via invite code or email invite | Now |
| FR-W3 | Workspace has owner, members, roles (e.g. connector manager) | Now |
| FR-W4 | User can belong to multiple workspaces | Now |
| FR-W5 | Workspace is the main place to add sources and ask questions | Now |

## 4. Connectors & account linking

| ID | Requirement | Status |
|----|-------------|--------|
| FR-C1 | Support connectors: GitHub, GitLab, Bitbucket, Jira, Slack, Notion, Linear, Confluence, Teams | Now |
| FR-C2 | User links external account via OAuth (per provider) | Now |
| FR-C3 | Connector OAuth uses org-registered app (client ID/secret on their install) | Now |
| FR-C4 | User can disconnect connector; optional removal of synced data | Now |
| FR-C5 | Connect flow in workspace: one pass (link account → pick objects) | Target |
| FR-C6 | Home page focuses on workspaces, not required account linking step | Target |
| FR-C7 | User settings page to manage linked accounts | Target |

## 5. Sources, ingestion & deduplication

| ID | Requirement | Status |
|----|-------------|--------|
| FR-S1 | User selects concrete sources in workspace (repo, Slack channel, Jira project, Notion DB, etc.) | Now |
| FR-S2 | System syncs source content on schedule or on demand | Now |
| FR-S3 | **One copy of each source at org level** (not per user) | Target |
| FR-S4 | First user to enable a source triggers ingestion | Target (partial: `sync_owner_user_id`) |
| FR-S5 | Later users subscribe to existing source — no re-ingest | Target |
| FR-S6 | Ingestion uses a connected user's token who has access to that source | Now |
| FR-S7 | When no user is subscribed to a source, system archives/purges automatically | Target |
| FR-S8 | Normalize provider data into searchable text (e.g. Notion blocks → text) | Now |
| FR-S9 | Index content into vector store (Chroma) per workspace/org | Now |

## 6. Permissions & retrieval

| ID | Requirement | Status |
|----|-------------|--------|
| FR-P1 | Permission enforced at retrieval, not by duplicating data per user | Now |
| FR-P2 | Search returns candidates from index, then filters by live provider permission check | Now |
| FR-P3 | User only sees results they are allowed to see in Slack/Jira/Notion/etc. | Now |
| FR-P4 | Visibility/access caches to limit repeated permission API calls | Now |
| FR-P5 | User without linked account cannot pass retrieval filter for that provider's content | Now |

## 7. Q&A & search

| ID | Requirement | Status |
|----|-------------|--------|
| FR-Q1 | User asks natural-language questions in workspace context | Now |
| FR-Q2 | System retrieves relevant chunks from repos + connector indexes | Now |
| FR-Q3 | Answers include citations / evidence snippets | Now |
| FR-Q4 | Optional LLM synthesis when API key configured | Now |
| FR-Q5 | Retrieval-only mode when no LLM configured | Now |

## 8. Code repositories

| ID | Requirement | Status |
|----|-------------|--------|
| FR-R1 | Index GitHub / GitLab / Bitbucket repos (URL or connected account) | Now |
| FR-R2 | Clone, chunk, and index source files | Now |
| FR-R3 | Repo access checked per user at retrieval | Now |

## 9. Graph & navigation (workspace)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-G1 | Hierarchy graph of sources/nodes in workspace | Now |
| FR-G2 | Users create/edit graph nodes and connections (with permissions) | Now |
| FR-G3 | Graph visibility respects user permissions | Now |

## 10. Invites & membership

| ID | Requirement | Status |
|----|-------------|--------|
| FR-I1 | Workspace owner/admin manages members | Now |
| FR-I2 | Email invites and join codes | Now |
| FR-I3 | Pending invites resolve when user signs in with matching email | Now |

## 11. Operations (in-app)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-OP1 | Manual sync trigger per source | Now |
| FR-OP2 | Sync status and errors visible in UI | Now |
| FR-OP3 | Health / storage check endpoint | Now |
| FR-OP4 | CLI for local index/ask (dev / power users) | Now |

---

# Non-functional requirements

## Security

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-S1 | Connector tokens encrypted at rest | Now |
| NFR-S2 | Session cookies HTTP-only; secure flag in production | Now |
| NFR-S3 | OAuth state parameter prevents CSRF on callbacks | Now |
| NFR-S4 | Enterprise: all credentials and indexed data stay in customer environment | Target |
| NFR-S5 | Minimal OAuth scopes per connector | Now |
| NFR-S6 | Automatic token refresh before expiry | Partial |
| NFR-S7 | Audit log: connect, disconnect, source enable, admin actions | Target |
| NFR-S8 | No secrets in logs or API responses | Now |

## Privacy & data sovereignty

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-D1 | Customer controls data location (region, disk, S3 bucket) | Target |
| NFR-D2 | Disconnect + optional data removal for user-owned sync data | Now |
| NFR-D3 | Auto purge when source has zero subscribers | Target |
| NFR-D4 | SaaS and enterprise are deploy modes of same core, not forked products | Target |

## Reliability & availability

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-R1 | Background sync schedulers per connector | Now |
| NFR-R2 | Sync failover if primary sync owner token invalid | Now |
| NFR-R3 | Graceful degradation: clear “reconnect” when token dead | Partial |
| NFR-R4 | Idempotent sync (upsert by content hash / item id) | Now |
| NFR-R5 | Enterprise: customer owns uptime SLA (self-hosted) | By design |
| NFR-R6 | Database migrations on upgrade | Now |

## Scalability & performance

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-P1 | Org-level dedup reduces storage and sync load | Target |
| NFR-P2 | Incremental sync where provider supports it | Partial |
| NFR-P3 | Visibility cache TTL to limit permission API calls | Now |
| NFR-P4 | Vector search bounded (`top_k`) per question | Now |
| NFR-P5 | Horizontal scaling path for enterprise (stateless API + shared Postgres/Chroma) | Target |

## Usability

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-U1 | Web UI — no desktop install for end users | Now |
| NFR-U2 | Minimal steps: workspace → connect → pick source → ask | Target |
| NFR-U3 | Clear errors when OAuth not configured or session expired | Now |
| NFR-U4 | Enterprise IT setup in ~half day (Docker, SSO, DB, URL) | Target |

## Maintainability & extensibility

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-M1 | Single generic OAuth module vs duplicate per-connector auth files | Target |
| NFR-M2 | Provider config (scopes, URLs) data-driven | Target |
| NFR-M3 | Clear layers: API → services → infrastructure | Now |
| NFR-M4 | New connector addable without rewriting permission model | Target |

## Deployability (IaaS-first)

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-DE1 | Config via env / config file, not code changes | Now (partial) |
| NFR-DE2 | `READBASE_DEPLOYMENT_MODE=customer` vs `saas` | Now |
| NFR-DE3 | Docker Compose (or Helm) single-package install | Target |
| NFR-DE4 | ~15 required env vars for enterprise; rest optional | Target |
| NFR-DE5 | Connectors enabled on demand, not all nine at install | Target |

## Compliance & enterprise readiness

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-C1 | SSO (OIDC / SAML) for enterprise | Target (OIDC first) |
| NFR-C2 | Customer-owned OAuth apps for connectors | Now |
| NFR-C3 | Data retention / purge policies automated | Target |
| NFR-C4 | Optional air-gapped install (no outbound except providers + updates) | Target |

---

# Implementation priority

| Phase | Functional focus | Non-functional focus |
|-------|------------------|----------------------|
| **P0 — Foundation** | FR-A6, FR-W*, FR-P*, FR-Q*, FR-S8–9 | NFR-S1–3, NFR-M3, NFR-DE2 |
| **P1 — Enterprise shape** | FR-A3, FR-O*, FR-C5–7, FR-S3–5, FR-S7 | NFR-D*, NFR-DE3–5, NFR-U2, NFR-U4 |
| **P2 — Scale & polish** | FR-G*, connector parity | NFR-S6–7, NFR-P*, NFR-C* |

---

# Open decisions

1. **Org vs workspace for source registry** — one org catalog with workspaces as views, or workspace-scoped sources only?
2. **Subscriber model** — explicit user↔source subscription table, or implicit via workspace membership?
3. **SaaS multi-tenant** — many orgs on one install, or one org per SaaS shard?
4. **Connector manager role** — keep restricted role, or any member can add sources?
5. **Archive vs purge** — retention windows and whether archive is reversible.
