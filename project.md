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
separate tenants or organisations. Users do not belong to a tenant; they belong to the
instance and can be members of one or more Projects.

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
    setup.html          One-time first-run admin account setup (no project created here)
    home.html           Blank canvas / project list with collapsible left sidebar
    assessment.html     Main assessment view (Jinja2 SSR + vanilla JS)
    users.html          User management (admin only) [planned]
  static/               (empty — all CSS/JS is inline in templates)
```

## How to Run
```bash
python3 app.py
```
Access at http://localhost:5000 (also available on local network at port 5000).

On first run, visit `/setup` to create the admin account. No project is created at this
point — the user lands on a blank canvas and creates their first Project from the sidebar.

Set `SECRET_KEY` env var for production — without it, Flask uses a random key that invalidates
sessions on every restart:
```bash
SECRET_KEY=your-secret-here python3 app.py
```

## Data Model

**cis_data.json** — static, never changes:
- 18 controls, each with a list of safeguards
- Each safeguard: `id`, `asset_class`, `function`, `title`, `description`, `ig1`, `ig2`, `ig3` (booleans)

**librevig.db** — tables:

**`projects`** — named containers for compliance work (currently called `orgs` in code — rename pending)
- `id` (PK), `name`, `slug` (unique, URL-safe), `created_at`

**`users`** — user accounts for the instance
- `id` (PK), `email` (globally unique), `display_name`, `password_hash`
- `created_at`, `last_login_at`

**`user_projects`** — membership + role per project (currently called `user_orgs` in code — rename pending)
- `user_id` (FK), `project_id` (FK), `role`: `admin` | `editor` | `viewer`
- PRIMARY KEY (`user_id`, `project_id`)

**`assessments`** — named assessments per project
- `id` (PK), `project_id` (FK), `name`
- `lifecycle`: `draft` → `review` → `completed` (completed is read-only)
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
- `action`: `status_change` | `assessment_created` | `assessment_activated` | `assessment_completed` | `note_added` | `note_deleted` | `attachment_added` | `attachment_deleted`
- `safeguard_id` (nullable — null for assessment-level events), `old_value`, `new_value`, `occurred_at`

**`schema_migrations`** — tracks applied DB migrations
- `version` (PK), `applied_at`

## RBAC

Roles are per-project. The instance itself has no global role — the first account created via
`/setup` gets `admin` on any project it creates.

| Action | admin | editor | viewer |
|---|---|---|---|
| Manage users | Yes | No | No |
| Create / start review / complete assessments | Yes | No | No |
| Delete draft assessment | Yes | No | No |
| Edit safeguard status, notes, attachments | Yes | Yes | No |
| View audit log | Yes | Yes | No |
| View assessment (read) | Yes | Yes | Yes |
| Export CSV | Yes | Yes | Yes |
| View risk register | Yes | Yes | Yes |

No self-registration — an admin creates user accounts directly (no SMTP required).

## API Routes

**Auth**
- `GET /login` — login page
- `POST /login` — authenticate; set session; redirect
- `GET /logout` — clear session; redirect to login

**Bootstrap**
- `GET/POST /setup` — one-time setup; only accessible when no users exist; creates admin account only (no project)

**Root**
- `GET /` — home page with collapsible left sidebar (logged in); else redirects to `/login`

**Project Management** (currently `/orgs/` in code — rename pending)
- `POST /projects` — create project (any authenticated user)
- `POST /projects/<id>/delete` — delete project and all contents (admin)

**Assessment Management**
- `POST /projects/<id>/assessments` — create assessment (admin)
- `POST /projects/<id>/assessments/<id>/activate` — draft → review (admin)
- `POST /projects/<id>/assessments/<id>/finalise` — review → completed, read-only (admin)
- `POST /projects/<id>/assessments/<id>/delete` — delete draft (admin)
- `GET /projects/<id>/assessments/<id>` — full assessment accordion view (all roles)

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
- `GET /api/projects/<id>/compare?a=<id>&b=<id>` — cross-assessment score delta (all roles)

**User Management** (admin only) [planned]
- `GET /users` — user list page
- `POST /users` — create user
- `POST /users/<uid>/edit` — change role / display_name
- `POST /users/<uid>/delete` — delete user
- `GET/POST /users/<uid>/reset-password` — set new password

## UI Features

**Existing (working)**
- Login / logout, /setup for first-run admin creation
- Home page with collapsible left sidebar listing all projects + their assessments
- Sidebar: inline create new project, create new assessment within a project, delete project
- Assessment lifecycle: Draft → Review → Completed badges + action buttons (admin only)
- Full CIS controls accordion with stat cards (IG1/IG2/IG3) and SVG radar chart
- Cascading filters: IG level, status, security function, control group, free-text search
- Multi-note comment threads per safeguard with timestamps
- Evidence file uploads (images, PDFs, Office docs, text/CSV), 50 MB limit
- Status dropdown auto-saves with "Saved" flash
- Export CSV, light/dark mode with localStorage persistence

**Planned**
- **Audit log panel** — collapsible panel in assessment view; paginated chronological change history
- **Risk register panel** — computed from `not_implemented` + `partial` safeguards; ranked by IG weight (IG1×3 + IG2×2 + IG3×1; halved for `partial`); exportable as CSV
- **Cross-assessment comparison** — dual-polygon radar (current = indigo solid, previous = emerald dashed) + per-control delta table with +/- indicators
- **User management page** — admin creates/edits/deletes users and assigns per-project roles
- **UX review** — deferred until after audit log + risk register are built
- **Rename orgs → projects in code** — `orgs` table → `projects`, `user_orgs` → `user_projects`, routes `/orgs/` → `/projects/`, role `org_admin` → `admin`; requires a DB migration

## Key Implementation Decisions

- HTML structure is rendered **server-side** by Jinja2 (not JS). JS only handles interactivity.
- Filtering works by toggling a `hidden` CSS class on `.sg-row` elements — no re-rendering.
- No Bootstrap accordion JS — plain `style.display` toggle.
- IG scoring: IG1 score = % of ig1=true safeguards implemented; IG2 = all ig1+ig2; IG3 = all.
- Radar chart is custom SVG (no Chart.js) — consistent with zero-dependency philosophy.
- CSS design token system for all colours, spacing, radii — see `DESIGN_SYSTEM.md`.
- **Single-tenant**: the app does not support multiple isolated tenants. Multi-user (shared instance) is planned but not yet implemented.
- **Sessions**: Flask signed cookie sessions; werkzeug password hashing (bundled — no new deps).
- **Home page is the shell**: `GET /` renders the full page with sidebar; assessment views load inside it.
- **Sidebar navigation**: collapsible left sidebar lists projects + their assessments; collapse state stored in `localStorage` keyed by project id.
- **Blank canvas on first login**: `/setup` creates only the admin account; no project is created. The user creates their first project from the sidebar.
- **Assessment isolation**: notes and attachments are assessment-scoped for audit integrity.
- **`assessment_id` in URL, not session** — bookmarkable.
- **Audit log denormalisation**: `user_display` is snapshotted at write time so the trail survives user deletion.
- **Attachment naming**: `uploads/{att_id}{ext}` — no path collision across assessments.
- **Risk register on demand**: computed at request time, not stored; excludes `not_assessed` safeguards.
- **Schema migrations**: `init_db()` tracks applied migrations in `schema_migrations`.

## Pending Code / Naming Debt

The following are implemented under the old "org" terminology and need renaming in a future migration:

| Current (code) | Target (user-facing + code) |
|---|---|
| `orgs` table | `projects` table |
| `user_orgs` table | `user_projects` table |
| `org_id` FK columns | `project_id` FK columns |
| `/orgs/` URL prefix | `/projects/` URL prefix |
| `org_admin` role value | `admin` |
| "Organisation" in all UI text | "Project" |
| `/setup` creates org + admin | `/setup` creates admin only |
