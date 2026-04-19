import json
import mimetypes
import os
import re
import secrets
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (Flask, Response, abort, jsonify, redirect, render_template,
                   request, send_file, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

_secret = os.environ.get("SECRET_KEY")
if not _secret:
    _secret = secrets.token_hex(32)
    print(
        "\n  !! WARNING: SECRET_KEY env var is not set.\n"
        "  !!          Sessions will not survive restarts.\n"
        "  !!          Set SECRET_KEY for any persistent deployment.\n"
    )
app.secret_key = _secret

DB_PATH = os.path.join(os.path.dirname(__file__), "librevig.db")
DATA_PATH = os.path.join(os.path.dirname(__file__), "cis_data.json")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".pptx",
    ".txt", ".csv", ".rtf",
}

VALID_STATUSES = {"not_assessed", "not_implemented", "partial", "implemented", "not_applicable"}

with open(DATA_PATH) as f:
    CIS_DATA = json.load(f)

# Pre-computed dummy hash used in login to prevent email-enumeration via timing.
_DUMMY_HASH = generate_password_hash("__timing_guard__")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def disk_path(att_id, filename):
    ext = os.path.splitext(filename)[1]
    return os.path.join(UPLOAD_DIR, f"{att_id}{ext}")


def _slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "org"


# ---------------------------------------------------------------------------
# DB init / migrations
# ---------------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # schema_migrations must exist before any other check.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version    TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        conn.commit()

        if not conn.execute("SELECT 1 FROM schema_migrations WHERE version='0001'").fetchone():
            # ---------------------------------------------------------------
            # Detect and snapshot the old 3-table single-assessment schema.
            # ---------------------------------------------------------------
            old_statuses = []
            old_notes = []
            old_attachments = []

            tbl = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='assessments'"
            ).fetchone()
            if tbl:
                cols = [row[1] for row in conn.execute("PRAGMA table_info(assessments)").fetchall()]
                if "safeguard_id" in cols:
                    old_statuses = conn.execute(
                        "SELECT safeguard_id, status, updated_at FROM assessments"
                    ).fetchall()
                    old_notes = conn.execute(
                        "SELECT safeguard_id, body, created_at FROM notes"
                    ).fetchall()
                    old_attachments = conn.execute(
                        "SELECT id, safeguard_id, filename, mime_type, size, uploaded_at FROM attachments"
                    ).fetchall()
                    for tbl_name in ("attachments", "notes", "assessments"):
                        conn.execute(f"DROP TABLE {tbl_name}")
                    conn.commit()

            # ---------------------------------------------------------------
            # Create the 7-table schema.
            # ---------------------------------------------------------------
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orgs (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT NOT NULL,
                    slug       TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id        INTEGER NOT NULL REFERENCES orgs(id),
                    email         TEXT NOT NULL UNIQUE,
                    display_name  TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role          TEXT NOT NULL DEFAULT 'viewer',
                    created_at    TEXT NOT NULL,
                    last_login_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS assessments (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id       INTEGER NOT NULL REFERENCES orgs(id),
                    name         TEXT NOT NULL,
                    lifecycle    TEXT NOT NULL DEFAULT 'draft',
                    start_date   TEXT,
                    end_date     TEXT,
                    created_by   INTEGER REFERENCES users(id),
                    finalised_by INTEGER REFERENCES users(id),
                    finalised_at TEXT,
                    created_at   TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS assessment_safeguards (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    assessment_id INTEGER NOT NULL REFERENCES assessments(id),
                    safeguard_id  TEXT NOT NULL,
                    status        TEXT NOT NULL DEFAULT 'not_assessed',
                    updated_at    TEXT,
                    updated_by    INTEGER REFERENCES users(id),
                    UNIQUE(assessment_id, safeguard_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    assessment_id INTEGER NOT NULL REFERENCES assessments(id),
                    safeguard_id  TEXT NOT NULL,
                    body          TEXT NOT NULL,
                    created_by    INTEGER REFERENCES users(id),
                    created_at    TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attachments (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    assessment_id INTEGER NOT NULL REFERENCES assessments(id),
                    safeguard_id  TEXT NOT NULL,
                    filename      TEXT NOT NULL,
                    mime_type     TEXT NOT NULL,
                    size          INTEGER NOT NULL,
                    uploaded_by   INTEGER REFERENCES users(id),
                    uploaded_at   TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    assessment_id INTEGER NOT NULL REFERENCES assessments(id),
                    user_id       INTEGER REFERENCES users(id),
                    user_display  TEXT NOT NULL,
                    action        TEXT NOT NULL,
                    safeguard_id  TEXT,
                    old_value     TEXT,
                    new_value     TEXT,
                    occurred_at   TEXT NOT NULL
                )
            """)
            conn.commit()

            # ---------------------------------------------------------------
            # Migrate old data → default org + "Initial Assessment".
            # ---------------------------------------------------------------
            if old_statuses or old_notes or old_attachments:
                now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                cur = conn.execute(
                    "INSERT INTO orgs (name, slug, created_at) VALUES (?, ?, ?)",
                    ("Default Organisation", "default", now),
                )
                org_id = cur.lastrowid
                cur = conn.execute(
                    "INSERT INTO assessments (org_id, name, lifecycle, created_at) VALUES (?, ?, 'active', ?)",
                    (org_id, "Initial Assessment", now),
                )
                asm_id = cur.lastrowid

                for row in old_statuses:
                    conn.execute(
                        "INSERT INTO assessment_safeguards "
                        "(assessment_id, safeguard_id, status, updated_at) VALUES (?, ?, ?, ?)",
                        (asm_id, row["safeguard_id"], row["status"], row["updated_at"]),
                    )
                for row in old_notes:
                    conn.execute(
                        "INSERT INTO notes (assessment_id, safeguard_id, body, created_at) VALUES (?, ?, ?, ?)",
                        (asm_id, row["safeguard_id"], row["body"], row["created_at"]),
                    )
                for row in old_attachments:
                    # Preserve original IDs so existing upload files on disk still resolve.
                    conn.execute(
                        "INSERT INTO attachments "
                        "(id, assessment_id, safeguard_id, filename, mime_type, size, uploaded_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (row["id"], asm_id, row["safeguard_id"],
                         row["filename"], row["mime_type"], row["size"], row["uploaded_at"]),
                    )
                conn.commit()

            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES ('0001', ?)",
                (datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),),
            )
            conn.commit()

        # -------------------------------------------------------------------
        # Migration 0002 — user_orgs junction table for multi-org membership.
        # -------------------------------------------------------------------
        if not conn.execute("SELECT 1 FROM schema_migrations WHERE version='0002'").fetchone():
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_orgs (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id   INTEGER NOT NULL REFERENCES users(id),
                    org_id    INTEGER NOT NULL REFERENCES orgs(id),
                    role      TEXT NOT NULL DEFAULT 'viewer',
                    joined_at TEXT NOT NULL,
                    UNIQUE(user_id, org_id)
                )
            """)
            # Seed from each user's primary org.
            conn.execute("""
                INSERT OR IGNORE INTO user_orgs (user_id, org_id, role, joined_at)
                SELECT id, org_id, role, created_at FROM users
            """)
            # Also seed from orgs where they created assessments
            # (covers orgs they moved away from via the old create_org route).
            conn.execute("""
                INSERT OR IGNORE INTO user_orgs (user_id, org_id, role, joined_at)
                SELECT DISTINCT a.created_by, a.org_id, 'org_admin',
                       COALESCE(a.created_at, datetime('now'))
                FROM assessments a WHERE a.created_by IS NOT NULL
            """)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES ('0002', ?)",
                (datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),),
            )
            conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _generate_csrf():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(32)
    return session["_csrf"]


def _validate_csrf():
    token = request.form.get("_csrf", "")
    expected = session.get("_csrf", "")
    if not expected or not secrets.compare_digest(token, expected):
        abort(400)


def _validate_csrf_api():
    token = request.headers.get("X-CSRF-Token", "")
    expected = session.get("_csrf", "")
    if not expected or not secrets.compare_digest(token, expected):
        abort(400)


@app.context_processor
def _inject_globals():
    return {
        "csrf_token": _generate_csrf(),
        "current_user": {
            "id": session.get("user_id"),
            "org_id": session.get("org_id"),
            "role": session.get("role"),
            "display_name": session.get("display_name"),
        } if "user_id" in session else None,
    }


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large (max 50 MB)"}), 413


@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="You don't have permission to do that."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found."), 404


# ---------------------------------------------------------------------------
# Bootstrap routes
# ---------------------------------------------------------------------------

@app.route("/setup", methods=["GET", "POST"])
def setup():
    # Accessible as long as no admin user exists yet.
    # A migrated DB may already have an org row but no users — that's fine.
    with get_db() as conn:
        has_users = conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    if has_users:
        abort(404)

    errors = []
    form = {}

    if request.method == "POST":
        _validate_csrf()
        form = request.form

        org_name = form.get("org_name", "").strip() or "Default Organisation"
        email = form.get("email", "").strip().lower()
        display_name = form.get("display_name", "").strip()
        password = form.get("password", "")
        confirm = form.get("confirm_password", "")

        if not email or "@" not in email or "." not in email.split("@")[-1]:
            errors.append("A valid email address is required.")
        if not display_name:
            errors.append("Display name is required.")
        if len(password) < 12:
            errors.append("Password must be at least 12 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if not errors:
            now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            slug = _slugify(org_name)
            password_hash = generate_password_hash(password)

            with get_db() as conn:
                existing_org = conn.execute("SELECT id FROM orgs LIMIT 1").fetchone()
                if existing_org:
                    # Migration already created an org — update its name and use it.
                    org_id = existing_org["id"]
                    conn.execute(
                        "UPDATE orgs SET name = ?, slug = ? WHERE id = ?",
                        (org_name, slug, org_id),
                    )
                else:
                    cur = conn.execute(
                        "INSERT INTO orgs (name, slug, created_at) VALUES (?, ?, ?)",
                        (org_name, slug, now),
                    )
                    org_id = cur.lastrowid

                conn.execute(
                    "INSERT INTO users (org_id, email, display_name, password_hash, role, created_at) "
                    "VALUES (?, ?, ?, ?, 'org_admin', ?)",
                    (org_id, email, display_name, password_hash, now),
                )
                conn.commit()

            return redirect(url_for("login"))

    return render_template("setup.html", errors=errors, form=form)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    error = None

    if request.method == "POST":
        _validate_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute(
                "SELECT id, org_id, email, display_name, password_hash, role "
                "FROM users WHERE email = ?",
                (email,),
            ).fetchone()

        # Always run check_password_hash regardless of whether the user exists
        # so response time does not leak whether the email is registered.
        candidate_hash = user["password_hash"] if user else _DUMMY_HASH
        valid = check_password_hash(candidate_hash, password)

        if user and valid:
            session.clear()
            session["user_id"] = user["id"]
            session["org_id"] = user["org_id"]
            session["role"] = user["role"]
            session["display_name"] = user["display_name"]

            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET last_login_at = ? WHERE id = ?",
                    (datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), user["id"]),
                )
                conn.commit()

            return redirect(url_for("index"))

        error = "Invalid email or password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Sidebar data
# ---------------------------------------------------------------------------

def _user_role_for_org(org_id):
    """Return the current user's role in org_id, or None if not a member."""
    if "user_id" not in session:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT role FROM user_orgs WHERE user_id = ? AND org_id = ?",
            (session["user_id"], org_id),
        ).fetchone()
    return row["role"] if row else None


def _load_sidebar_orgs():
    """All orgs the current user belongs to, each with their assessments."""
    if "user_id" not in session:
        return []
    with get_db() as conn:
        org_rows = conn.execute(
            "SELECT o.id, o.name, o.slug FROM orgs o "
            "JOIN user_orgs uo ON uo.org_id = o.id "
            "WHERE uo.user_id = ? ORDER BY o.name",
            (session["user_id"],),
        ).fetchall()
        result = []
        for org in org_rows:
            rows = conn.execute(
                "SELECT id, name, lifecycle, created_at FROM assessments "
                "WHERE org_id = ? ORDER BY created_at DESC",
                (org["id"],),
            ).fetchall()
            result.append({
                "id": org["id"],
                "name": org["name"],
                "slug": org["slug"],
                "assessments": [dict(a) for a in rows],
            })
        return result


def _lifecycle_summary(orgs):
    summary = {"draft": 0, "review": 0, "completed": 0}
    for org in orgs:
        for a in org["assessments"]:
            summary[a["lifecycle"]] = summary.get(a["lifecycle"], 0) + 1
    return summary


# ---------------------------------------------------------------------------
# Home (authenticated shell)
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    with get_db() as conn:
        has_users = conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    if not has_users:
        return redirect(url_for("setup"))
    if "user_id" not in session:
        return redirect(url_for("login"))

    orgs = _load_sidebar_orgs()
    return render_template(
        "home.html",
        orgs=orgs,
        lifecycle_summary=_lifecycle_summary(orgs),
        active_assessment=None,
    )


# ---------------------------------------------------------------------------
# Assessment management
# ---------------------------------------------------------------------------

@app.route("/orgs/<int:org_id>/assessments", methods=["POST"])
@login_required
def create_assessment(org_id):
    if _user_role_for_org(org_id) != "org_admin":
        abort(403)
    _validate_csrf()

    name = request.form.get("name", "").strip()
    if not name:
        abort(400)
    name = name[:200]

    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO assessments (org_id, name, lifecycle, created_by, created_at) "
            "VALUES (?, ?, 'draft', ?, ?)",
            (org_id, name, session["user_id"], now),
        )
        asm_id = cur.lastrowid
        conn.execute(
            "INSERT INTO audit_log "
            "(assessment_id, user_id, user_display, action, new_value, occurred_at) "
            "VALUES (?, ?, ?, 'assessment_created', ?, ?)",
            (asm_id, session["user_id"], session.get("display_name", ""), name, now),
        )
        conn.commit()

    return redirect(url_for("view_assessment", org_id=org_id, asm_id=asm_id))


@app.route("/orgs/<int:org_id>/assessments/<int:asm_id>/activate", methods=["POST"])
@login_required
def activate_assessment(org_id, asm_id):
    if _user_role_for_org(org_id) != "org_admin":
        abort(403)
    _validate_csrf()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_db() as conn:
        asm = conn.execute(
            "SELECT id, lifecycle FROM assessments WHERE id = ? AND org_id = ?",
            (asm_id, org_id),
        ).fetchone()
        if not asm:
            abort(404)
        if asm["lifecycle"] != "draft":
            abort(400)
        conn.execute(
            "UPDATE assessments SET lifecycle = 'review', start_date = ? WHERE id = ?",
            (now[:10], asm_id),
        )
        _log(conn, asm_id, "assessment_activated")
        conn.commit()
    return redirect(url_for("view_assessment", org_id=org_id, asm_id=asm_id))


@app.route("/orgs/<int:org_id>/assessments/<int:asm_id>/finalise", methods=["POST"])
@login_required
def finalise_assessment(org_id, asm_id):
    if _user_role_for_org(org_id) != "org_admin":
        abort(403)
    _validate_csrf()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_db() as conn:
        asm = conn.execute(
            "SELECT id, lifecycle FROM assessments WHERE id = ? AND org_id = ?",
            (asm_id, org_id),
        ).fetchone()
        if not asm:
            abort(404)
        if asm["lifecycle"] != "review":
            abort(400)
        conn.execute(
            "UPDATE assessments SET lifecycle = 'completed', finalised_by = ?, finalised_at = ?, end_date = ? "
            "WHERE id = ?",
            (session["user_id"], now, now[:10], asm_id),
        )
        _log(conn, asm_id, "assessment_completed")
        conn.commit()
    return redirect(url_for("view_assessment", org_id=org_id, asm_id=asm_id))


@app.route("/orgs/<int:org_id>/assessments/<int:asm_id>/delete", methods=["POST"])
@login_required
def delete_assessment(org_id, asm_id):
    if _user_role_for_org(org_id) != "org_admin":
        abort(403)
    _validate_csrf()
    with get_db() as conn:
        asm = conn.execute(
            "SELECT id, lifecycle FROM assessments WHERE id = ? AND org_id = ?",
            (asm_id, org_id),
        ).fetchone()
        if not asm:
            abort(404)
        if asm["lifecycle"] != "draft":
            abort(400)
        # Cascade-delete dependent rows (FK constraints are on, but SQLite needs explicit deletes
        # unless ON DELETE CASCADE was set — safer to do it explicitly).
        for table in ("audit_log", "attachments", "notes", "assessment_safeguards"):
            conn.execute(f"DELETE FROM {table} WHERE assessment_id = ?", (asm_id,))
        conn.execute("DELETE FROM assessments WHERE id = ?", (asm_id,))
        conn.commit()
    return redirect(url_for("index"))


@app.route("/orgs", methods=["POST"])
@login_required
def create_org():
    _validate_csrf()
    name = request.form.get("name", "").strip()
    if not name:
        abort(400)
    name = name[:200]
    slug = _slugify(name)
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_db() as conn:
        base_slug = slug
        counter = 2
        while conn.execute("SELECT 1 FROM orgs WHERE slug = ?", (slug,)).fetchone():
            slug = f"{base_slug}-{counter}"
            counter += 1
        cur = conn.execute(
            "INSERT INTO orgs (name, slug, created_at) VALUES (?, ?, ?)",
            (name, slug, now),
        )
        org_id = cur.lastrowid
        # Add the creating user as org_admin — don't change their primary org.
        conn.execute(
            "INSERT OR IGNORE INTO user_orgs (user_id, org_id, role, joined_at) VALUES (?, ?, 'org_admin', ?)",
            (session["user_id"], org_id, now),
        )
        conn.commit()
    return redirect(url_for("index"))


@app.route("/orgs/<int:org_id>/delete", methods=["POST"])
@login_required
def delete_org(org_id):
    if _user_role_for_org(org_id) != "org_admin":
        abort(403)
    _validate_csrf()
    with get_db() as conn:
        asm_ids = [
            r["id"] for r in conn.execute(
                "SELECT id FROM assessments WHERE org_id = ?", (org_id,)
            ).fetchall()
        ]
        for asm_id in asm_ids:
            for table in ("audit_log", "attachments", "notes", "assessment_safeguards"):
                conn.execute(f"DELETE FROM {table} WHERE assessment_id = ?", (asm_id,))
            conn.execute("DELETE FROM assessments WHERE id = ?", (asm_id,))
        conn.execute("DELETE FROM user_orgs WHERE org_id = ?", (org_id,))
        conn.execute("DELETE FROM orgs WHERE id = ?", (org_id,))
        conn.commit()

    # Redirect to home if the user still has other orgs, otherwise to login.
    remaining = _load_sidebar_orgs()
    if remaining:
        return redirect(url_for("index"))
    session.clear()
    return redirect(url_for("login"))


@app.route("/orgs/<int:org_id>/assessments/<int:asm_id>")
@login_required
def view_assessment(org_id, asm_id):
    if not _user_role_for_org(org_id):
        abort(403)
    with get_db() as conn:
        asm = conn.execute(
            "SELECT id, name, lifecycle, created_at FROM assessments "
            "WHERE id = ? AND org_id = ?",
            (asm_id, org_id),
        ).fetchone()
    if not asm:
        abort(404)

    orgs = _load_sidebar_orgs()
    return render_template(
        "assessment.html",
        orgs=orgs,
        active_assessment=dict(asm),
        active_org_id=org_id,
        controls=CIS_DATA["controls"],
        read_only=(asm["lifecycle"] == "completed"),
    )


# ---------------------------------------------------------------------------
# Assessment API — data access + mutations
# ---------------------------------------------------------------------------

def _load_assessment_or_abort(asm_id):
    """Fetch assessment + verify user can see it. Returns sqlite Row."""
    with get_db() as conn:
        asm = conn.execute(
            "SELECT id, org_id, name, lifecycle FROM assessments WHERE id = ?",
            (asm_id,),
        ).fetchone()
    if not asm:
        abort(404)
    if not _user_role_for_org(asm["org_id"]):
        abort(403)
    return asm


def _require_editable(asm):
    if asm["lifecycle"] == "completed":
        abort(403)
    if _user_role_for_org(asm["org_id"]) not in ("org_admin", "editor"):
        abort(403)


def _log(conn, asm_id, action, sg_id=None, old=None, new=None):
    conn.execute(
        "INSERT INTO audit_log "
        "(assessment_id, user_id, user_display, action, safeguard_id, old_value, new_value, occurred_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (asm_id, session.get("user_id"), session.get("display_name", ""),
         action, sg_id, old, new, datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
    )


@app.route("/api/assessments/<int:asm_id>")
@login_required
def api_get_assessment(asm_id):
    asm = _load_assessment_or_abort(asm_id)
    with get_db() as conn:
        statuses = conn.execute(
            "SELECT safeguard_id, status, updated_at FROM assessment_safeguards "
            "WHERE assessment_id = ?", (asm_id,),
        ).fetchall()
        notes = conn.execute(
            "SELECT id, safeguard_id, body, created_at FROM notes "
            "WHERE assessment_id = ? ORDER BY created_at",
            (asm_id,),
        ).fetchall()
        atts = conn.execute(
            "SELECT id, safeguard_id, filename, mime_type, size, uploaded_at "
            "FROM attachments WHERE assessment_id = ? ORDER BY uploaded_at",
            (asm_id,),
        ).fetchall()

    by_sg = {}
    for s in statuses:
        by_sg.setdefault(s["safeguard_id"], {"status": s["status"],
                                              "updated_at": s["updated_at"],
                                              "notes": [],
                                              "attachments": []})
    for n in notes:
        by_sg.setdefault(n["safeguard_id"], {"status": "not_assessed",
                                              "updated_at": None,
                                              "notes": [],
                                              "attachments": []})
        by_sg[n["safeguard_id"]]["notes"].append(dict(n))
    for a in atts:
        by_sg.setdefault(a["safeguard_id"], {"status": "not_assessed",
                                              "updated_at": None,
                                              "notes": [],
                                              "attachments": []})
        by_sg[a["safeguard_id"]]["attachments"].append(dict(a))

    return jsonify({
        "id": asm["id"],
        "name": asm["name"],
        "lifecycle": asm["lifecycle"],
        "safeguards": by_sg,
    })


@app.route("/api/assessments/<int:asm_id>/safeguards/<sg_id>", methods=["POST"])
@login_required
def api_update_status(asm_id, sg_id):
    asm = _load_assessment_or_abort(asm_id)
    _require_editable(asm)
    _validate_csrf_api()

    payload = request.get_json(silent=True) or {}
    status = payload.get("status", "")
    if status not in VALID_STATUSES:
        return jsonify({"error": "Invalid status"}), 400

    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_db() as conn:
        existing = conn.execute(
            "SELECT status FROM assessment_safeguards "
            "WHERE assessment_id = ? AND safeguard_id = ?",
            (asm_id, sg_id),
        ).fetchone()
        old = existing["status"] if existing else "not_assessed"

        if existing:
            conn.execute(
                "UPDATE assessment_safeguards SET status = ?, updated_at = ?, updated_by = ? "
                "WHERE assessment_id = ? AND safeguard_id = ?",
                (status, now, session["user_id"], asm_id, sg_id),
            )
        else:
            conn.execute(
                "INSERT INTO assessment_safeguards "
                "(assessment_id, safeguard_id, status, updated_at, updated_by) "
                "VALUES (?, ?, ?, ?, ?)",
                (asm_id, sg_id, status, now, session["user_id"]),
            )
        if old != status:
            _log(conn, asm_id, "status_change", sg_id=sg_id, old=old, new=status)
        conn.commit()

    return jsonify({"status": status, "updated_at": now})


@app.route("/api/assessments/<int:asm_id>/safeguards/<sg_id>/notes", methods=["POST"])
@login_required
def api_add_note(asm_id, sg_id):
    asm = _load_assessment_or_abort(asm_id)
    _require_editable(asm)
    _validate_csrf_api()

    payload = request.get_json(silent=True) or {}
    body = (payload.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Note body is required"}), 400
    body = body[:5000]

    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO notes (assessment_id, safeguard_id, body, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (asm_id, sg_id, body, session["user_id"], now),
        )
        note_id = cur.lastrowid
        _log(conn, asm_id, "note_added", sg_id=sg_id, new=body[:200])
        conn.commit()

    return jsonify({"id": note_id, "safeguard_id": sg_id, "body": body, "created_at": now})


@app.route("/api/assessments/<int:asm_id>/notes/<int:note_id>", methods=["DELETE"])
@login_required
def api_delete_note(asm_id, note_id):
    asm = _load_assessment_or_abort(asm_id)
    _require_editable(asm)
    _validate_csrf_api()

    with get_db() as conn:
        note = conn.execute(
            "SELECT id, safeguard_id, body FROM notes WHERE id = ? AND assessment_id = ?",
            (note_id, asm_id),
        ).fetchone()
        if not note:
            abort(404)
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        _log(conn, asm_id, "note_deleted",
             sg_id=note["safeguard_id"], old=note["body"][:200])
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/assessments/<int:asm_id>/safeguards/<sg_id>/attachments", methods=["POST"])
@login_required
def api_add_attachment(asm_id, sg_id):
    asm = _load_assessment_or_abort(asm_id)
    _require_editable(asm)
    _validate_csrf_api()

    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file"}), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"File type '{ext}' not allowed"}), 400

    # Sanitise the display filename; disk path is derived from attachment id.
    safe_name = re.sub(r"[^\w\s.\-]", "_", f.filename)[:255]
    mime = f.mimetype or mimetypes.guess_type(f.filename)[0] or "application/octet-stream"
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO attachments "
            "(assessment_id, safeguard_id, filename, mime_type, size, uploaded_by, uploaded_at) "
            "VALUES (?, ?, ?, ?, 0, ?, ?)",
            (asm_id, sg_id, safe_name, mime, session["user_id"], now),
        )
        att_id = cur.lastrowid
        path = disk_path(att_id, safe_name)
        f.save(path)
        size = os.path.getsize(path)
        conn.execute("UPDATE attachments SET size = ? WHERE id = ?", (size, att_id))
        _log(conn, asm_id, "attachment_added", sg_id=sg_id, new=safe_name)
        conn.commit()

    return jsonify({
        "id": att_id,
        "safeguard_id": sg_id,
        "filename": safe_name,
        "mime_type": mime,
        "size": size,
        "uploaded_at": now,
    })


@app.route("/api/assessments/<int:asm_id>/attachments/<int:att_id>", methods=["DELETE"])
@login_required
def api_delete_attachment(asm_id, att_id):
    asm = _load_assessment_or_abort(asm_id)
    _require_editable(asm)
    _validate_csrf_api()

    with get_db() as conn:
        att = conn.execute(
            "SELECT id, safeguard_id, filename FROM attachments "
            "WHERE id = ? AND assessment_id = ?",
            (att_id, asm_id),
        ).fetchone()
        if not att:
            abort(404)
        conn.execute("DELETE FROM attachments WHERE id = ?", (att_id,))
        _log(conn, asm_id, "attachment_deleted",
             sg_id=att["safeguard_id"], old=att["filename"])
        conn.commit()

    path = disk_path(att_id, att["filename"])
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass

    return jsonify({"ok": True})


@app.route("/api/attachments/<int:att_id>")
@login_required
def api_get_attachment(att_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT a.id, a.filename, a.mime_type, a.assessment_id, s.org_id "
            "FROM attachments a JOIN assessments s ON s.id = a.assessment_id "
            "WHERE a.id = ?",
            (att_id,),
        ).fetchone()
    if not row:
        abort(404)
    if row["org_id"] != session.get("org_id"):
        abort(403)

    path = disk_path(att_id, row["filename"])
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype=row["mime_type"],
                     download_name=row["filename"], as_attachment=False)


@app.route("/api/assessments/<int:asm_id>/export")
@login_required
def api_export_csv(asm_id):
    asm = _load_assessment_or_abort(asm_id)

    with get_db() as conn:
        rows = conn.execute(
            "SELECT safeguard_id, status, updated_at FROM assessment_safeguards "
            "WHERE assessment_id = ?", (asm_id,),
        ).fetchall()
    status_by_sg = {r["safeguard_id"]: dict(r) for r in rows}

    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Control", "Safeguard", "Title", "Function", "Asset Class",
                "IG1", "IG2", "IG3", "Status", "Updated At"])
    for ctrl in CIS_DATA["controls"]:
        for sg in ctrl["safeguards"]:
            parts = sg["id"].split(".")
            sg_display = f"C{int(parts[0]):02d}-{int(parts[1]):02d}"
            s = status_by_sg.get(sg["id"], {})
            w.writerow([
                f"C{ctrl['id']:02d}",
                sg_display,
                sg["title"],
                sg["function"],
                sg["asset_class"],
                "Y" if sg["ig1"] else "",
                "Y" if sg["ig2"] else "",
                "Y" if sg["ig3"] else "",
                s.get("status", "not_assessed"),
                s.get("updated_at", "") or "",
            ])

    safe_name = re.sub(r"[^\w\-]", "_", asm["name"])[:80] or "assessment"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=\"{safe_name}.csv\""},
    )


if __name__ == "__main__":
    init_db()
    app.run(
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        host="0.0.0.0",
        port=5000,
    )
