# LibreVigilant — User Guide

LibreVigilant is a self-hosted web application for tracking your organisation's compliance against
[CIS Controls v8.1.2](https://www.cisecurity.org/controls/v8). It covers all 153 safeguards across
18 controls, supports multiple projects and team members, and maintains a living risk register that
you update across successive assessment cycles.

**Typical workflow:** deploy → create users → create a project → run an initial assessment →
import gaps to the risk register → compare follow-on assessments → close resolved risks.

---

## Contents

1. [Deployment](#1-deployment)
2. [First Run](#2-first-run)
3. [Creating a Project and Adding Members](#3-creating-a-project-and-adding-members)
4. [Running an Assessment](#4-running-an-assessment)
5. [Risk Register](#5-risk-register)
6. [Comparing Assessments](#6-comparing-assessments)
7. [Follow-on Assessments](#7-follow-on-assessments)

---

## 1. Deployment

### Option A — Python (development / small teams)

Requirements: Python 3.10+.

```bash
git clone https://github.com/your-org/librevigilant.git
cd librevigilant
pip install -r requirements.txt
SECRET_KEY=your-secret-here python3 app.py
```

The app starts on port 5000. SQLite database (`librevig.db`) and the `uploads/` folder are created
automatically on first run. Set `SECRET_KEY` to a long random string — without it, sessions are
invalidated every time the process restarts.

This option is fine for a single machine or a home lab. For anything team-facing, use one of the
options below so you get TLS and a production-grade HTTP server.

### Option B — Docker

> Docker support is on the roadmap. This section will be completed when the Dockerfile ships.

### Option C — Docker Compose with a reverse proxy

> Docker Compose support (with Traefik or Caddy for TLS termination) is on the roadmap. This
> section will be completed alongside Option B.

---

## 2. First Run

On the very first visit, the app redirects you to `/setup`. Fill in a display name, email address,
and password — this creates the **instance admin** account. The setup page is only accessible while
no users exist; it locks itself permanently once the first account is created.

After setup you land on the home page with an empty workspace. From here, create your first project
or add further user accounts (via the **Users** page in the top navbar, visible to instance admins
only).

**Adding users:** LibreVigilant has no self-registration and requires no email server. Instance
admins create accounts directly on the Users page: provide a display name, email, and temporary
password, then share those credentials with the person.

**Changing your password:** Once logged in, click your display name in the top navbar to open the
**Change password** dialog. Enter your current password and a new one (minimum 12 characters) to
update it immediately — no admin involvement needed. Instance admins can still force-reset any
user's password from the Users page if someone is locked out.

---

## 3. Creating a Project and Adding Members

A **Project** is the top-level container for all your compliance work. Each project holds its own
assessments, risk register, and audit history. You can run multiple projects in parallel — for
example, one per business unit or client engagement.

**Create a project:** Click **+ New project** at the bottom of the left sidebar. Give it a name;
LibreVigilant generates a URL slug automatically. The project appears in the sidebar immediately.

**Add members:** Open the project in the sidebar and click **Members** under Project tools. Enter
a user's email address and assign them a role:

| Role | What they can do |
|---|---|
| **Admin** | Full control — create and delete assessments, manage members, import to risk register |
| **Editor** | Assess safeguards, add notes and evidence, edit risk items |
| **Viewer** | Read-only access to all project data, can export CSV |

A user can hold different roles across different projects. The instance admin role (set on the
Users page) only grants access to the Users page — project roles govern everything within a project.

---

## 4. Running an Assessment

An assessment is a point-in-time snapshot of your compliance posture against all 153 CIS safeguards.

**Create:** From the sidebar, click **+ New assessment** under the project name. Give it a
descriptive name (e.g. "Q2 2026 — Initial baseline"). Only project admins can create assessments.

**Assess safeguards:** Open the assessment to see the full accordion view, grouped by CIS control.
Set a status on each safeguard:

| Status | Meaning |
|---|---|
| Not assessed | Default — not yet reviewed |
| Not implemented | The control is absent |
| Partial | Some elements in place but not complete |
| Implemented | Fully in place |
| Not applicable | Excluded from scope with justification |

Editors and admins can set statuses, add notes (threaded comments), and attach evidence files.
Viewers can read everything and export to CSV. The assessment view includes an SVG radar chart and
score summary cards — these update live as you work.

**Filtering:** Use the filter bar above the accordion to narrow by IG level, CIS function, control,
or status. Filtering is instant and client-side — no page reload.

**Lifecycle:**

1. **Draft** — editable by all editors and admins.
2. **In Review** — an admin clicks *Start review* to signal the assessment is under final
   scrutiny. Still editable.
3. **Completed** — an admin clicks *Complete*. The assessment becomes permanently read-only and
   its results are preserved for comparison and risk register import.

An assessment must reach Completed before it can be imported to the risk register or used in
a comparison.

---

## 5. Risk Register

The risk register is project-scoped — it persists across assessments and accumulates your
remediation plan over time. All open gaps (non-implemented safeguards) from any completed
assessment can be imported into it.

**Import:** On the Risk Register page, select a completed assessment and click **Import gaps**.
LibreVigilant adds any safeguards with a status of *Not implemented* or *Partial* that aren't
already in the register. Existing items are never overwritten — your treatment notes, owners, and
target dates are safe.

Each imported item is assigned a **risk weight** (`IG1 × 3 + IG2 × 2 + IG3 × 1`, halved for
Partial status). Items are listed highest-weight first by default.

**Triage each item** by clicking its row to expand the inline editor:

- **Treatment** — Accept, Mitigate, Transfer, Avoid, or Remediate
- **Owner** — free text; name or team responsible
- **Target date** — ISO date for planned completion
- **Notes** — context, decisions, links to tickets

**Close an item** once the safeguard is implemented. The Current Status column (pulled from the
most recent assessment) shows whether a safeguard has improved since the item was opened — an
amber *Resolved in latest* badge appears when it has. Items can be reopened if circumstances change.

**Export:** Download the full register as CSV for use in spreadsheets or reports.

---

## 6. Comparing Assessments

The Compare view lets you place two completed assessments side by side. Select them from the
dropdowns and click **Compare**. You get:

- **Dual-polygon radar chart** — one polygon per assessment, overlaid on the same 18-control axes.
  Score per control runs 0–100% based on implemented and partial safeguards (not-applicable
  safeguards are excluded from the denominator).
- **Delta table** — every control listed with its score in each assessment and the percentage-point
  change. Controls that improved are highlighted green; regressions are highlighted red.

This view is most useful for comparing a baseline against a follow-on assessment to demonstrate
progress, or for comparing two projects against a shared benchmark.

---

## 7. Follow-on Assessments

CIS compliance is not a one-time exercise. Create a new assessment at each review cycle (quarterly,
annually, or after significant infrastructure change) and repeat the workflow from section 4.

Once the new assessment is completed:

1. **Re-import to the risk register.** Import from the new assessment. Items already in the
   register are skipped; new gaps are added.
2. **Review reconciliation suggestions.** After import, LibreVigilant checks whether any open risk
   items are now showing *Implemented* in the new assessment. A modal lists these and lets you close
   them in bulk with a single click — your treatment notes are preserved.
3. **Update the register.** Work through any new items, update owners and target dates, and close
   anything else that has been remediated.
4. **Compare.** Use the Compare view to show progress between the previous and new assessment.

Over time, the risk register becomes a living remediation roadmap that carries your decisions and
history forward, regardless of how many assessment cycles have passed.
