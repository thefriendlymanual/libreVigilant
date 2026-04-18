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

        if conn.execute("SELECT 1 FROM schema_migrations WHERE version='0001'").fetchone():
            return  # Already fully migrated.

        # -------------------------------------------------------------------
        # Detect and snapshot the old 3-table single-assessment schema.
        # Old `assessments` table holds per-safeguard status rows (PK: safeguard_id).
        # New `assessments` table holds named assessment records (PK: id).
        # -------------------------------------------------------------------
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

        # -------------------------------------------------------------------
        # Create the 7-table schema.
        # -------------------------------------------------------------------
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

        # -------------------------------------------------------------------
        # Migrate old data → default org + "Initial Assessment".
        # -------------------------------------------------------------------
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
# Root redirect
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    with get_db() as conn:
        has_users = conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    if not has_users:
        return redirect(url_for("setup"))
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("org_assessments", org_id=session["org_id"]))


# ---------------------------------------------------------------------------
# Assessment list — placeholder until Phase 2
# ---------------------------------------------------------------------------

@app.route("/orgs/<int:org_id>/assessments")
@login_required
def org_assessments(org_id):
    if org_id != session.get("org_id"):
        abort(403)
    with get_db() as conn:
        org = conn.execute("SELECT name FROM orgs WHERE id = ?", (org_id,)).fetchone()
    if not org:
        abort(404)
    return render_template("placeholder.html", org_name=org["name"])


if __name__ == "__main__":
    init_db()
    app.run(
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        host="0.0.0.0",
        port=5000,
    )
