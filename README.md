# LibreVigilant

A self-hosted cybersecurity self-assessment and tracking tool built around the
[CIS Critical Security Controls v8.1.2](https://www.cisecurity.org/controls/v8) (March 2025).

The CIS Controls are a practical, prioritised framework of 153 safeguards across 18 control
areas — an accessible starting point for any organisation that wants to understand and
systematically improve its cybersecurity posture. LibreVigilant helps teams work through those
controls at their own pace, track where they are today, and make visible progress over time.

![Assessment view showing stat cards, radar chart and collapsed controls](docs/img/03-assessment-collapsed.jpg)

## Features

**Self-assessment**
- All 153 CIS v8.1.2 safeguards across 18 controls, grouped by control in a collapsible accordion
- Five status levels: Not Assessed, Not Implemented, Partial, Implemented, Not Applicable
- IG1/IG2/IG3 scoring with live progress indicators and an SVG radar chart
- Filter by Implementation Group, CIS function, control, or status — all client-side, instant
- Notes (threaded comments) and file evidence attachments per safeguard
- CSV export

**Assessment lifecycle**
- Draft → In Review → Completed — completed assessments are permanently read-only
- Create a new assessment blank or copied from any previous one (statuses and notes pre-populated)
- Audit log recording every status change, note, and attachment action

**Risk register**
- Project-scoped, persistent across assessment cycles
- Import gaps (Not Implemented / Partial safeguards) from any completed assessment
- Risk weighting: `IG1×3 + IG2×2 + IG3×1`, halved for Partial — highest-weight items listed first
- Triage inline: treatment, owner, target date, notes
- Close resolved items; reopen if circumstances change
- Reconciliation suggestions: after import, flags open items now showing Implemented in the new assessment
- CSV export

**Comparison**
- Place any two completed assessments side by side
- Dual-polygon SVG radar chart and a per-control delta table

![Compare view showing dual radar and control breakdown delta table](docs/img/07-compare.jpg)

**Multi-user, multi-project**
- Unlimited projects; each with its own assessments, risk register, and audit history
- Per-project roles: Admin, Editor, Viewer
- Instance-level admin for user management (no SMTP required)
- Self-service password change; admin password reset

**UI**
- Light and dark mode, persisted in `localStorage`
- Responsive layout with slide-in sidebar on mobile
- Accessible: skip link, ARIA landmarks, focus rings, `prefers-reduced-motion` support

## Quick Start

**Docker (recommended):**

```bash
git clone https://github.com/thefriendlymanual/libreVigilant.git
cd libreVigilant
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
mkdir -p data && sudo chown 1000:1000 data
docker compose up -d
```

Open [http://localhost:5000](http://localhost:5000). On first visit you'll be directed to `/setup`
to create the admin account.

**Python (for local use / home lab):**

```bash
pip install -r requirements.txt
SECRET_KEY="replace-with-a-long-random-string" python3 app.py
```

The SQLite database (`librevig.db`) and `uploads/` folder are created automatically on first run.

See [docs/docs.md](docs/docs.md) for the full deployment guide, including Gunicorn, systemd, and
reverse proxy options.

## Project Structure

```
app.py                  Flask app — routes, DB init, RBAC, all API endpoints
cis_data.json           CIS Controls v8.1.2 static dataset (loaded at startup)
requirements.txt        Flask >= 3.0 (only dependency)
Dockerfile
docker-compose.yml
templates/
  base.html             Layout shell, design tokens, shared component CSS
  _sidebar.html         Project/assessment nav sidebar
  _sidebar_script.html  Sidebar JS
  login.html            Authentication
  setup.html            First-run admin account creation
  home.html             Workspace home page
  assessment.html       Assessment accordion view
  risk_register.html    Project risk register
  compare.html          Cross-assessment comparison
  members.html          Project member management
  users.html            Instance user management
  error.html            Generic error page
docs/
  docs.md               User guide
  img/                  Screenshots
data/                   Docker volume — librevig.db + uploads/
DESIGN_SYSTEM.md        CSS token reference
project.md              Architecture and full API reference
```

## Technology

- **Backend:** Python 3 + Flask ≥ 3.0, SQLite (WAL mode)
- **Frontend:** Vanilla JavaScript, Jinja2 server-side rendering, inline CSS
- **Styling:** CSS custom properties (design tokens) — no frameworks, no build step
- **Charts:** Custom SVG radar chart — no charting libraries
- **Auth:** Werkzeug password hashing, Flask signed-cookie sessions, per-request CSRF tokens

No external JavaScript or CSS frameworks. No npm. No node_modules.

Developed with [Claude Code](https://claude.ai/code) (Anthropic).

## License

The **application code** is licensed under the [MIT License](LICENSE).

The **CIS Controls data** (`cis_data.json`) is derived from CIS Controls v8.1.2, the intellectual
property of the Center for Internet Security, Inc. (CIS®), licensed under the
[Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License](https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode).

> CIS Controls® are developed by the Center for Internet Security. For the most current version,
> visit [https://www.cisecurity.org/controls/](https://www.cisecurity.org/controls/).

**Important:** Because this repository includes CIS Controls content, **commercial use of this
project is not permitted** without prior written approval from CIS. The MIT license applies only
to the original application code and does not supersede the CIS Controls license terms.
