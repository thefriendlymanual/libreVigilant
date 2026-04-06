# LibreVigilant

A self-hosted web application for tracking compliance against [CIS Controls v8.1.2](https://www.cisecurity.org/controls) (March 2025). Assess 153 safeguards across 18 controls, track evidence, and visualise your compliance posture — all from a single lightweight tool with zero external dependencies beyond Flask.

## Features

**Dashboard**
- Real-time IG1, IG2, and IG3 compliance scores with progress bars
- Interactive SVG radar chart showing per-control compliance at a glance
- Radar chart adapts to active filters: per-control overview, per-function breakdown, or individual safeguards
- Per-control score displayed in each control header

**Assessment Tracking**
- Five status levels per safeguard: Not Assessed, Not Implemented, Partial, Implemented, Not Applicable
- Auto-save on status change
- Scoring: Implemented = 100%, Partial = 50%, N/A excluded from totals

**Notes and Evidence**
- Multi-note comment threads per safeguard with timestamps
- File attachment support (images, PDFs, Office documents, text/CSV)
- Drag-and-drop or browse upload, 50 MB per file limit

**Filtering**
- Filter by Implementation Group (IG1, IG2, IG3)
- Filter by security function (Govern, Identify, Protect, Detect, Respond, Recover)
- Filter by control group (C01-C18)
- Filter by status
- Full-text search across safeguard IDs, titles, and descriptions
- All filters cascade — radar chart, stats, and table update together

**Export**
- CSV export with full assessment data including notes and attachments

**UI/UX**
- Light and dark mode with persistent preference
- Design system using CSS custom properties
- Consistent C-prefix ID convention (C01-C18 for controls, C01-01 for safeguards)
- Responsive layout
- Accessible: colour is never the sole indicator of status

## Quick Start

**Requirements:** Python 3 with Flask >= 3.0

```bash
pip install flask
```

**Run:**

```bash
python3 app.py
```

Open [http://localhost:5000](http://localhost:5000). The app also listens on all network interfaces (0.0.0.0:5000).

The SQLite database (`librevig.db`) is created automatically on first run.

## Project Structure

```
app.py               Flask application — routes, DB init, API endpoints
cis_data.json        CIS Controls v8.1.2 dataset (18 controls, 153 safeguards)
templates/
  index.html         Single-page UI (Jinja2 + vanilla JS + inline CSS)
uploads/             File attachments stored on disk
librevig.db          SQLite database (auto-created, gitignored)
DESIGN_SYSTEM.md     UI token reference for contributors
project.md           Internal architecture and API documentation
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main application page |
| GET | `/api/assessments` | All assessments, notes, and attachments as JSON |
| POST | `/api/assessments/<id>` | Update safeguard status |
| POST | `/api/assessments/<id>/notes` | Add a note |
| DELETE | `/api/notes/<id>` | Delete a note |
| POST | `/api/assessments/<id>/attachments` | Upload a file |
| GET | `/api/attachments/<id>` | Download/view an attachment |
| DELETE | `/api/attachments/<id>` | Delete an attachment |
| GET | `/api/export` | Export assessment as CSV |

## Technology

- **Backend:** Flask (Python 3) + SQLite
- **Frontend:** Vanilla JavaScript, Jinja2 server-side rendering
- **Styling:** CSS custom properties (design tokens), no frameworks
- **Charts:** Custom SVG radar chart, no chart libraries
- **Fonts:** System font stack only

No external JavaScript or CSS frameworks. No build step. No node_modules.

## License

[MIT](LICENSE)
