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

**1. Clone the repository:**

```bash
git clone https://github.com/thefriendlymanual/libreVigilant.git
cd libreVigilant
```

If you already have the repo, pull the latest changes:

```bash
git pull
```

**2. Install dependencies:**

```bash
pip install flask
```

**3. Set a secret key:**

```bash
export SECRET_KEY="replace-with-a-long-random-string"
```

This is required to secure user sessions. The app will start without it but will warn you — do not skip this for any persistent or networked deployment.

**4. Start the app:**

```bash
python3 app.py
```

Open [http://localhost:5000](http://localhost:5000). The app also listens on all network interfaces (`0.0.0.0:5000`), so it is reachable from other devices on the same network.

The SQLite database (`librevig.db`) is created automatically on first run.

**5. First-run setup:**

On first run, you will be redirected to `/setup` to create your organisation and admin account. Fill in your organisation name, email address, display name, and a password. After completing setup, you will be taken directly to the login page.

**6. Stop the app:**

Press `Ctrl+C` in the terminal where the app is running.

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

The **application code** is licensed under the [MIT License](LICENSE).

The **CIS Controls data** (`cis_data.json`) is derived from CIS Controls v8.1.2, which is the intellectual property of the Center for Internet Security, Inc. (CIS®) and is licensed under the [Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License](https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode).

> CIS Controls® are developed by the Center for Internet Security. For the most current version, visit [https://www.cisecurity.org/controls/](https://www.cisecurity.org/controls/).

**Important:** Because this repository includes CIS Controls content, **commercial use of this project is not permitted** without prior written approval from CIS. The MIT license applies only to the original application code; it does not supersede the CIS Controls license terms.
