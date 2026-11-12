# Engineering notes

Decisions for this starter. Prefer simple, robust, boring.

This file is the source of truth for architecture and conventions. When a decision or the code changes, update this document in the same change so it stays accurate for future readers (and agents). Do not refer to chat threads, option letters, or temporary debate labels.

## Goals

- Mature shape (clear modules, auth, tests, Docker) without shortcuts that fight growth.
- One primary full-stack path; optional demos stay thin and removable.
- Async-first; raw SQL (no ORM); Pydantic at the HTTP edge only.
- **HTML-first / HTMX** for the browser UI; `/api` JSON for machines. Not an SPA. HTMX is pinned to **4.0.1** in `app/web/static/js/htmx.min.js`. Teach and copy from [four.htmx.org](https://four.htmx.org/docs).

### HTMX 4

- `app.js` listens for `htmx:config:request` and writes the CSRF token on `event.detail.ctx.request.headers`. The 2.x names `htmx:configRequest` and `event.detail.headers` do not fire.
- From 4.0.1, a new trigger on an element cancels a pending `delay` or `throttle` on that same element (same as 2.x). Debounced search relies on that.
- Back and Forward refetch the URL and still send `HX-Request`. `_wants_books_partial` returns the full page when `HX-History-Restore-Request` is set, and the table fragment otherwise. `/ui/books` and `/ui/books/search` both use it.
- HTTP 4xx and 5xx responses swap into the HTMX target.
- An expired or missing session on an HTMX request must not return a normal `303` to `/auth/login`. HTMX would follow it and swap the login page into the fragment target. The `LoginRequired` handler returns `204` with `HX-Redirect: /auth/login` when `HX-Request` is set, so the whole window navigates. Full-page visits still use `303`.

### FastAPI / Starlette

FastAPI is pinned in `pyproject.toml` (`fastapi[standard]==0.162.2`). Starlette is not pinned there; it comes in as FastAPI’s dependency and is resolved in `uv.lock` (currently **1.10.0**). Starlette **1.x** is intentional — security updates land through that line. Do not force Starlette back to 0.x without a concrete break and an update to this note. Prefer FastAPI’s declared range plus the lockfile unless an override is required. From 0.162.0, omitted boolean form fields no longer become `False` by inference — declare `bool = Form(False)` for checkboxes. This app’s book `available` field uses `str | None = Form(None)` instead.

`pyproject.toml` declares `[tool.fastapi] entrypoint = "app.main:app"` so `fastapi dev` / `fastapi run`, FastAPI Cloud, and editor tooling can find the app without a path argument. Keep that entrypoint accurate when the ASGI object moves.

### Annotated auth dependencies

Handler parameters use Annotated aliases from `app/auth/deps.py`, not inline `Depends(require_…)`:

| Alias | For | Wraps |
|-------|-----|-------|
| `UserDep` | JSON `/api` | `require_user` (Bearer or session; CSRF on session mutations) |
| `EditorDep` / `AdminDep` | JSON `/api` | role gates on top of `require_user` |
| `HtmlUserDep` | HTML `/ui` | `require_user_html` (session; `LoginRequired`) |
| `HtmlEditorDep` / `HtmlAdminDep` | HTML `/ui` | role gates |

Example: `async def me(user: UserDep) -> UserPublic:`. Router-level side effects that inject nothing stay as `dependencies=[Depends(verify_csrf)]`. Add a new alias next to the underlying function when you introduce a reusable auth dependency; export it from `app/auth/__init__.py`.

## Choosing technologies (agents)

This file wins over generic FastAPI tutorials, checklists, or agent skills. Those often assume SQLModel/SQLAlchemy, JWT, SPA front ends, OpenTelemetry, or a frontend build by default. **Do not apply those defaults here.**

When picking a library or path:

1. Prefer what this repo already ships for that concern (see **Goals**, **Product shape**, **Non-negotiables**, **Out of scope**).
2. Copy primary-path style (`/api/books`, `/ui/books`, `app/auth/deps.py` aliases) rather than inventing a parallel stack.
3. Treat skill or blog advice as a checklist of questions, not a rewrite plan. Adopt a suggestion only when it fits these notes; if it conflicts, keep the starter choice and update this file only when the project deliberately changes course.
4. New architectural patterns require an update to this document in the same change.

## UI architecture (HTML-first)

Prefer boring, server-driven UI over client frameworks. Concrete HTMX usage is under **HTMX patterns in use**.

### Principles

| Principle | Meaning |
|-----------|---------|
| **Server owns the truth** | Pages and HTMX fragments are the UI. Do not grow a client-side app store or SPA router. |
| **HTML first** | First paint and list/filter/mutation flows are server-rendered HTML (Jinja + Pico). |
| **HTMX for interaction** | Search, filters, pagination, and forms use HTMX swaps. |
| **Small JS islands** | Vanilla JS only where the browser must own a bit of widget state (confirm modal, toasts, CSRF header on HTMX). Prefer one focused script (`app/web/static/js/app.js`). |
| **Progressive enhancement** | Pagination links keep usable `href`s; forms still work without JS where practical. |
| **Shareable URLs** | List/search use `hx-push-url`. |

### What not to add by default

- **No Alpine, React, Vue, Svelte, or similar** — local reactivity is not a reason. Add a client library only when a concrete widget cannot be done with HTMX + a small vanilla island, and document why in this file in the same change.
- **No SPA routing or frontend build step** — no Vite/Webpack app shell; static CSS/JS under `app/web/static/` is enough.
- **No client i18n framework** — if i18n lands, prefer server-side templates.

### Island boundary

Use an island when interaction is inherently client-side (dialog, toast DOM, attaching a request header). Prefer HTMX when the server can return the next HTML fragment. Do not move list/table/form flows into islands “for speed.”

## Product shape

| Surface | Role |
|---------|------|
| SQLite + session/CSRF + HTMX UI + protected books JSON API | Primary path — fork and grow this |
| `/items` (in-memory) | Minimal teaching CRUD — no auth, no UI |
| `/db-items` (MongoDB) | Teaching async Mongo (Motor) — no auth, no UI |

Do not add auth, HTMX, or shared abstractions to the memory/Mongo demos unless the point is to teach that idea. Keep demos thin on purpose.

**Removable means delete the demo from a fork**, not “leave the container off and the app still starts.” While `/db-items` ships in this tree, lifespan connects to MongoDB, Compose includes a Mongo service, and the full test suite expects a reachable Mongo. There is no feature flag to skip that connection. A fork that does not want Mongo deletes the `/db-items` routes, `app/utils/mongo.py`, the Motor/pymongo dependencies, the Compose Mongo service, and the related tests. Until then, the supported way to run the app and `pytest` is Docker Compose (`make upd` / `make test`), or a local Mongo that matches `MONGO_*` in `.env`. CI (`.github/workflows/docker-test.yml`) builds that Compose stack, waits for `/health`, runs `pytest` in the app container, and tears down — it does not publish an image.

The primary domain entity is **books**. Demo routes keep the thin **Item** CRUD naming (`/items`, `/db-items`) on purpose — they teach storage, not a second books product.

## Roles

Three hierarchical roles on `users.role`:

| Role | Capabilities |
|------|----------------|
| `viewer` | Read books (UI + API GET) |
| `editor` | Create / update / delete books |
| `admin` | Editor powers + `/ui/admin/users` (list users, change roles) |

Enforcement is always on the server (`UserDep` / `EditorDep` / `AdminDep` and HTML aliases). Templates hide buttons; never trust the UI alone.

The seeded demo user is an **admin** (`DEMO_USERNAME` / `DEMO_PASSWORD`).

Startup only ensures that admin when `users` is empty. Richer demo data (sample `viewer` / `editor` accounts and books) is opt-in via `python -m app.seed` / `make seed` — idempotent (skips existing usernames; inserts only missing sample book titles). Sample list is larger than the UI page size (10) so pagination is easy to exercise.

## Code style (primary path)

Write primary-path code like the SQL and web layers:

- Thin route handlers: validate → call a helper → map to the response model.
- SQL in small modules (`app/db/…`, `app/auth/users.py`) with parameterized queries.
- Schema in `app/db/schema.sql`.
- Pydantic models are request/response schemas only, not persistence objects.
- Prefer FastAPI dependencies for auth over ad-hoc checks in every handler. Use the Annotated aliases (`UserDep`, `EditorDep`, `AdminDep`, `HtmlUserDep`, …) in signatures; see **Annotated auth dependencies**.

Reference implementations: `app/routes/books.py`, `app/db/books.py`, `app/web/books_routes.py`.

The in-memory and Mongo routes may stay more verbose (logic in the handler, broad try/except). That style is for demos only — do not copy it into the primary path.

## URL layout

Path indicates the client. Do not serve HTML under `/api`, and do not issue API tokens from the HTML `/auth` routes.

| Prefix | Client | Auth | Response |
|--------|--------|------|----------|
| `/api/...` | Machines (curl, Swagger, services) | Bearer (session also allowed where useful) | JSON |
| `/auth/...` | Browsers | Session cookie + CSRF | HTML (forms, redirects) |
| `/ui/...` | Browsers and HTMX | Session + CSRF on mutations | HTML pages and fragments |
| `/items`, `/db-items` | Teaching demos | None | JSON |
| `/`, `/health`, `/docs` | Ops / docs | — | unchanged |

**Browser auth routes:** `GET/POST /auth/login`, `POST /auth/logout` — establish or clear a session. Logout is POST-only with CSRF (no GET logout). No token issuance here.

**API auth routes:** `POST /api/auth/token` (issue), `DELETE /api/auth/token` (revoke current Bearer), `GET /api/auth/me` (introspect, includes `role`).

**HTMX:** pages and partials share the `/ui/...` prefix (same router). Do not add a separate `/htmx` prefix. Use `templates/` for full pages and `templates/partials/` for fragments.

Primary mounts:

| Surface | Path |
|---------|------|
| UI list / HTMX | `/ui/books` (full page or partial via `HX-Request`) |
| Advanced search | `/ui/books/search` (filters outside swap target) |
| Staff | `/ui/admin/users` (admin only) |
| JSON API | `/api/books` (reads: login; writes: editor+; filter query params; allowlisted `ordering`) |
| Root | `/` → `/ui/books` |

Demos remain at `/items` and `/db-items`.

### Books fields and N+1

Books include scalars (`category`, `isbn`, `page_count`, `available`) and `added_by_user_id` → `users`. List/get **LEFT JOIN** users so `added_by_username` is loaded in the same query — do not resolve the adder with a per-row `get_user_by_id` (classic N+1).

`GET /api/books` accepts `ordering`. The value must be an allowlisted column, with an optional `-` prefix for descending (`title`, `-year`, `added_by`, and the other list columns, plus `created_at`). Anything else, including a missing value, sorts newest first (`-created_at`). The sort text comes from that map, never from the query string. The Pico list does not send `ordering`, so its pages stay newest first.

### HTMX patterns in use

See **UI architecture** for the HTML-first contract. Patterns below are what this starter actually ships (Pico + `app.js`). Do not add Idiomorph, `hx-boost` shells, or OOB toasts unless they land in code and this file in the same change.

- **`HX-Request` dual response** — one list route returns the full page or `partials/books_table.html`.
- **Search** — `q` on title/author/ISBN with debounce + `hx-push-url`. Keep the search/filter form **outside** the HTMX swap target so inputs are not replaced (focus stays while typing).
- **Advanced filters** — `/ui/books/search`: selects + debounced text update live; year inputs update on `change`/explicit Apply (avoid mid-typing requests). Active filter chips render inside the results partial. Delete keeps filter query params via `return_to`.
- **Pagination** — `page` / `size` query params, same dual-response + push URL; swaps only the results panel.
- **Indicator** — shared `#books-indicator` via `hx-indicator` (search, pagination, create). CSS-only spinner; HTMX toggles `.htmx-request` / opacity. Keep the indicator outside the swap target.
- **Progressive enhancement** — HTMX-enhanced navigation keeps a real `href` pointing to the same URL as `hx-get`. Forms keep meaningful `action` and `method` attributes and return usable full-page responses on ordinary submission where practical. Use actual links for navigation and buttons for actions.
- **Confirm modal** — Pico `<dialog>` + small JS (`app/web/static/js/app.js`); delete buttons use `hx-trigger="confirmed-delete"` after the user confirms (no `window.confirm`).
- **Toasts** — minimal custom CSS toasts; server sets `HX-Trigger: {"showToast": {...}}` (e.g. after delete).
- **Session expiry under HTMX** — see **HTMX 4** above. Do not “fix” this with a login fragment inside a panel.
- **Polling / heartbeats (future)** — this starter does not poll to keep a session alive. If a fork adds `hx-trigger="every …"` (or similar) for live updates, treat that traffic as background: it must not silently extend an idle session forever, and an expired session must still use `HX-Redirect` (or a full-page lock screen), never a login form swapped into a small target. Prefer short-lived tokens or an explicit “still here?” flow over a keepalive that defeats timeout.

## Production HTTP boundary

The application owns authentication and response semantics. A reverse proxy may own TLS termination, some security headers, and compression. Who owns each concern must stay explicit in the deploy notes for that environment. This section is a checklist for a shared or production deploy. It is **not** a claim that every item is wired in this repository today.

### Required for a shared deploy

- Authenticated `/ui` and `/auth` responses must not be stored in shared caches. Prefer `Cache-Control: private, no-store`.
- If a full-page or fragment route is ever cacheable, its response must vary on every request header that changes the representation. For the current HTMX 4 patterns that includes `HX-Request` and `HX-History-Restore-Request`.
- Production session cookies must be `Secure`, `HttpOnly`, and use an appropriate `SameSite` policy.
- Production startup must reject the default `SECRET_KEY` and the documented demo credentials.
- Apply HSTS, `X-Content-Type-Options`, an appropriate `Referrer-Policy`, framing restrictions, and a Content Security Policy either in FastAPI or at the reverse proxy — one documented place, not conflicting layers.
- Avoid inline event handlers where practical; any retained inline bootstrap needs an explicit CSP nonce or hash.
- Static assets need a cache-invalidation strategy before they receive long-lived cache headers. Use versioned URLs or content-hashed filenames.
- Compression may be handled by FastAPI or the reverse proxy, but do it in one documented layer rather than both.

### Status in this repository

| Concern | Today |
|---------|--------|
| Session cookie `HttpOnly` / `SameSite=lax` | Set by Starlette `SessionMiddleware` |
| Session cookie `Secure` (`https_only`) | Always `False` in `app/main.py` — not production-ready |
| Reject default `SECRET_KEY` / demo passwords when `ENVIRONMENT=production` | Not implemented (README only warns) |
| `Cache-Control: private, no-store` on authenticated HTML | Not set |
| `Vary` on HTMX request headers for dual full-page / fragment routes | Not set (acceptable while those responses stay uncacheable) |
| HSTS, CSP, `Referrer-Policy`, framing, `X-Content-Type-Options` | Not set in the app; leave to a reverse proxy until this file says otherwise |
| Versioned or content-hashed static URLs | Not implemented |
| Compression | Not configured here; prefer the reverse proxy |

When any row above is implemented in code, update this table in the same change. Prefer small slices: production `Secure` cookies and rejecting unsafe defaults first; CSP next; long-lived static caching only after URL versioning exists.

## Authentication

Teaching overview (cookies, CSRF, Bearer): [`auth.md`](auth.md).

One user store; two client mechanisms:

1. **Browsers / HTMX** — signed session cookie. Mutating HTML/HTMX requests require CSRF (`require_user_html`, `verify_csrf`). `LoginRequired` uses `303` for full pages and `HX-Redirect` for HTMX (see **HTMX 4**).
2. **Machine clients** — opaque Bearer token from `POST /api/auth/token` (username/password). Store tokens in SQLite so revocation is deleting a row. Do not default to JWT unless this document is updated to say so.
3. **Protected JSON routes** — inject `UserDep` (or `EditorDep` / `AdminDep`). Under the hood, `require_user` accepts a valid session **or** a valid Bearer token. If the client uses the **session cookie** on a mutating method (`POST`/`PUT`/`PATCH`/`DELETE`), CSRF is required (`X-CSRF-Token` header or form field). **Bearer requests skip CSRF.**
4. **Same-origin JS calling `/api`** — either send the session cookie with `credentials: "include"` **and** `X-CSRF-Token` (from the page meta tag), or use a Bearer token. Prefer Bearer for non-HTML clients; session+CSRF is fine for page scripts.
5. **Swagger `/docs`** — use HTTP Bearer for `/api` routes. Cookie login is for the UI, not the main docs Authorize flow.

In-memory and Mongo demos remain unauthenticated unless that changes deliberately.

Implemented: session + CSRF for the UI and for session-authenticated `/api` writes; `POST/DELETE /api/auth/token` + opaque tokens in `api_tokens`; `require_user` accepts Bearer or session; Swagger shows HTTP Bearer via `HTTPBearer` on API deps.

### Return URLs after POST (open redirects)

Some forms carry a “where next” value so the browser returns to the same list or page after a save (filters, pagination). Never put that value straight into `RedirectResponse` without a server check (CWE-601).

| Pattern | Where | Rule |
|---------|--------|------|
| Token → server builds URL | Books (`return_to=list\|search`, list query rebuilt server-side) | Client does not supply the redirect path |
| Relative path only | When a path is unavoidable (`safe_relative_path` in `app/web/redirects.py`) | Leading `/`, no scheme/host; strip `\`; else fallback |

Prefer the token pattern for new list flows. CodeQL may still flag helpers; dismiss with a note pointing at this section when the check is already in place.

## Logging

Stdlib `logging` to **stdout** (Docker/12-factor). No log files, Loguru, or structlog.

| Setting | Role |
|---------|------|
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`. Default `INFO`. How chatty the app is. |
| `ENVIRONMENT` | `production` → one JSON object per line (for a log shipper). Anything else → human-readable text. |
| `DEBUG` | When true, dump masked settings at startup (`log_config_values`). Independent of `LOG_LEVEL`. |

Configure once in `app/core/logging.py` (`setup_logging` from the lifespan). Use `logging.getLogger(__name__)` in modules. `LOG_LEVEL` applies to the `app` logger (and uvicorn). The root logger stays at INFO so third-party DEBUG does not flood stdout. `pymongo` / `motor` / `httpx` / `httpcore` / `urllib3` are pinned to WARNING (PyMongo otherwise logs a topology heartbeat every ~10s at DEBUG). Uvicorn access logs stay at INFO even if `LOG_LEVEL` is higher.

Do not log passwords, session cookies, Bearer tokens, or CSRF secrets. Examples: failed HTML login and failed `POST /api/auth/token` log `username=` only.

## Schema / local SQLite

`CREATE TABLE IF NOT EXISTS` does not migrate existing databases. Startup runs a small additive migrate for new `books` columns when missing; for larger shape changes, delete local `data/*.db` (and test DBs) and restart. The starter prefers recreate / tiny ALTER helpers over Alembic.

## Non-negotiables

- **Async-first** on the request path (async handlers, aiosqlite, Motor). Avoid new sync I/O in handlers. Sync `bcrypt` is an accepted exception; do not add more blocking work without noting it here.
- **No ORM** (no SQLAlchemy, SQLModel, Tortoise, etc.). SQL strings + parameters.
- **Removable demos** — `/items`, `/db-items`, and their storage helpers must stay deletable from a fork without rewriting the primary path; do not entangle them into books, session auth, or the Pico UI. Removable is not the same as runtime-optional.
- **Document new patterns here** in the same change that introduces them.

## Patterns in use (primary path)

- Lifespan for connect / schema / seed / shutdown (not deprecated `@on_event`).
- Process-wide SQLite connection via `app/db/connection.py` (simple single-process setup; not a pool).
- Repository-style helpers return dicts (or simple structures); routes map to Pydantic.
- Separate dependencies for JSON vs HTML auth: Annotated aliases `UserDep` / `EditorDep` / `AdminDep` vs `HtmlUserDep` / `HtmlEditorDep` / `HtmlAdminDep` (session + `LoginRequired`). Underlying callables remain in `app/auth/deps.py` for router `dependencies=[Depends(…)]` and tests.
- Opaque API tokens hashed (SHA-256) in `api_tokens`; plaintext returned once from `POST /api/auth/token`.
- Settings via Pydantic Settings (`app/core/config.py`).
- Stdlib logging to stdout (`app/core/logging.py`); `LOG_LEVEL` env; JSON when `ENVIRONMENT=production`.
- Shared identity helpers in `app/auth/` (passwords, users, tokens, deps). HTTP routes live in `app/routes/` (JSON) and `app/web/` (HTML).
- **uv** for Python deps: `pyproject.toml` + committed `uv.lock`; Docker installs with `uv sync --frozen`. Do not reintroduce `requirements.txt` as a second source of truth. Target CPython **3.14** (`.python-version`, `requires-python`).
- FastAPI CLI entrypoint: `[tool.fastapi] entrypoint = "app.main:app"` in `pyproject.toml`.

## Out of scope

Unless this document is updated first:

- ORMs and sync DB drivers for the primary path
- SPA frameworks, SPA routers, or a frontend build step (vanilla JS + HTMX + Pico)
- Alpine.js / React / Vue / Svelte (or similar) unless a concrete widget forces an island and this doc is updated
- HTMX out-of-band (`hx-swap-oob`) swaps, client-side i18n libraries
- OAuth2 / OIDC providers
- JWT as the default API token
- Django-style generic admin
- Loguru / structlog, log files inside the container, or a bundled log shipper
