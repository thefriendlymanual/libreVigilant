# LibreVigilant — CIS Controls v8.1 Compliance Assessment Tool

## What It Is
A self-hosted web app for tracking compliance against CIS Controls Version 8.1.2 (March 2025).
Built with Flask + SQLite. No external dependencies beyond Flask itself.

## Purpose
Allows a team to create **Projects** as named containers for compliance work. Each project holds
assessments against the 153 CIS safeguards across 18 controls, with notes and evidence per
safeguard, scores by IG level, a prioritised risk register, and cross-assessment comparison.

The app is **single-tenant** — one instance serves one team. Multi-user is on the roadmap
(multiple accounts sharing one instance with role-based access), but there is no concept of
separate tenants or organisations. Users belong to the instance and can be members of one
or more Projects with a role per project.

## Project Structure
```
~/librevigilant/
  app.py                Flask app — routes, DB init, data loading, RBAC helpers
  cis_data.json         Static CIS Controls data (18 controls, 153 safeguards with descriptions)
  librevig.db           SQLite DB — all application data
  requirements.txt      Just: flask>=3.0
  uploads/              Evidence file uploads (named {attachment_id}{ext})
  templates/
    base.html           Shared layout + single source of truth for all design tokens
                        (surfaces, primary/secondary/tertiary, IG, status, CIS function
                        badges), navbar, theme toggle, sidebar CSS
    _sidebar.html       Project/assessment nav sidebar (included by shell pages)
    _sidebar_script.html  Sidebar JS (toggleProject, showNewAsm, showNewProject helpers)
    login.html          Auth entry point
    setup.html          One-time first-run admin account setup
    home.html           Blank canvas / project list
    assessment.html     Main assessment view (Jinja2 SSR + vanilla JS)
    risk_register.html  Project-scoped risk register page
    compare.html        Cross-assessment comparison (dual-polygon radar + delta table)
    error.html          Generic error page
  static/               (empty — all CSS/JS is inline in templates)
  docs/
    docs.md             User guide (canonical source; future /docs route will render this)
```

## How to Run

**Dev:**
```bash
python3 app.py
```
Access at http://localhost:5000 (also available on local network at port 5000).

On first run, visit `/setup` to create the admin account. No project is created at that
point — the user lands on a blank canvas and creates their first Project from the sidebar.

Set `SECRET_KEY` env var for production — without it, Flask uses a random key that invalidates
sessions on every restart:
```bash
SECRET_KEY=your-secret-here python3 app.py
```

**Production:** recommended path is Docker (`docker compose up -d`, see `Dockerfile` /
`docker-compose.yml`); alternative is Gunicorn + systemd on bare metal. Both documented in
`docs/docs.md` Section 1. `init_db()` is called at module import time (not just under
`if __name__ == "__main__"`) so it runs correctly under Gunicorn, which imports `app:app`
without executing the `__main__` block. With multiple Gunicorn workers, **always pass
`--preload`** — without it, each worker imports `app.py` independently and runs `init_db()`
concurrently, which races on the migration steps (e.g. two workers both trying to
`ALTER TABLE orgs RENAME TO projects`) and crashes. `--preload` imports the app once in the
master before forking workers, so migrations run exactly once.

## Data Model

**cis_data.json** — static, never changes:
- 18 controls, each with a list of safeguards
- Each safeguard: `id`, `asset_class`, `function`, `title`, `description`, `ig1`, `ig2`, `ig3` (booleans)
- Flat lookup index `_SG_INDEX` built at startup: `safeguard_id → {control_id, control_title, title, function, asset_class, ig1, ig2, ig3}`

**librevig.db** — tables:

**`projects`** — named containers for compliance work
- `id` (PK), `name`, `slug` (unique, URL-safe), `created_at`

**`users`** — user accounts for the instance
- `id` (PK), `email` (globally unique), `display_name`, `password_hash`
- `role`: `admin` (instance-level flag for /setup only — project roles live in `user_projects`)
- `created_at`, `last_login_at`

**`user_projects`** — membership + role per project
- `user_id` (FK), `project_id` (FK), `role`: `admin` | `editor` | `viewer`
- PRIMARY KEY (`user_id`, `project_id`)

**`assessments`** — named assessments per project
- `id` (PK), `project_id` (FK), `name`
- `lifecycle`: `draft` → `review` → `completed` (completed is read-only)
- `created_by` (FK → users), `finalised_by` (FK → users), `finalised_at`, `created_at`

**`assessment_safeguards`** — per-safeguard status within an assessment
- `id` (PK), `assessment_id` (FK), `safeguard_id` (e.g. `"1.1"`), `status`, `updated_at`, `updated_by` (FK)
- `status`: `not_assessed` | `not_implemented` | `partial` | `implemented` | `not_applicable`
- UNIQUE(`assessment_id`, `safeguard_id`)

**`notes`** — comment threads per safeguard, scoped to an assessment
- `id` (PK), `assessment_id` (FK), `safeguard_id`, `body`, `created_by` (FK), `created_at`

**`attachments`** — evidence file metadata, scoped to an assessment
- `id` (PK), `assessment_id` (FK), `safeguard_id`, `filename`, `mime_type`, `size`, `uploaded_by` (FK), `uploaded_at`

**`audit_log`** — immutable record of all changes within an assessment
- `id` (PK), `assessment_id` (FK), `user_id` (FK), `user_display` (snapshot of name at log time)
- `action`: `status_change` | `assessment_created` | `assessment_activated` | `assessment_completed` | `note_added` | `note_deleted` | `attachment_added` | `attachment_deleted`
- `safeguard_id` (nullable — null for assessment-level events), `old_value`, `new_value`, `occurred_at`

**`risk_items`** — project-scoped risk register entries
- `id` (PK), `project_id` (FK), `safeguard_id`
- UNIQUE(`project_id`, `safeguard_id`) — one live item per safeguard per project
- `status`: `open` | `closed`
- `treatment`: `accept` | `mitigate` | `transfer` | `avoid` | `remediate` (nullable)
- `owner` (free text, nullable), `target_date` (ISO date string, nullable), `notes` (free text, nullable)
- `weight` — computed at import: `ig1×3 + ig2×2 + ig3×1`; halved for `partial` status
- `created_at`, `updated_at`, `closed_at`

**`schema_migrations`** — tracks applied DB migrations
- `version` (PK), `applied_at`

## RBAC

Roles are per-project. A user can hold different roles across different projects.

| Action | admin | editor | viewer |
|---|---|---|---|
| Create / start review / complete assessments | Yes | No | No |
| Delete draft assessment | Yes | No | No |
| Create / delete project | Yes | No | No |
| Edit safeguard status, notes, attachments | Yes | Yes | No |
| View audit log | Yes | Yes | No |
| Import to risk register | Yes | Yes | No |
| Edit risk items (treatment, owner, etc.) | Yes | Yes | No |
| Close / reopen risk items | Yes | Yes | No |
| View assessment, risk register, compare | Yes | Yes | Yes |
| Export CSV (assessment + risk register) | Yes | Yes | Yes |

No self-registration — an admin creates user accounts directly (no SMTP required). Project admins can manage their project's members via `/projects/<id>/members`.

## Routes

**Auth**
- `GET /login` — login page
- `POST /login` — authenticate; set session; redirect
- `GET /logout` — clear session; redirect to login

**Bootstrap**
- `GET/POST /setup` — one-time setup; only accessible when no users exist; creates admin account only

**Root**
- `GET /` — home page with collapsible left sidebar (logged in); else redirects to `/login`

**Project Management**
- `POST /projects` — create project (any authenticated user)
- `POST /projects/<id>/delete` — delete project and all contents (admin)

**Assessment Management**
- `POST /projects/<id>/assessments` — create assessment (admin)
- `POST /projects/<id>/assessments/<id>/activate` — draft → review (admin)
- `POST /projects/<id>/assessments/<id>/finalise` — review → completed, read-only (admin)
- `POST /projects/<id>/assessments/<id>/delete` — delete draft (admin)
- `GET /projects/<id>/assessments/<id>` — full assessment accordion view (all roles)

**Assessment Data APIs** (all scoped to `assessment_id`)
- `GET /api/assessments/<id>` — all statuses + notes + attachments as JSON
- `POST /api/assessments/<id>/safeguards/<sg_id>` — update status; body `{"status": "..."}` (editor+)
- `POST /api/assessments/<id>/safeguards/<sg_id>/notes` — add note (editor+)
- `DELETE /api/assessments/<id>/notes/<note_id>` — delete note (editor+)
- `POST /api/assessments/<id>/safeguards/<sg_id>/attachments` — upload file (editor+)
- `DELETE /api/assessments/<id>/attachments/<att_id>` — delete file (editor+)
- `GET /api/attachments/<att_id>` — serve attachment file (forced download; `Content-Disposition: attachment`)
- `GET /api/assessments/<id>/export` — download CSV (all roles)
- `GET /api/assessments/<id>/audit-log?page=<n>` — paginated audit log, 25/page (editor+)

**Risk Register**
- `GET /projects/<id>/risk-register` — risk register page (all roles)
- `POST /api/projects/<id>/risk-register/import` — import gaps from an assessment; body `{"assessment_id": n}`; uses INSERT OR IGNORE so existing treatment notes are preserved (editor+)
- `POST /api/projects/<id>/risk-items/<item_id>` — update treatment/owner/target_date/notes (editor+)
- `POST /api/projects/<id>/risk-items/<item_id>/close` — mark item closed (editor+)
- `POST /api/projects/<id>/risk-items/<item_id>/reopen` — reopen closed item (editor+)
- `GET /api/projects/<id>/risk-register/export` — download risk register as CSV (all roles)
- `GET /api/projects/<id>/project-audit-log?page=<n>` — paginated risk register activity log, 25/page (editor+)

**Comparison**
- `GET /projects/<id>/compare?a=<asm_id>&b=<asm_id>` — dual-polygon radar + delta table for two assessments (all roles); renders selector UI with no params or mismatched IDs

**Project Member Management** *(project admin only)*
- `GET /projects/<id>/members` — members list + add-user form (project admin only)
- `POST /api/projects/<id>/members` — add existing user to project; body `{"user_id": n, "role": "..."}` (project admin)
- `POST /api/projects/<id>/members/<uid>/role` — change a member's role; body `{"role": "..."}` (project admin; cannot change own role)
- `POST /api/projects/<id>/members/<uid>/remove` — remove member from project (project admin; cannot remove self)

**User Management** *(admin only — instance role = admin)*
- `GET /users` — user list page (table of all users + project memberships)
- `POST /users` — create user (email, display_name, password, instance role)
- `POST /users/<uid>/edit` — change display_name / instance role
- `POST /users/<uid>/delete` — delete user (blocks self-delete; cascades user_projects)
- `POST /users/<uid>/reset-password` — admin sets new password (no SMTP)
- `POST /users/<uid>/projects` — add user to a project with a role
- `POST /users/<uid>/projects/<pid>/remove` — remove user from a project

## Key Implementation Decisions

- HTML structure is rendered **server-side** by Jinja2. JS handles interactivity only.
- Filtering in the assessment view works by toggling a `hidden` CSS class on `.sg-row` elements — no re-rendering or backend queries.
- Radar charts are custom SVG (no Chart.js or D3) — consistent with zero-dependency philosophy.
- **Comparison scoring**: `_compute_control_scores(asm_id)` mirrors the JS radar logic — `implemented=1.0`, `partial=0.5`, `not_applicable` excluded from denominator, `not_assessed`/`not_implemented=0`. Returns `{control_id: float}` per control.
- **Risk register weighting**: `ig1×3 + ig2×2 + ig3×1`; halved for `partial` status. Computed at import, stored in `weight` column.
- CSS design token system for all colours, spacing, radii — see `DESIGN_SYSTEM.md`.
- **Single-tenant**: the app does not support multiple isolated tenants.
- **Sessions**: Flask signed cookie sessions; werkzeug password hashing (bundled — no new deps).
- **Sidebar navigation**: fixed-width (260px) left sidebar lists projects + their assessments + Risk Register + Compare links per project; per-project expand/collapse state stored in `localStorage`.
- **Blank canvas on first login**: `/setup` creates only the admin account; no project is created.
- **Assessment isolation**: notes and attachments are assessment-scoped for audit integrity.
- **`assessment_id` in URL, not session** — all assessment views are bookmarkable.
- **Audit log denormalisation**: `user_display` is snapshotted at write time so the trail survives user deletion.
- **Attachment naming**: `uploads/{att_id}{ext}` — no path collision across assessments.
- **Risk register on demand**: risk item weights are computed at import and stored; the register page reads directly from `risk_items`.
- **Schema migrations**: `init_db()` tracks applied migrations in `schema_migrations`. Current migrations: `0001` (initial schema), `0002` (audit_log), `0003` (user_projects rename), `0004` (risk_items), `0005` (project_audit_log).
- **CSRF protection**: all state-changing requests require a CSRF token — forms use a hidden `_csrf` field, JS API calls use an `X-CSRF-Token` header. Token is embedded in each page via Jinja2.

## Roadmap

| Feature | Status |
|---|---|
| Auth (login/logout/setup) | ✅ Done |
| Project create/delete | ✅ Done |
| Assessment lifecycle (draft→review→completed) | ✅ Done |
| CIS accordion + status editing + notes + attachments | ✅ Done |
| SVG radar chart + IG/function/control filters | ✅ Done |
| CSV export | ✅ Done |
| Audit log panel (collapsible, paginated) | ✅ Done |
| Risk register (project-scoped, import, treatments, close/reopen, CSV export) | ✅ Done |
| Risk register: reconciliation on import (surface resolved risks for closure) | ✅ Done |
| Risk register: latest-assessment status join (current status always from newest assessment) | ✅ Done |
| Risk register: full filter/sort bar (IG, treatment, owner, current status, target date sort) | ✅ Done |
| Cross-assessment comparison (dual-polygon radar + delta table) | ✅ Done |
| User management page (admin creates/edits/deletes users, assigns roles) | ✅ Done |
| Risk register audit log (track treatment/close/reopen changes per project) | ✅ Done |
| Project member management (project admins add/remove/change role of existing users) | ✅ Done |
| UX review pass | ✅ Done — see `UX-REVIEW.md` |
| Design-system consistency fixes (dead template removed, undefined vars, centralized tokens) | ✅ Done |
| Compare legend: wrap long assessment names within the panel | ✅ Done |
| UI improvements (sidebar, responsive, a11y) — see below | ✅ Done |
| Production install guide (Gunicorn + systemd) | ✅ Done — `docs/docs.md` Option A |
| Dockerfile + Docker Compose for Docker deployment | ✅ Done — `Dockerfile`, `docker-compose.yml`, `docs/docs.md` Option B |
| Reverse proxy examples (Traefik/Caddy) for TLS in front of Docker Compose | 🔲 Todo — `docs/docs.md` Option C stubbed |
| User documentation | ✅ Done — `docs/docs.md` scaffolded, all sections written including Docker/production deployment |
| In-app help (docs served inline, linked from UI) | 🔲 Todo — defer until docs.md is finalised; route + template pattern is designed |
| GitHub icon + link to project repo in UI | 🔲 Todo |
| Self-service password reset (user resets own password from within the app) | ✅ Done |
| Create assessment from template (modal: blank vs. copy from a previous assessment in the same project, prepopulating safeguard statuses/notes; skips modal straight to blank if project has no prior assessments) | ✅ Done |
| Fix CSV export — root cause was SQLite lock contention causing Gunicorn worker timeouts (WORKER TIMEOUT in logs); fixed by adding WAL mode + busy_timeout to `get_db()` | ✅ Done |
| **[PRE-GO-LIVE]** Fix assessment/project name crash when name contains a spaced hyphen/en-dash (e.g. `"Initial Assessment – FY26 Q1"`). `POST /projects/<id>/assessments` returns 500 for names matching ` - ` or ` – ` pattern. Likely a slug-generation or regex issue in `app.py`. Also affects `POST /setup` (separate 500 on valid first submit, no auto-login) — both likely share a slug/sanitisation root cause. | 🔲 Todo |
| Fix intermittent 500s on state-changing POST routes — SQLite lock contention; fixed by `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=5000` in `get_db()` | ✅ Done |
| **[PRE-GO-LIVE]** Fix bulk risk-register reconciliation modal — never appears in practice. Root cause: `api_risk_import` (~line 1517) computes `suggested_closures` by joining against `assessment_id = :asm_id` (the just-imported source assessment), so it always returns empty because gaps are by definition non-implemented in their source. Query should instead join against the most recent *completed* assessment for the project, separate from the one being imported. Per-row "Resolved in latest" badge (line ~1323) uses the correct logic and is unaffected. | 🔲 Todo |
| **[PRE-GO-LIVE]** Fix `POST /setup` UX: redirect to home page (with the new session) on success instead of returning a 500 error page. Account is created correctly server-side but the response is an error page with no auto-login, leaving the user stranded. | 🔲 Todo |
| **[PRE-GO-LIVE]** Fix docs.md: (1) section 3 says "enter a user's email address" to add a project member — the actual UI is a user-picker dropdown, no email field exists; (2) section 7 "Follow-on Assessments" never mentions the shipped create-from-template modal; (3) reconciliation description ("modal lists resolved items for bulk closure") doesn't match current UX (per-row badge + close button). | 🔲 Todo |

### UI Improvements

Outstanding items from the UX review (`UX-REVIEW.md`). The design-system consistency
fixes are already landed; the items below are the remaining follow-ups, ordered by
priority. Sidebar work is the highest-value cluster.

**Sidebar layout** (highest priority — the nav is the spine of the app)

- ✅ **Removed broken collapse toggle.** The 52px collapsed state hid all content leaving
  an empty strip, which was worse than no collapse at all. Toggle button, CSS, and JS
  state machine have been removed; sidebar is now always fully visible at 260px.
- ✅ **Separate assessments from project tools.** Risk Register, Compare, and Members use
  the same `.asm-link` styling and indentation as actual assessments, so tools read as if
  they were assessments. Group them under a small uppercase `label-sm` sub-heading
  ("Project tools") or give them a distinct treatment, and keep "+ New assessment" with
  the assessment list.
- ✅ **Strengthen the active-nav state.** The current 30%-mix background is faint
  (especially in light mode where `--primary-container` is already pale). Add a 3px
  `--primary` left accent bar to the active link and bump the background.
- ✅ **Replace glyph icons with real SVG icons.** Replaced `■ ▲ ☉` entities and `▾ ‹ ›`
  text glyphs with inline SVGs (`aria-hidden="true"`, `stroke-width="1.5"`, `currentColor`).
- ✅ **Make "Delete project" safer.** Moved into a ⋯ context menu button on the project
  header (`.project-header-wrap`). The dropdown shows on hover/click and contains a
  danger-styled "Delete project" item. `confirm()` dialog retained as a second confirmation
  step. Dropdown closes on outside click.
- **Add project/assessment search** once a workspace accumulates enough projects that the
  flat scroll becomes unwieldy.

**Responsive** ✅ Done

- At `max-width: 768px` the shell collapses to a single column. The sidebar becomes a
  slide-in overlay drawer (fixed, z-index 150, `transform: translateX(-100%)`) toggled by
  a hamburger button in the navbar. A semi-transparent backdrop closes the drawer on tap.
  All existing sidebar JS (toggleProject, showNewAsm, etc.) is unchanged. Implemented in
  `templates/base.html`.

**Accessibility** — completed in "Accessibility: skip link, nav landmark, focus ring, reduced-motion, aria-label"

- Sidebar wrapped in `<nav aria-label="Workspace">` (replaces `<aside>`).
- Skip-to-content link (`<a href="#main-content" class="skip-link">`) added as first `<body>` child in `base.html`; all page templates (`home`, `assessment`, `risk_register`, `compare`, `members`, `users`) updated with `id="main-content"` on their `<main>` element.
- Global `:focus-visible` ring (2px solid `--surface-tint`, offset 2px) added to base styles.
- `aria-label="Select assessment to import"` added to risk-register import `<select>`.
- `@media (prefers-reduced-motion: reduce)` block added to base styles, suppressing all transitions and animations.

**Risk register horizontal scroll** ✅ Done

- Removed `overflow-y: auto` from `.rr-main` and `overflow-x: auto` from `.rr-table-wrap`.
  CSS spec forces `overflow-x` to `auto` whenever `overflow-y` is `auto`, making `.rr-main`
  a scroll container that clipped the table horizontally. Removing both lets the table overflow
  all the way to the browser, which shows its own native horizontal scrollbar at the bottom
  of the viewport. Implemented in `templates/risk_register.html`.

**Token hygiene** — completed in "Token hygiene: replace hardcoded hex values with CSS custom properties"

All previously identified hardcoded hex values replaced with CSS custom properties:
- `base.html`: `.app-nav-brand` and `.btn-nav` colours → `var(--on-surface)` / `var(--on-primary)`; `.filter-select` SVG arrow fill uses theme-aware values (`%23918F9F` base, `%2344424F` light override). (`.delete-project-btn` removed — replaced by `.project-dropdown-item.danger` which uses `var(--color-danger)`)
- `risk_register.html`: `.rr-resolved-badge` → `color-mix(in srgb, var(--color-warning) 18%, transparent)` bg + `var(--color-warning)` text.
- `assessment.html`: `.ig1/.ig2/.ig3` chip backgrounds → `color-mix(in srgb, var(--igN-color) 15%, transparent)`.
