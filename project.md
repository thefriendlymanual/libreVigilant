# LibreVigilant — CIS Controls v8.1 Compliance Assessment Tool

## What It Is
A self-hosted web app for tracking compliance against CIS Controls Version 8.1.2 (March 2025).
Built with Flask + SQLite. No external dependencies beyond Flask itself.

## Purpose
Allows an organization to assess their implementation status for each of the 153 CIS safeguards
across 18 controls, track notes per safeguard, and view compliance scores by IG level.

## Project Structure
```
~/librevigilant/
  app.py              Flask app — routes, DB init, data loading
  cis_data.json       Static CIS Controls data (18 controls, 153 safeguards with descriptions)
  librevig.db             SQLite DB — stores assessment status + notes per safeguard
  requirements.txt    Just: flask>=3.0
  templates/
    index.html        Single-page UI (Jinja2 server-side rendering + vanilla JS)
  static/             (empty — all CSS/JS is inline in index.html)
```

## How to Run
```bash
python3 app.py
```
Access at http://localhost:5000 (also available on local network at port 5000).

Flask was installed with:
```bash
python3 /tmp/get-pip.py --user --break-system-packages
~/.local/bin/pip install flask --user --break-system-packages
```

## Data Model
**cis_data.json** — static, never changes:
- 18 controls, each with a list of safeguards
- Each safeguard: `id`, `asset_class`, `function`, `title`, `description`, `ig1`, `ig2`, `ig3` (booleans)

**librevig.db** — `assessments` table:
- `safeguard_id` (PK, e.g. "1.1")
- `status`: `not_assessed` | `not_implemented` | `partial` | `implemented` | `not_applicable`
- `notes`: free text
- `updated_at`: timestamp string

## API Routes
- `GET /` — main page (server-side rendered, all 153 rows in HTML)
- `GET /api/assessments` — returns all saved assessments as JSON
- `POST /api/assessments/<id>` — save status for a safeguard
- `POST /api/assessments/<id>/notes` — add a note
- `DELETE /api/notes/<id>` — delete a note
- `POST /api/assessments/<id>/attachments` — upload evidence file
- `GET /api/attachments/<id>` — download/view attachment
- `DELETE /api/attachments/<id>` — delete attachment
- `GET /api/export` — download full assessment as CSV

## UI Features
- **Dashboard**: stat cards (total, IG1/IG2/IG3 scores) stacked vertically on the left, SVG radar chart on the right
- **Radar chart**: context-sensitive — shows per-control overview by default, per-control scores for a selected function, or per-safeguard status for a selected control. All filters cascade.
- **Per-control score** shown in each control header (colour-coded: green >= 80%, amber >= 50%, red > 0%)
- **Filters**: by IG level, status, security function, control group, free-text search — all cascading
- **C-prefix IDs**: controls display as C01–C18, safeguards as C01-01 etc. (internal data unchanged)
- **Notes**: multi-note comment threads per safeguard with timestamps
- **Attachments**: evidence file uploads (images, PDFs, Office docs, text/CSV), 50 MB limit
- **Expand/Collapse All** buttons
- **Click safeguard title** to expand full description
- **Status dropdown** auto-saves on change with a brief "Saved" flash
- **Export CSV** button downloads full assessment
- **Light/dark mode** toggle with persistent preference (`librevig-theme` in localStorage)

## Key Implementation Decisions
- HTML structure is rendered **server-side** by Jinja2 (not JS). JS only handles interactivity.
  This was critical — an earlier version tried to build the accordion DOM in JS and failed silently.
- Filtering works by toggling a `hidden` CSS class on `.sg-row` elements — no re-rendering.
- No Bootstrap accordion JS used for expand/collapse — plain `style.display` toggle instead.
- IG scoring: IG1 score = % of ig1=true safeguards implemented; IG2 = all ig1+ig2 safeguards; IG3 = all.
- Radar chart is custom SVG (no Chart.js) — consistent with zero-dependency philosophy.
- CSS design token system for all colours, spacing, radii — see `DESIGN_SYSTEM.md`.

## Status / What's Working
- All 18 controls and 153 safeguards render correctly
- Status tracking persists to SQLite
- Notes and attachments persist to SQLite + disk
- Filtering works (IG level, status, function, control, search) — all cascading
- Radar chart updates live on status changes and filter changes
- Per-control and per-IG scores calculate correctly
- CSV export works with C-prefix IDs
- Light/dark mode works
- App runs on 0.0.0.0:5000

## Potential Next Steps (not yet implemented)
- Multi-user / named assessments (currently single shared assessment)
- Assessment history / audit trail
- Print/PDF report view
- Due dates or ownership assignment per safeguard
- Import previous CSV assessment
