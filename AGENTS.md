# Agent notes

Before changing this repo, read [`docs/ENGINEERING.md`](docs/ENGINEERING.md) and follow it.

## Choosing technologies

[`docs/ENGINEERING.md`](docs/ENGINEERING.md) is the source of truth. Generic FastAPI skills, tutorials, or checklists often push SQLModel/ORMs, JWT, SPA front ends, OpenTelemetry, or a frontend build — **do not adopt those by default here**. Treat external advice as questions; keep this starter’s stack unless `ENGINEERING.md` is updated in the same change. See that file’s **Choosing technologies (agents)** and **Out of scope**.

## Must follow

- Prefer the primary path: SQLite, session/CSRF + HTMX UI, protected books JSON API (`/api/books`, `/ui/books`). Keep in-memory and Mongo demos thin and removable. While `/db-items` ships here, startup and the full test suite expect Mongo (Compose); do not treat that demo as runtime-optional.
- Auth on handlers: use Annotated aliases from `app/auth/deps.py` (`UserDep`, `EditorDep`, `AdminDep`, `HtmlUserDep`, `HtmlEditorDep`, `HtmlAdminDep`). Keep `Depends(verify_csrf)` (and similar) on router `dependencies=` when nothing is injected. App entrypoint: `[tool.fastapi] entrypoint = "app.main:app"` in `pyproject.toml`.
- **HTML-first / HTMX** — see [`docs/ENGINEERING.md`](docs/ENGINEERING.md) § UI architecture. Server owns pages and fragments. Vanilla JS islands only when needed (confirm modal, toasts, CSRF). Do **not** add Alpine, React, Vue, Svelte, SPA routing, or a frontend build step unless a concrete widget forces it and `ENGINEERING.md` is updated in the same change. Keep the Pico CSS shell; do not swap in another design system unless asked.
- HTMX is pinned to **4.0.1** (`app/web/static/js/htmx.min.js`). Use [four.htmx.org](https://four.htmx.org/docs). Do not reintroduce HTMX 2 event names (`htmx:configRequest`, `htmx:pushedIntoHistory`) or the `htmx.ajax` options `pushUrl` and `indicator`.
- Async-first on the request path. No ORM — parameterized SQL only. Pydantic for request/response schemas, not persistence.
- Match primary-path style: thin routes, SQL/helpers in `app/db/` (and `app/auth/` for users), HTML/HTMX under `app/web/`.
- URL intent: `/api` = JSON (machines), `/auth` = HTML session, `/ui` = pages + HTMX fragments. Do not invent a separate `/htmx` prefix.
- Auth direction: browser session + CSRF; API Bearer opaque tokens in SQLite; protected JSON accepts session or Bearer. Session-authenticated mutating `/api` calls require CSRF. Roles: viewer / editor / admin (`require_editor`, `require_admin`). Do not default to JWT or OAuth unless `ENGINEERING.md` says so.
- Primary domain is **books**. Demo routes stay named **items** (`/items`, `/db-items`).
- Do not introduce new architectural patterns without updating `docs/ENGINEERING.md` in the same change.
- Python deps: **uv** only (`pyproject.toml` + `uv.lock`). Do not add `requirements.txt`.
- Logging: stdlib to stdout; `LOG_LEVEL` env; JSON when `ENVIRONMENT=production`. Do not log secrets. See `docs/ENGINEERING.md` § Logging.

## Scope

Only change what the task requires. Do not “improve” demo routes (`/items`, `/db-items`) toward the primary stack unless asked.
