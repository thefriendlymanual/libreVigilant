# LibreVigilant — CIS Controls v8.1 Compliance Assessment Tool

## What It Is
A self-hosted web app for tracking compliance against CIS Controls Version 8.1.2 (March 2025).
Built with Flask + SQLite. No external dependencies beyond Flask itself.

## Purpose
Allows organisations to run named compliance assessments against the 153 CIS safeguards across
18 controls, track notes and evidence per safeguard, view scores by IG level, generate a
prioritised risk register, and compare improvements across assessments. Multiple organisations
and users are supported with role-based access control.

## Project Structure
```
~/librevigilant/
  app.py                Flask app — routes, DB init, data loading, RBAC helpers
  cis_data.json         Static CIS Controls data (18 controls, 153 safeguards with descriptions)
  librevig.db           SQLite DB — all application data
  requirements.txt      Just: flask>=3.0
  uploads/              Evidence file uploads (named {attachment_id}{ext})
  templates/
    base.html           Shared layout (CSS tokens, navbar, theme toggle)
    login.html          Auth entry point
    setup.html          One-time first-run org + admin setup
    assessments.html    Per-org assessment list/manager
    assessment.html     Main assessment view (Jinja2 SSR + vanilla JS)
    users.html          User management (org_admin only)
  static/               (empty — all CSS/JS is inline in templates)
```

## How to Run
```bash
python3 app.py
```
Access at http://localhost:5000 (also available on local network at port 5000).

On first run with no existing data, visit `/setup` to create the first organisation and admin account.

Set `SECRET_KEY` env var for production — without it, Flask uses a random key that invalidates
sessions on every restart:
```bash
SECRET_KEY=your-secret-here python3 app.py
```

Flask was installed with:
```bash
python3 /tmp/get-pip.py --user --break-system-packages
~/.local/bin/pip install flask --user --break-system-packages
```

## Data Model

**cis_data.json** — static, never changes:
- 18 controls, each with a list of safeguards
- Each safeguard: `id`, `asset_class`, `function`, `title`, `description`, `ig1`, `ig2`, `ig3` (booleans)

**librevig.db** — 7 tables:

**`orgs`** — organisations
- `id` (PK), `name`, `slug` (unique, URL-safe), `created_at`

**`users`** — user accounts, scoped to one org
- `id` (PK), `org_id` (FK), `email` (globally unique), `display_name`, `password_hash`
- `role`: `org_admin` | `editor` | `viewer`
- `created_at`, `last_login_at`

**`assessments`** — named assessments per org
- `id` (PK), `org_id` (FK), `name`
- `lifecycle`: `draft` → `active` → `finalised` (finalised is read-only)
- `start_date`, `end_date` (ISO date strings, nullable)
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
- `action`: `status_change` | `assessment_created` | `assessment_activated` | `assessment_finalised` | `note_added` | `note_deleted` | `attachment_added` | `attachment_deleted`
- `safeguard_id` (nullable — null for assessment-level events), `old_value`, `new_value`, `occurred_at`

**`schema_migrations`** — tracks applied DB migrations
- `version` (PK), `applied_at`

## RBAC

| Action | org_admin | editor | viewer |
|---|---|---|---|
| Manage users | Yes | No | No |
| Create / activate / finalise assessments | Yes | No | No |
| Delete draft assessment | Yes | No | No |
| Edit safeguard status, notes, attachments | Yes | Yes | No |
| View audit log | Yes | Yes | No |
| View assessment (read) | Yes | Yes | Yes |
| Export CSV | Yes | Yes | Yes |
| View risk register | Yes | Yes | Yes |

No self-registration — org_admin creates user accounts directly (no SMTP required).

## API Routes

**Auth**
- `GET /login` — login page
- `POST /login` — authenticate; set session; redirect
- `GET /logout` — clear session; redirect to login

**Bootstrap**
- `GET/POST /setup` — one-time setup; only accessible when no orgs exist

**Root**
- `GET /` — home page with collapsible left sidebar (logged in); else redirects to `/login`

**Org Management**
- `POST /orgs` — create org (any authenticated user can create their own org)
- `GET /orgs/<id>` — redirects to home with that org's sidebar section expanded

**Assessment Management**
- `POST /orgs/<id>/assessments` — create assessment (org_admin)
- `POST /orgs/<id>/assessments/<id>/activate` — draft → active (org_admin)
- `POST /orgs/<id>/assessments/<id>/finalise` — active → finalised, read-only (org_admin)
- `POST /orgs/<id>/assessments/<id>/delete` — delete draft (org_admin)
- `GET /orgs/<id>/assessments/<id>` — full assessment accordion view (all roles)

**Assessment Data APIs** (all scoped to `assessment_id`)
- `GET /api/assessments/<id>` — all statuses + notes + attachments
- `POST /api/assessments/<id>/safeguards/<sg_id>` — update status (editor+)
- `POST /api/assessments/<id>/safeguards/<sg_id>/notes` — add note (editor+)
- `DELETE /api/assessments/<id>/notes/<note_id>` — delete note (editor+)
- `POST /api/assessments/<id>/safeguards/<sg_id>/attachments` — upload file (editor+)
- `DELETE /api/assessments/<id>/attachments/<att_id>` — delete file (editor+)
- `GET /api/attachments/<att_id>` — serve attachment file
- `GET /api/assessments/<id>/export` — download CSV (all roles)
- `GET /api/assessments/<id>/audit-log` — paginated audit log (editor+)
- `GET /api/assessments/<id>/risk-register` — computed risk register JSON (all roles)
- `GET /api/orgs/<id>/compare?a=<id>&b=<id>` — cross-assessment score delta (all roles)

**User Management** (org_admin only)
- `GET /orgs/<id>/users` — user list page
- `POST /orgs/<id>/users` — create user
- `POST /orgs/<id>/users/<uid>/edit` — change role / display_name
- `POST /orgs/<id>/users/<uid>/delete` — delete user
- `GET/POST /orgs/<id>/users/<uid>/reset-password` — set new password

## UI Features

**Existing (current)**
- Dashboard: IG1/IG2/IG3 stat cards + custom SVG radar chart
- Radar chart: context-sensitive — per-control, per-function, or per-safeguard mode
- Per-control score in each control header (colour-coded green/amber/red)
- Cascading filters: IG level, status, security function, control group, free-text search
- C-prefix IDs: C01–C18 / C01-01 (internal IDs unchanged)
- Multi-note comment threads per safeguard with timestamps
- Evidence file uploads (images, PDFs, Office docs, text/CSV), 50 MB limit
- Expand/Collapse All, click-to-expand safeguard description
- Status dropdown auto-saves with "Saved" flash
- Export CSV, light/dark mode with localStorage persistence

**Implemented**
- Login page — email/password auth; no self-registration
- /setup — first-run org + admin account creation
- /logout

**Planned**
- **Home page with collapsible left sidebar** — primary navigation surface after login; sidebar lists all orgs the user belongs to, each expandable to show their assessments; inline actions to create a new org or a new assessment within an org; sidebar state (collapsed/expanded per org) persisted in `localStorage`; main content area shows a welcome/summary when no assessment is open
- **Assessment view** — full CIS controls accordion adapted to the new schema; read-only banner when lifecycle is `finalised`; lifecycle badge in navbar
- **Assessment lifecycle UI** — draft/active/finalised badge; activate and finalise actions for org_admin
- **Audit log panel** — collapsible panel in assessment view; paginated chronological change history
- **Risk register panel** — computed from `not_implemented` + `partial` safeguards; ranked by IG weight (IG1×3 + IG2×2 + IG3×1; halved for `partial`); exportable as CSV
- **Cross-assessment comparison** — dual-polygon radar (current = indigo solid, previous = emerald dashed) + per-control delta table with +/- indicators
- **User management page** — org_admin creates/edits/deletes users and assigns roles

## Key Implementation Decisions

- HTML structure is rendered **server-side** by Jinja2 (not JS). JS only handles interactivity.
- Filtering works by toggling a `hidden` CSS class on `.sg-row` elements — no re-rendering.
- No Bootstrap accordion JS — plain `style.display` toggle.
- IG scoring: IG1 score = % of ig1=true safeguards implemented; IG2 = all ig1+ig2; IG3 = all.
- Radar chart is custom SVG (no Chart.js) — consistent with zero-dependency philosophy.
- CSS design token system for all colours, spacing, radii — see `DESIGN_SYSTEM.md`.
- **Sessions**: Flask signed cookie sessions; werkzeug password hashing (bundled — no new deps).
- **Home page is the shell**: `GET /` renders the full page with sidebar; assessment views load inside it. The sidebar is always present on authenticated pages.
- **Sidebar navigation**: collapsible left sidebar lists orgs + their assessments; collapse state stored in `localStorage` keyed by org id. New org / new assessment actions live in the sidebar, not on separate pages.
- **Assessment isolation**: notes and attachments are assessment-scoped for audit integrity.
- **`assessment_id` in URL, not session** — bookmarkable; URL org_id must match session org_id (403 otherwise).
- **Audit log denormalisation**: `user_display` is snapshotted at write time so the trail survives user deletion.
- **Attachment naming**: `uploads/{att_id}{ext}` with globally unique autoincrement IDs — no path collision across assessments; no directory restructuring needed.
- **Risk register on demand**: computed at request time, not stored; excludes `not_assessed` safeguards to keep the register actionable.
- **Schema migrations**: `init_db()` tracks applied migrations in `schema_migrations`; existing single-assessment data migrates automatically to a default org + "Initial Assessment" on first run post-upgrade.

## Status / What's Working

- 7-table schema with migration from old single-assessment schema
- /setup (first-run org + admin), /login, /logout with Flask sessions
- CSRF protection on all POST forms; werkzeug scrypt password hashing
- SECRET_KEY warning on startup; SESSION_COOKIE_HTTPONLY + SAMESITE=Lax
- /orgs/<id>/assessments placeholder (real home page with sidebar is next)
- All 18 controls and 153 safeguards render correctly (legacy index.html, not yet wired to new schema)
- Light/dark mode works; app runs on 0.0.0.0:5000

## Potential Next Steps (future, not yet planned)

- SSO / OAuth integration (currently email+password only)
- Superadmin role spanning multiple orgs (for platform operators)
- "Copy assessment" to carry forward status from a previous assessment as a starting point
- Email notifications on assessment finalisation or user creation (requires SMTP config opt-in)
- Custom risk scoring weights per org
- Print / PDF report view
