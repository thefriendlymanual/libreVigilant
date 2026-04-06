import json
import mimetypes
import os
import sqlite3
from datetime import datetime

from flask import Flask, Response, abort, jsonify, render_template, request, send_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

DB_PATH = os.path.join(os.path.dirname(__file__), "librevig.db")
DATA_PATH = os.path.join(os.path.dirname(__file__), "cis_data.json")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".pptx",
    ".txt", ".csv", ".rtf",
}

with open(DATA_PATH) as f:
    CIS_DATA = json.load(f)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def disk_path(att_id, filename):
    ext = os.path.splitext(filename)[1]
    return os.path.join(UPLOAD_DIR, f"{att_id}{ext}")


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assessments (
                safeguard_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'not_assessed',
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                safeguard_id TEXT NOT NULL,
                body         TEXT NOT NULL,
                created_at   TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                safeguard_id TEXT NOT NULL,
                filename     TEXT NOT NULL,
                mime_type    TEXT NOT NULL,
                size         INTEGER NOT NULL,
                uploaded_at  TEXT NOT NULL
            )
        """)
        # One-time migration: move existing notes text into the new table
        rows = conn.execute(
            "SELECT safeguard_id, notes, updated_at FROM assessments WHERE notes != ''"
        ).fetchall()
        for row in rows:
            created = row["updated_at"] or datetime.now().strftime("%Y-%m-%d %H:%M")
            conn.execute(
                "INSERT INTO notes (safeguard_id, body, created_at) VALUES (?, ?, ?)",
                (row["safeguard_id"], row["notes"], created),
            )
            conn.execute(
                "UPDATE assessments SET notes = '' WHERE safeguard_id = ?",
                (row["safeguard_id"],),
            )
        conn.commit()


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large (max 50 MB)"}), 413


@app.route("/")
def index():
    return render_template("index.html", controls=CIS_DATA["controls"])


@app.route("/api/assessments")
def get_assessments():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM assessments").fetchall()
        note_rows = conn.execute(
            "SELECT id, safeguard_id, body, created_at FROM notes ORDER BY id ASC"
        ).fetchall()
        att_rows = conn.execute(
            "SELECT id, safeguard_id, filename, size, uploaded_at FROM attachments ORDER BY id ASC"
        ).fetchall()

    notes_by_sg = {}
    for n in note_rows:
        notes_by_sg.setdefault(n["safeguard_id"], []).append({
            "id": n["id"],
            "body": n["body"],
            "created_at": n["created_at"],
        })

    atts_by_sg = {}
    for a in att_rows:
        atts_by_sg.setdefault(a["safeguard_id"], []).append({
            "id": a["id"],
            "filename": a["filename"],
            "size": a["size"],
            "uploaded_at": a["uploaded_at"],
        })

    return jsonify({
        row["safeguard_id"]: {
            "status": row["status"],
            "updated_at": row["updated_at"],
            "notes": notes_by_sg.get(row["safeguard_id"], []),
            "attachments": atts_by_sg.get(row["safeguard_id"], []),
        }
        for row in rows
    })


@app.route("/api/assessments/<safeguard_id>", methods=["POST"])
def update_assessment(safeguard_id):
    data = request.get_json()
    status = data.get("status", "not_assessed")
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    valid_statuses = {"not_assessed", "not_implemented", "partial", "implemented", "not_applicable"}
    if status not in valid_statuses:
        return jsonify({"error": "Invalid status"}), 400

    with get_db() as conn:
        conn.execute(
            "INSERT INTO assessments (safeguard_id, status, notes, updated_at) VALUES (?, ?, '', ?) "
            "ON CONFLICT(safeguard_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at",
            (safeguard_id, status, updated_at),
        )
        conn.commit()
    return jsonify({"ok": True, "updated_at": updated_at})


@app.route("/api/assessments/<safeguard_id>/notes", methods=["POST"])
def add_note(safeguard_id):
    data = request.get_json()
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Note body is required"}), 400

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO notes (safeguard_id, body, created_at) VALUES (?, ?, ?)",
            (safeguard_id, body, created_at),
        )
        note_id = cur.lastrowid
        conn.commit()

    return jsonify({"id": note_id, "body": body, "created_at": created_at}), 201


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    with get_db() as conn:
        result = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
    if result.rowcount == 0:
        return jsonify({"error": "Note not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/assessments/<safeguard_id>/attachments", methods=["POST"])
def upload_attachment(safeguard_id):
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "No file selected"}), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"File type '{ext}' not allowed"}), 400

    mime = f.content_type or mimetypes.guess_type(f.filename)[0] or "application/octet-stream"
    data = f.read()
    size = len(data)
    uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO attachments (safeguard_id, filename, mime_type, size, uploaded_at) VALUES (?, ?, ?, ?, ?)",
            (safeguard_id, f.filename, mime, size, uploaded_at),
        )
        att_id = cur.lastrowid
        conn.commit()

    path = disk_path(att_id, f.filename)
    with open(path, "wb") as out:
        out.write(data)

    return jsonify({"id": att_id, "filename": f.filename, "size": size, "uploaded_at": uploaded_at}), 201


@app.route("/api/attachments/<int:attachment_id>")
def serve_attachment(attachment_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT filename, mime_type FROM attachments WHERE id = ?", (attachment_id,)
        ).fetchone()
    if not row:
        abort(404)

    path = disk_path(attachment_id, row["filename"])
    if not os.path.exists(path):
        abort(404)

    return send_file(path, download_name=row["filename"], mimetype=row["mime_type"], as_attachment=False)


@app.route("/api/attachments/<int:attachment_id>", methods=["DELETE"])
def delete_attachment(attachment_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT filename FROM attachments WHERE id = ?", (attachment_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "Attachment not found"}), 404
        conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        conn.commit()

    path = disk_path(attachment_id, row["filename"])
    try:
        os.remove(path)
    except FileNotFoundError:
        pass

    return jsonify({"ok": True})


@app.route("/api/export")
def export_csv():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM assessments").fetchall()
        note_rows = conn.execute(
            "SELECT safeguard_id, body FROM notes ORDER BY id ASC"
        ).fetchall()
        att_rows = conn.execute(
            "SELECT safeguard_id, filename FROM attachments ORDER BY id ASC"
        ).fetchall()

    assessments = {row["safeguard_id"]: row for row in rows}

    notes_by_sg = {}
    for n in note_rows:
        notes_by_sg.setdefault(n["safeguard_id"], []).append(n["body"])

    atts_by_sg = {}
    for a in att_rows:
        atts_by_sg.setdefault(a["safeguard_id"], []).append(a["filename"])

    lines = ["CIS Control,Safeguard ID,Title,Asset Class,Function,IG1,IG2,IG3,Status,Notes,Attachments,Last Updated"]
    for control in CIS_DATA["controls"]:
        for sg in control["safeguards"]:
            a = assessments.get(sg["id"])
            status = a["status"] if a else "not_assessed"
            bodies = notes_by_sg.get(sg["id"], [])
            notes = " | ".join(bodies).replace('"', '""')
            filenames = atts_by_sg.get(sg["id"], [])
            att_str = ", ".join(filenames).replace('"', '""')
            updated = a["updated_at"] if a else ""
            ig1 = "Yes" if sg["ig1"] else "No"
            ig2 = "Yes" if sg["ig2"] else "No"
            ig3 = "Yes" if sg["ig3"] else "No"
            title = sg["title"].replace('"', '""')
            ctrl_code = f'C{control["id"]:02d}'
            parts = sg["id"].split(".")
            sg_code = f'C{int(parts[0]):02d}-{int(parts[1]):02d}'
            lines.append(f'{ctrl_code},{sg_code},"{title}",{sg["asset_class"]},{sg["function"]},{ig1},{ig2},{ig3},{status},"{notes}","{att_str}",{updated}')

    csv_content = "\n".join(lines)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=cis_assessment.csv"},
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
