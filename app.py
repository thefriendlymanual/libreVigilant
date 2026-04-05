import json
import os
import sqlite3
from datetime import datetime

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "csat.db")
DATA_PATH = os.path.join(os.path.dirname(__file__), "cis_data.json")

with open(DATA_PATH) as f:
    CIS_DATA = json.load(f)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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

    notes_by_sg = {}
    for n in note_rows:
        notes_by_sg.setdefault(n["safeguard_id"], []).append({
            "id": n["id"],
            "body": n["body"],
            "created_at": n["created_at"],
        })

    return jsonify({
        row["safeguard_id"]: {
            "status": row["status"],
            "updated_at": row["updated_at"],
            "notes": notes_by_sg.get(row["safeguard_id"], []),
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


@app.route("/api/export")
def export_csv():
    from flask import Response

    with get_db() as conn:
        rows = conn.execute("SELECT * FROM assessments").fetchall()
        note_rows = conn.execute(
            "SELECT safeguard_id, body FROM notes ORDER BY id ASC"
        ).fetchall()

    assessments = {row["safeguard_id"]: row for row in rows}

    notes_by_sg = {}
    for n in note_rows:
        notes_by_sg.setdefault(n["safeguard_id"], []).append(n["body"])

    lines = ["CIS Control,Safeguard ID,Title,Asset Class,Function,IG1,IG2,IG3,Status,Notes,Last Updated"]
    for control in CIS_DATA["controls"]:
        for sg in control["safeguards"]:
            a = assessments.get(sg["id"])
            status = a["status"] if a else "not_assessed"
            bodies = notes_by_sg.get(sg["id"], [])
            notes = " | ".join(bodies).replace('"', '""')
            updated = a["updated_at"] if a else ""
            ig1 = "Yes" if sg["ig1"] else "No"
            ig2 = "Yes" if sg["ig2"] else "No"
            ig3 = "Yes" if sg["ig3"] else "No"
            title = sg["title"].replace('"', '""')
            lines.append(f'{control["id"]},{sg["id"]},"{title}",{sg["asset_class"]},{sg["function"]},{ig1},{ig2},{ig3},{status},"{notes}",{updated}')

    csv_content = "\n".join(lines)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=cis_assessment.csv"},
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
