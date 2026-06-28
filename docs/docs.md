# LibreVigilant — User Guide

LibreVigilant is a cybersecurity self-assessment and tracking tool built around the
[CIS Critical Security Controls v8.1.2](https://www.cisecurity.org/controls/v8). The CIS Controls
are a practical, prioritised framework of 153 safeguards across 18 control areas — an accessible
starting point for any organisation that wants to understand and systematically improve its
cybersecurity posture.

LibreVigilant is designed to help organisations understand their initial baseline cybersecurity posture, identify and prioritise improvement actions based on risk and to enable tracking changes to the posture over time. 

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

**Docker is the recommended way to run LibreVigilant** (Option B) — it bundles a production
WSGI server and keeps the host clean. Option A (running Python directly) is documented for
servers or laptops where Docker isn't available or wanted.

### Option A — Running directly with Python

Requirements: Python 3.10+.

We recommend using a virtual environment to isolate dependencies:

```bash
python3 -m venv venv && source venv/bin/activate
```

```bash
git clone https://github.com/your-org/librevigilant.git
cd librevigilant
pip install -r requirements.txt
SECRET_KEY=your-secret-here python3 app.py
```

The app starts on port 5000. SQLite database (`librevig.db`) and the `uploads/` folder are created
automatically on first run. Set `SECRET_KEY` to a long random string — without it, sessions are
invalidated every time the process restarts.

This is fine for trying the app out or a home lab. The above runs Flask's built-in development
server in the foreground (`Ctrl+C` to stop) — it is single-threaded and not hardened for
team-facing or networked use. For anything beyond a quick trial, use the production setup below.

> **Windows:** Gunicorn does not run on Windows. Use Docker, Podman, or WSL instead — see
> Option B.

#### Running in production: Gunicorn

Run the app behind Gunicorn instead of the dev server:

```bash
SECRET_KEY=your-secret-here gunicorn --preload -w 2 -b 0.0.0.0:5000 app:app
```

This still runs in the foreground. For a real deployment you want it running in the background,
restarting automatically on crash or reboot, and easy to start/stop — use systemd for that.

#### Running in production: systemd service

Create `/etc/systemd/system/librevigilant.service` (adjust `User`, `WorkingDirectory`, and the
venv path to match your install):

```ini
[Unit]
Description=LibreVigilant
After=network.target

[Service]
User=librevigilant
WorkingDirectory=/opt/librevigilant
Environment=SECRET_KEY=your-secret-here
ExecStart=/opt/librevigilant/venv/bin/gunicorn --preload -w 2 -b 0.0.0.0:5000 app:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now librevigilant   # start now, and on every boot
```

Common commands:

```bash
sudo systemctl stop librevigilant
sudo systemctl restart librevigilant
sudo systemctl status librevigilant
journalctl -u librevigilant -f              # follow logs
```

### Option B — Docker (recommended)

Requirements: Docker with the Compose plugin.

```bash
git clone https://github.com/your-org/librevigilant.git
cd librevigilant
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
mkdir -p data && sudo chown 1000:1000 data
docker compose up -d
```

The container runs as a non-root user (uid 1000), so the host `./data` directory must be
writable by that uid — the `chown` step above takes care of that. If you skip it, Compose will
create `./data` as `root:root` and the app will fail to create `librevig.db` inside it.

The app is available at `http://localhost:5000`. `librevig.db` and the `uploads/` folder are
persisted on the host under `./data/`, so they survive container rebuilds and `docker compose
down`. The container runs the app via Gunicorn, not the Flask dev server.

Common commands:

```bash
docker compose logs -f      # follow logs
docker compose restart      # restart the app
docker compose down         # stop and remove the container (data in ./data/ is kept)
```

### Option C — Docker Compose with Traefik and automatic TLS

This extends Option B with Traefik as a TLS-terminating reverse proxy. Certificates are
issued automatically by Let's Encrypt using the **DNS-01 challenge** — the only ACME
challenge type that works on internal networks, since it proves domain ownership by writing
a DNS TXT record rather than requiring any inbound port to be reachable from the internet.

The example below uses **Cloudflare** as the DNS provider. Traefik supports many other DNS
providers through the [LEGO library](https://go-acme.github.io/lego/dns/) — the full list
of providers and their required environment variables is documented there. Traefik's own ACME
reference (including all challenge options) is at
[doc.traefik.io](https://doc.traefik.io/traefik/reference/install-configuration/tls/certificate-resolvers/acme/#the-different-acme-challenges).
To switch providers, replace `CF_DNS_API_TOKEN` in the `.env` and change the `provider:` value
in `traefik/traefik.yml` to match your provider's LEGO name.

**Prerequisites:**
- A domain whose DNS is managed by a [LEGO-supported provider](https://go-acme.github.io/lego/dns/)
  (Cloudflare in this example). The host running LibreVigilant does not need to be reachable
  from the internet — only the DNS provider's API does.
- A Cloudflare API token with **Zone → DNS → Edit** and **Zone → Zone → Read** permissions,
  scoped to the relevant zone.

#### 1. Create a Cloudflare API token

In the Cloudflare dashboard: **My Profile → API Tokens → Create Token**.
Use the *Edit zone DNS* template, scope it to your zone, and copy the token.

#### 2. Prepare the `traefik/` directory

The repository ships with ready-to-use config files in `traefik/`:

```
traefik/
  docker-compose.yml   Traefik + app services, with labels for automatic routing
  traefik.yml          Traefik static config: entrypoints, DNS-01 resolver
```

Create the certificate storage file and lock it down — ACME requires it to be `600`:

```bash
touch traefik/acme.json
chmod 600 traefik/acme.json
```

#### 3. Set environment variables

Add to your `.env` file (in the project root, alongside the main `docker-compose.yml`):

```bash
SECRET_KEY=your-secret-here        # already set from Option B
CF_DNS_API_TOKEN=your-token-here   # Cloudflare API token from step 1
DOMAIN=librevigilant.example.com   # the hostname to serve the app on
```

#### 4. Set your email in `traefik/traefik.yml`

Open `traefik/traefik.yml` and replace `your-email@example.com` with your address —
Let's Encrypt uses it for expiry notifications:

```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      email: "you@example.com"
```

#### 5. Point DNS at the host

The hostname needs to resolve to the machine running LibreVigilant, but it does **not**
need a public DNS record. For an internal-only deployment, create the record on your local
DNS server (e.g. Pi-hole, AdGuard Home, a router with custom DNS, or Windows Server DNS)
pointing `librevigilant.example.com` at the host's private IP address. A private IP is
perfectly valid — Let's Encrypt never connects to your host; it only checks for the DNS TXT
record that Traefik creates via the Cloudflare API.

If the host is also publicly reachable and you want external access, you can instead create
a public A record in Cloudflare pointing to the public IP — but this is not required for
internal use.

#### 6. Start

Run Compose from the `traefik/` directory (which has its own `docker-compose.yml`):

```bash
cd traefik
docker compose --env-file ../.env up -d
```

Traefik will request a certificate from Let's Encrypt on first start. DNS propagation
can take a few minutes — check progress with `docker compose logs -f traefik`.

Once running, LibreVigilant is available at `https://librevigilant.example.com`.
HTTP requests are redirected to HTTPS automatically.

Common commands (from the `traefik/` directory):

```bash
docker compose --env-file ../.env logs -f        # follow logs
docker compose --env-file ../.env restart app    # restart the app only
docker compose --env-file ../.env down           # stop everything
```

> **Note:** `SESSION_COOKIE_SECURE` should be set to `True` for production deployments
> behind a TLS proxy. This requires `ProxyFix` middleware to correctly read
> `X-Forwarded-Proto` headers from Traefik — a follow-up hardening step documented in
> `SECURITY.md` (item M1).

---

## 2. First Run

On the very first visit, the app redirects you to `/setup`. Fill in a display name, email address,
and password — this creates the **instance admin** account. The setup page is only accessible while
no users exist; it locks itself permanently once the first account is created. After setup you are
logged in automatically and land on the home page.

![The home workspace with sidebar showing projects and assessments](img/02-home.jpg)

From here, create your first project or add further user accounts (via the **Users** page in the
top navbar, visible to instance admins only).

**Adding users:** LibreVigilant has no self-registration and requires no email server. Instance
admins create accounts directly on the Users page: provide a display name, email, and temporary
password, then share those credentials with the person.

![User management page showing all users, roles and project memberships](img/10-users.jpg)

**Changing your password:** Once logged in, click your display name in the top navbar to open the
**Change password** dialog. Enter your current password and a new one (minimum 12 characters) to
update it immediately — no admin involvement needed. Instance admins can still force-reset any
user's password from the Users page if someone is locked out.

The sign-in page is shown on any unauthenticated visit:

![Sign-in page](img/01-login.jpg)

---

## 3. Creating a Project and Adding Members

A **Project** is the top-level container for your security improvement work. Each project holds
its own assessments, risk register, and audit history. You can run multiple projects in parallel —
for example, one per business unit, site, or engagement.

**Create a project:** Click **+ New project** at the bottom of the left sidebar. Give it a name;
LibreVigilant generates a URL slug automatically. The project appears in the sidebar immediately.

**Add members:** Open the project in the sidebar and click **Members** under Project tools. Use
the dropdown to select an existing user and assign them a role:

| Role | What they can do |
|---|---|
| **Admin** | Full control — create and delete assessments, manage members, import to risk register |
| **Editor** | Assess safeguards, add notes and evidence, edit risk items |
| **Viewer** | Read-only access to all project data, can export CSV |

A user can hold different roles across different projects. The instance admin role (set on the
Users page) only grants access to the Users page — project roles govern everything within a project.

![Project members page showing team members with their roles](img/09-members.jpg)

---

## 4. Running an Assessment

An assessment is a point-in-time snapshot of where your organisation stands against the 153 CIS
safeguards. The goal is not to achieve a particular score but to build an honest picture of your
current posture — understanding your gaps is the first step to addressing them.

**Create:** From the sidebar, click **+ New assessment** under the project name. A modal appears
asking for a name and a starting point — either blank or copied from a previous assessment in the
same project. Copying pre-populates all safeguard statuses and notes, so you only need to record
what changed. Only project admins can create assessments.

![Create assessment modal with name field and Start From dropdown](img/11-create-from-template-modal.jpg)

**Work through the safeguards:** Open the assessment to see the full accordion view, grouped by
CIS control. Score cards and a radar chart at the top update live as you work.

![Assessment view showing stat cards, radar chart and collapsed controls](img/03-assessment-collapsed.jpg)

Expand any control to see its safeguards. For each one, record your honest current state:

| Status | Meaning |
|---|---|
| Not assessed | Default — not yet reviewed |
| Not implemented | This safeguard is not in place |
| Partial | Some elements are in place but the safeguard is not complete |
| Implemented | Fully in place |
| Not applicable | Out of scope for this organisation or environment |

![Control expanded showing individual safeguards with statuses and IG level badges](img/04-assessment-expanded.jpg)

Editors and admins can set statuses, add notes (threaded comments per safeguard), and attach
evidence files. Click the **Notes** button on any safeguard row to open the notes panel inline —
useful for capturing rationale, decisions, or links to supporting evidence.

![Notes panel open on a safeguard showing threaded comments](img/05-notes-panel.jpg)

Viewers can read everything and export to CSV.

**Implementation Groups:** Each safeguard is tagged IG1, IG2, and/or IG3, reflecting the CIS
guidance on which organisations should prioritise it:

- **IG1** — essential cyber hygiene, recommended for every organisation regardless of size or
  resources. A strong starting point for any team new to the Controls.
- **IG2** — builds on IG1 for organisations with more IT complexity, dedicated security staff, or
  a greater exposure to sensitive data. Suitable for most mid-sized organisations.
- **IG3** — the full set, targeting organisations that face sophisticated, targeted attacks and
  have the resources and expertise to implement advanced controls.

The filter bar lets you focus on a specific IG level, CIS function, or control area — useful for
working through the assessment in structured passes rather than trying to do everything at once.

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
remediation plan over time. Rather than re-entering context every cycle, the register carries
your decisions forward: treatment choices, owners, target dates, and notes all survive from one
assessment to the next.

![Risk register showing open items with treatment, owner, target date and weight columns](img/06-risk-register.jpg)

**Import:** On the Risk Register page, select a completed assessment and click **Import gaps**.
LibreVigilant adds any safeguards with a status of *Not implemented* or *Partial* that aren't
already in the register. Existing items are never overwritten — your treatment notes, owners, and
target dates are preserved.

Each imported item is assigned a **risk weight** (`IG1 × 3 + IG2 × 2 + IG3 × 1`, halved for
Partial status) to reflect the breadth of impact across implementation groups. Items are listed
highest-weight first by default, giving a natural starting point for prioritisation.

**Triage each item** by expanding the inline editor:

- **Treatment** — Accept, Mitigate, Transfer, Avoid, or Remediate
- **Owner** — free text; name or team responsible
- **Target date** — planned completion date
- **Notes** — context, decisions, links to tickets or evidence

**Close an item** once a safeguard is in place. The Current Status column (pulled from the most
recent assessment) shows whether a safeguard has improved since the item was opened — an amber
*Resolved in latest* badge appears when it has. Items can be reopened if circumstances change.

**Export:** Download the full register as CSV for use in reports or spreadsheets.

---

## 6. Comparing Assessments

The Compare view lets you place two completed assessments side by side to see how your posture
has shifted. Select them from the dropdowns and click **Compare**. You get:

- **Dual-polygon radar chart** — one polygon per assessment, overlaid on the same 18-control axes.
  The score per control reflects the proportion of implemented and partial safeguards (not-applicable
  safeguards are excluded from the denominator, so out-of-scope areas don't drag down your picture).
- **Delta table** — every control listed with its score in each assessment and the percentage-point
  change. The legend panel summarises the net change and counts of improved, unchanged, and declined
  controls.

![Compare view showing dual-polygon radar chart with legend and overall scores](img/07-compare.jpg)

![Control breakdown table showing A%, B% and delta for all 18 controls](img/08-compare-delta.jpg)

The Compare view is most useful after completing a follow-on assessment — it gives a concrete,
visual account of where your security posture has improved and where effort is still needed.

---

## 7. Follow-on Assessments

Security posture improvement is an ongoing process, not a one-time exercise. Running assessments
at regular intervals — quarterly, annually, or after significant infrastructure change — lets you
track progress, revisit decisions, and keep your risk register current.

When creating a new assessment, the **Start from** dropdown lets you copy an existing assessment
as a template. This pre-populates all safeguard statuses and notes so you only need to record
what changed since the previous cycle — a significant time saving on subsequent passes.

Once the new assessment is completed:

1. **Re-import to the risk register.** Import from the new assessment. Items already in the
   register are skipped; newly identified gaps are added.
2. **Review reconciliation suggestions.** After import, LibreVigilant checks whether any open
   risk items are now showing *Implemented* in the new assessment. If any are found, a modal
   lists them and lets you close them in bulk — your treatment notes are preserved.
3. **Update the register.** Work through any new items, update owners and target dates, and close
   anything else that has been addressed.
4. **Compare.** Use the Compare view to show the shift in posture between the previous and new
   assessment.

Over time, the risk register becomes a living improvement roadmap — carrying your context and
decisions forward across every assessment cycle.
