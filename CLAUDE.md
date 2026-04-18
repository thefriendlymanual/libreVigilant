# LibreVigilant — Claude Code Guide

## Project Overview

Self-hosted Flask web app for tracking compliance against CIS Controls v8.1.2 (153 safeguards, 18 controls). Zero external frontend dependencies — no npm, no build step.

## Tech Stack

- **Backend**: Python 3 + Flask >= 3.0, SQLite 3 (auto-created as `librevig.db`)
- **Frontend**: Vanilla JS, Jinja2 server-side rendering, inline CSS with CSS custom properties
- **No build step**: All frontend assets are inline in `templates/index.html`

## Running the App

```bash
pip install -r requirements.txt
python3 app.py
# Serves at http://localhost:5000
```

- DB is auto-created on first run via `init_db()` in `app.py`
- Debug mode: disabled by default; enable with `FLASK_DEBUG=true`
- Max upload size: 50 MB

## Key Files

| File | Purpose |
|---|---|
| `app.py` | Flask routes, DB init, API endpoints |
| `cis_data.json` | Static CIS Controls v8.1.2 dataset (loaded at startup) |
| `templates/index.html` | Entire UI: Jinja2 + vanilla JS + inline CSS (~1200 lines) |
| `DESIGN_SYSTEM.md` | **Mandatory reference** for all UI work — CSS tokens, typography, spacing |
| `project.md` | Internal architecture and API documentation |

## Architecture Notes

- **Server-side rendering**: Jinja2 builds the full HTML; JS handles interactivity only. Do not move safeguard rendering to JavaScript.
- **Filtering**: CSS class toggling (`.hidden` on `.sg-row`) — no DOM re-rendering or backend queries.
- **Radar chart**: Custom SVG, no Chart.js or D3.
- **ID formatting**: Safeguard IDs stored as `"1.1"` internally, displayed as `"C01-01"` via app.py formatting — never store C-prefixed IDs.

## Conventions

- **CSS**: All colors/spacing must use CSS custom properties from DESIGN_SYSTEM.md. Never hardcode hex values.
- **Theme**: `data-theme="light|dark"` on `<html>`; persisted in `localStorage["librevig-theme"]`.
- **DB columns**: snake_case (`safeguard_id`, `created_at`, `uploaded_at`)
- **Valid statuses**: `not_assessed`, `not_implemented`, `partial`, `implemented`, `not_applicable`

## No Tests

No automated test suite. Manual testing only.
