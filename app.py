"""Campus Connect - Integrated Student Enrollment and Information System
Flask REST API + SQLite backend (Laboratory 3 course API + Laboratory 4 portal).

Run locally (Windows): double-click run.bat
Run locally (any OS):  python app.py
API base URL:          http://127.0.0.1:5000/api
"""

import os
import sqlite3
from datetime import date, timedelta

from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# On Render you can point DATABASE_PATH at a mounted persistent disk.
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "database.db"))

VALID_STATUSES = ("Pending", "Approved", "Rejected", "Cancelled")
STUDENT_FIELDS = ("student_id", "first_name", "last_name", "email", "program", "year_level", "contact_number")
COURSE_FIELDS = ("course_code", "course_name", "department", "units", "slots")

app = Flask(__name__)
# Lab setting: the Base44 frontend is on a different origin than Flask.
# In production replace "*" with your frontend URL, e.g.
# CORS(app, origins=["https://your-app.base44.app"])
CORS(app)

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    program TEXT NOT NULL,
    year_level INTEGER NOT NULL DEFAULT 1,
    contact_number TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL UNIQUE,
    course_name TEXT NOT NULL,
    department TEXT NOT NULL,
    units INTEGER NOT NULL DEFAULT 3,
    slots INTEGER NOT NULL DEFAULT 30,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    enrollment_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    status TEXT NOT NULL DEFAULT 'Pending',
    UNIQUE (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES students (id),
    FOREIGN KEY (course_id) REFERENCES courses (id)
);

CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT 'Office of the Registrar',
    date_posted TEXT NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'staff',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SEED_STUDENTS = [
    ("2024-0001", "Maria", "Santos", "maria.santos@campusconnect.edu", "BS Computer Science", 3, "0917 555 0101"),
    ("2024-0002", "Juan", "Dela Cruz", "juan.delacruz@campusconnect.edu", "BS Information Technology", 2, "0917 555 0102"),
    ("2024-0003", "Ana", "Reyes", "ana.reyes@campusconnect.edu", "BS Information Systems", 4, "0917 555 0103"),
    ("2024-0004", "Mark", "Villanueva", "mark.villanueva@campusconnect.edu", "BS Computer Engineering", 1, "0917 555 0104"),
    ("2024-0005", "Liza", "Mendoza", "liza.mendoza@campusconnect.edu", "BS Accountancy", 2, "0917 555 0105"),
    ("2024-0006", "Paolo", "Garcia", "paolo.garcia@campusconnect.edu", "BS Civil Engineering", 3, "0917 555 0106"),
]

SEED_COURSES = [
    ("CS 101", "Introduction to Computing", "College of Computer Studies", 3, 30),
    ("CS 102", "Programming Fundamentals", "College of Computer Studies", 3, 28),
    ("IT 201", "Web Systems and Technologies", "College of Computer Studies", 3, 25),
    ("IS 210", "Systems Integration and Architecture", "College of Computer Studies", 3, 20),
    ("GE 105", "Mathematics in the Modern World", "College of Arts and Sciences", 3, 40),
    ("BA 120", "Principles of Management", "College of Business", 3, 35),
]

SEED_ENROLLMENTS = [
    (1, 1, "Approved"),
    (1, 3, "Pending"),
    (2, 2, "Approved"),
    (3, 4, "Approved"),
    (4, 1, "Pending"),
    (5, 6, "Rejected"),
    (6, 5, "Cancelled"),
]

SEED_ANNOUNCEMENTS = [
    (
        "Enrollment for the 2nd semester is now open",
        "Students may submit enrollment requests through the Campus Connect portal until the end of the month. "
        "Requests are reviewed by the Office of the Registrar and appear as Pending until approved.",
        "Office of the Registrar",
    ),
    (
        "Systems Integration laboratory schedule",
        "The Laboratory 3 and Laboratory 4 consultation sessions will be held every Tuesday and Thursday, "
        "1:00 PM to 3:00 PM at the Computer Studies Laboratory.",
        "College of Computer Studies",
    ),
]


def init_db():
    """Create the tables and add sample fictional records on first run."""
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA_SQL)
    if db.execute("SELECT COUNT(*) AS total FROM students").fetchone()["total"] == 0:
        db.executemany(
            "INSERT INTO students (student_id, first_name, last_name, email, program, year_level, contact_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            SEED_STUDENTS,
        )
        db.executemany(
            "INSERT INTO courses (course_code, course_name, department, units, slots) VALUES (?, ?, ?, ?, ?)",
            SEED_COURSES,
        )
        db.executemany(
            "INSERT INTO enrollments (student_id, course_id, status) VALUES (?, ?, ?)",
            SEED_ENROLLMENTS,
        )
        db.executemany(
            "INSERT INTO announcements (title, content, author) VALUES (?, ?, ?)",
            SEED_ANNOUNCEMENTS,
        )
        # Demo users row. Portal sign-in is handled by the hosted frontend in this
        # laboratory; replace this with real hashing (werkzeug) when you need it.
        db.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("registrar", "demo-only-not-a-real-hash", "admin"),
        )
    db.commit()
    db.close()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def rows_to_list(rows):
    return [dict(row) for row in rows]


def error(message, status=400):
    return jsonify({"error": message}), status


def payload():
    return request.get_json(silent=True) or {}


# ---------------------------------------------------------------------------
# Health + dashboard statistics
# ---------------------------------------------------------------------------
@app.route("/api/health")
def health():
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS total FROM students").fetchone()["total"]
    return jsonify(
        {
            "status": "ok",
            "service": "Campus Connect Flask API",
            "database": "connected",
            "database_path": DATABASE_PATH,
            "students": total,
        }
    )


@app.route("/api/stats")
def stats():
    db = get_db()

    def count(sql):
        return db.execute(sql).fetchone()["total"]

    available_sql = (
        "SELECT COUNT(*) AS total FROM courses c WHERE "
        "(SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.id AND e.status != 'Cancelled') < c.slots"
    )

    totals = {
        "students": count("SELECT COUNT(*) AS total FROM students"),
        "courses": count("SELECT COUNT(*) AS total FROM courses"),
        "enrollments": count("SELECT COUNT(*) AS total FROM enrollments"),
        "available_courses": count(available_sql),
    }

    status_totals = {"pending": 0, "approved": 0, "rejected": 0, "cancelled": 0}
    for row in db.execute("SELECT status, COUNT(*) AS total FROM enrollments GROUP BY status"):
        key = str(row["status"]).lower()
        if key in status_totals:
            status_totals[key] = row["total"]

    per_day = {}
    for row in db.execute("SELECT enrollment_date, COUNT(*) AS total FROM enrollments GROUP BY enrollment_date"):
        per_day[row["enrollment_date"]] = row["total"]

    today = date.today()
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    by_day = [{"date": day.isoformat(), "count": per_day.get(day.isoformat(), 0)} for day in days]

    recent_enrollments = rows_to_list(
        db.execute(ENROLLMENT_SELECT + " ORDER BY e.id DESC LIMIT 5").fetchall()
    )
    recent_announcements = rows_to_list(
        db.execute(
            "SELECT id AS announcement_id, title, content, author, date_posted "
            "FROM announcements ORDER BY date_posted DESC, id DESC LIMIT 3"
        ).fetchall()
    )

    return jsonify(
        {
            "totals": totals,
            "enrollment_status": status_totals,
            "enrollments_by_day": by_day,
            "recent_enrollments": recent_enrollments,
            "recent_announcements": recent_announcements,
        }
    )


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
@app.route("/api/students", methods=["GET"])
def list_students():
    db = get_db()
    term = request.args.get("q", "").strip()
    sql = "SELECT * FROM students"
    params = []
    if term:
        like = "%" + term + "%"
        sql += (
            " WHERE student_id LIKE ? OR first_name LIKE ? OR last_name LIKE ? "
            "OR email LIKE ? OR program LIKE ?"
        )
        params = [like] * 5
    sql += " ORDER BY last_name ASC, first_name ASC"
    return jsonify(rows_to_list(db.execute(sql, params).fetchall()))


@app.route("/api/students/<int:student_pk>", methods=["GET"])
def get_student(student_pk):
    row = get_db().execute("SELECT * FROM students WHERE id = ?", (student_pk,)).fetchone()
    if row is None:
        return error("Student not found.", 404)
    return jsonify(dict(row))


@app.route("/api/students", methods=["POST"])
def create_student():
    data = payload()
    for field in ("student_id", "first_name", "last_name", "email"):
        if not str(data.get(field, "")).strip():
            return error("student_id, first_name, last_name and email are required.")

    try:
        year_level = int(data.get("year_level") or 1)
    except (TypeError, ValueError):
        return error("year_level must be a number.")

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO students (student_id, first_name, last_name, email, program, year_level, contact_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(data["student_id"]).strip(),
                str(data["first_name"]).strip(),
                str(data["last_name"]).strip(),
                str(data["email"]).strip(),
                str(data.get("program") or "Undeclared").strip(),
                year_level,
                str(data.get("contact_number") or "").strip(),
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("A student with that student ID or email already exists.", 409)

    row = db.execute("SELECT * FROM students WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/students/<int:student_pk>", methods=["PUT"])
def update_student(student_pk):
    data = payload()
    db = get_db()
    existing = db.execute("SELECT * FROM students WHERE id = ?", (student_pk,)).fetchone()
    if existing is None:
        return error("Student not found.", 404)

    merged = dict(existing)
    for field in STUDENT_FIELDS:
        if field in data and str(data[field]).strip() != "":
            merged[field] = data[field]

    try:
        merged["year_level"] = int(merged["year_level"])
    except (TypeError, ValueError):
        return error("year_level must be a number.")

    try:
        db.execute(
            "UPDATE students SET student_id = ?, first_name = ?, last_name = ?, email = ?, "
            "program = ?, year_level = ?, contact_number = ? WHERE id = ?",
            (
                merged["student_id"],
                merged["first_name"],
                merged["last_name"],
                merged["email"],
                merged["program"],
                merged["year_level"],
                merged["contact_number"],
                student_pk,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("A student with that student ID or email already exists.", 409)

    row = db.execute("SELECT * FROM students WHERE id = ?", (student_pk,)).fetchone()
    return jsonify(dict(row))


@app.route("/api/students/<int:student_pk>", methods=["DELETE"])
def delete_student(student_pk):
    db = get_db()
    row = db.execute("SELECT id FROM students WHERE id = ?", (student_pk,)).fetchone()
    if row is None:
        return error("Student not found.", 404)

    linked = db.execute(
        "SELECT COUNT(*) AS total FROM enrollments WHERE student_id = ?", (student_pk,)
    ).fetchone()["total"]
    if linked:
        return error(
            "This student still has " + str(linked) + " enrollment record(s). Delete those first.",
            409,
        )

    db.execute("DELETE FROM students WHERE id = ?", (student_pk,))
    db.commit()
    return jsonify({"success": True, "deleted": student_pk})


# ---------------------------------------------------------------------------
# Courses (Laboratory 3 API)
# ---------------------------------------------------------------------------
COURSE_SELECT = (
    "SELECT c.*, (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.id "
    "AND e.status != 'Cancelled') AS enrolled FROM courses c"
)


@app.route("/api/courses", methods=["GET"])
def list_courses():
    db = get_db()
    term = request.args.get("q", "").strip()
    sql = COURSE_SELECT
    params = []
    if term:
        like = "%" + term + "%"
        sql += " WHERE c.course_code LIKE ? OR c.course_name LIKE ? OR c.department LIKE ?"
        params = [like] * 3
    sql += " ORDER BY c.course_code ASC"
    return jsonify(rows_to_list(db.execute(sql, params).fetchall()))


@app.route("/api/courses/<int:course_pk>", methods=["GET"])
def get_course(course_pk):
    row = get_db().execute(COURSE_SELECT + " WHERE c.id = ?", (course_pk,)).fetchone()
    if row is None:
        return error("Course not found.", 404)
    return jsonify(dict(row))


@app.route("/api/courses", methods=["POST"])
def create_course():
    data = payload()
    for field in ("course_code", "course_name", "department"):
        if not str(data.get(field, "")).strip():
            return error("course_code, course_name and department are required.")

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO courses (course_code, course_name, department, units, slots) VALUES (?, ?, ?, ?, ?)",
            (
                str(data["course_code"]).strip().upper(),
                str(data["course_name"]).strip(),
                str(data["department"]).strip(),
                int(data.get("units") or 3),
                int(data.get("slots") or 30),
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("A course with that course code already exists.", 409)
    except (TypeError, ValueError):
        return error("units and slots must be numbers.")

    row = db.execute(COURSE_SELECT + " WHERE c.id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/courses/<int:course_pk>", methods=["PUT"])
def update_course(course_pk):
    data = payload()
    db = get_db()
    existing = db.execute("SELECT * FROM courses WHERE id = ?", (course_pk,)).fetchone()
    if existing is None:
        return error("Course not found.", 404)

    merged = dict(existing)
    for field in COURSE_FIELDS:
        if field in data and str(data[field]).strip() != "":
            merged[field] = data[field]

    try:
        merged["units"] = int(merged["units"])
        merged["slots"] = int(merged["slots"])
    except (TypeError, ValueError):
        return error("units and slots must be numbers.")

    try:
        db.execute(
            "UPDATE courses SET course_code = ?, course_name = ?, department = ?, units = ?, slots = ? "
            "WHERE id = ?",
            (
                str(merged["course_code"]).upper(),
                merged["course_name"],
                merged["department"],
                merged["units"],
                merged["slots"],
                course_pk,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("A course with that course code already exists.", 409)

    row = db.execute(COURSE_SELECT + " WHERE c.id = ?", (course_pk,)).fetchone()
    return jsonify(dict(row))


@app.route("/api/courses/<int:course_pk>", methods=["DELETE"])
def delete_course(course_pk):
    db = get_db()
    row = db.execute("SELECT id FROM courses WHERE id = ?", (course_pk,)).fetchone()
    if row is None:
        return error("Course not found.", 404)

    linked = db.execute(
        "SELECT COUNT(*) AS total FROM enrollments WHERE course_id = ?", (course_pk,)
    ).fetchone()["total"]
    if linked:
        return error(
            "This course still has " + str(linked) + " enrollment record(s). Delete those first.",
            409,
        )

    db.execute("DELETE FROM courses WHERE id = ?", (course_pk,))
    db.commit()
    return jsonify({"success": True, "deleted": course_pk})


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------
ENROLLMENT_SELECT = (
    "SELECT e.id AS enrollment_id, e.student_id, e.course_id, e.enrollment_date, e.status, "
    "s.student_id AS student_number, s.first_name || ' ' || s.last_name AS student_name, "
    "c.course_code, c.course_name, c.units "
    "FROM enrollments e "
    "JOIN students s ON s.id = e.student_id "
    "JOIN courses c ON c.id = e.course_id"
)


def fetch_enrollment(db, enrollment_id):
    return db.execute(ENROLLMENT_SELECT + " WHERE e.id = ?", (enrollment_id,)).fetchone()


@app.route("/api/enrollments", methods=["GET"])
def list_enrollments():
    db = get_db()
    term = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    student_pk = request.args.get("student_id", "").strip()

    clauses = []
    params = []
    if term:
        like = "%" + term + "%"
        clauses.append(
            "(s.first_name LIKE ? OR s.last_name LIKE ? OR s.student_id LIKE ? "
            "OR c.course_code LIKE ? OR c.course_name LIKE ?)"
        )
        params.extend([like] * 5)
    if status:
        clauses.append("e.status = ?")
        params.append(status)
    if student_pk:
        clauses.append("e.student_id = ?")
        params.append(student_pk)

    sql = ENROLLMENT_SELECT
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY e.id DESC"
    return jsonify(rows_to_list(db.execute(sql, params).fetchall()))


@app.route("/api/enrollments/<int:enrollment_id>", methods=["GET"])
def get_enrollment(enrollment_id):
    row = fetch_enrollment(get_db(), enrollment_id)
    if row is None:
        return error("Enrollment not found.", 404)
    return jsonify(dict(row))


@app.route("/api/enrollments", methods=["POST"])
def create_enrollment():
    data = payload()
    try:
        student_pk = int(data.get("student_id"))
        course_pk = int(data.get("course_id"))
    except (TypeError, ValueError):
        return error("student_id and course_id are required numbers.")

    db = get_db()
    if db.execute("SELECT id FROM students WHERE id = ?", (student_pk,)).fetchone() is None:
        return error("Student not found.", 404)
    if db.execute("SELECT id FROM courses WHERE id = ?", (course_pk,)).fetchone() is None:
        return error("Course not found.", 404)

    duplicate = db.execute(
        "SELECT id FROM enrollments WHERE student_id = ? AND course_id = ?",
        (student_pk, course_pk),
    ).fetchone()
    if duplicate is not None:
        return error("This student is already enrolled in that course.", 409)

    try:
        cursor = db.execute(
            "INSERT INTO enrollments (student_id, course_id, status) VALUES (?, ?, ?)",
            (student_pk, course_pk, "Pending"),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("This student is already enrolled in that course.", 409)

    return jsonify(dict(fetch_enrollment(db, cursor.lastrowid))), 201


@app.route("/api/enrollments/<int:enrollment_id>", methods=["PUT"])
def update_enrollment(enrollment_id):
    data = payload()
    db = get_db()
    existing = fetch_enrollment(db, enrollment_id)
    if existing is None:
        return error("Enrollment not found.", 404)

    status = str(data.get("status") or existing["status"]).strip().title()
    if status not in VALID_STATUSES:
        return error("status must be one of: Pending, Approved, Rejected, Cancelled.")

    db.execute("UPDATE enrollments SET status = ? WHERE id = ?", (status, enrollment_id))
    db.commit()
    return jsonify(dict(fetch_enrollment(db, enrollment_id)))


@app.route("/api/enrollments/<int:enrollment_id>", methods=["DELETE"])
def delete_enrollment(enrollment_id):
    db = get_db()
    if db.execute("SELECT id FROM enrollments WHERE id = ?", (enrollment_id,)).fetchone() is None:
        return error("Enrollment not found.", 404)
    db.execute("DELETE FROM enrollments WHERE id = ?", (enrollment_id,))
    db.commit()
    return jsonify({"success": True, "deleted": enrollment_id})


# ---------------------------------------------------------------------------
# Announcements (Laboratory 4 portal feature)
# ---------------------------------------------------------------------------
ANNOUNCEMENT_SELECT = (
    "SELECT id AS announcement_id, title, content, author, date_posted FROM announcements"
)


@app.route("/api/announcements", methods=["GET"])
def list_announcements():
    rows = get_db().execute(
        ANNOUNCEMENT_SELECT + " ORDER BY date_posted DESC, id DESC"
    ).fetchall()
    return jsonify(rows_to_list(rows))


@app.route("/api/announcements/<int:announcement_id>", methods=["GET"])
def get_announcement(announcement_id):
    row = get_db().execute(
        ANNOUNCEMENT_SELECT + " WHERE id = ?", (announcement_id,)
    ).fetchone()
    if row is None:
        return error("Announcement not found.", 404)
    return jsonify(dict(row))


@app.route("/api/announcements", methods=["POST"])
def create_announcement():
    data = payload()
    if not str(data.get("title", "")).strip() or not str(data.get("content", "")).strip():
        return error("title and content are required.")

    db = get_db()
    cursor = db.execute(
        "INSERT INTO announcements (title, content, author) VALUES (?, ?, ?)",
        (
            str(data["title"]).strip(),
            str(data["content"]).strip(),
            str(data.get("author") or "Office of the Registrar").strip(),
        ),
    )
    db.commit()
    row = db.execute(
        ANNOUNCEMENT_SELECT + " WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/announcements/<int:announcement_id>", methods=["PUT"])
def update_announcement(announcement_id):
    data = payload()
    db = get_db()
    existing = db.execute(
        "SELECT * FROM announcements WHERE id = ?", (announcement_id,)
    ).fetchone()
    if existing is None:
        return error("Announcement not found.", 404)

    db.execute(
        "UPDATE announcements SET title = ?, content = ?, author = ? WHERE id = ?",
        (
            str(data.get("title") or existing["title"]).strip(),
            str(data.get("content") or existing["content"]).strip(),
            str(data.get("author") or existing["author"]).strip(),
            announcement_id,
        ),
    )
    db.commit()
    row = db.execute(
        ANNOUNCEMENT_SELECT + " WHERE id = ?", (announcement_id,)
    ).fetchone()
    return jsonify(dict(row))


@app.route("/api/announcements/<int:announcement_id>", methods=["DELETE"])
def delete_announcement(announcement_id):
    db = get_db()
    if db.execute("SELECT id FROM announcements WHERE id = ?", (announcement_id,)).fetchone() is None:
        return error("Announcement not found.", 404)
    db.execute("DELETE FROM announcements WHERE id = ?", (announcement_id,))
    db.commit()
    return jsonify({"success": True, "deleted": announcement_id})


# ---------------------------------------------------------------------------
# Server-rendered pages (used when you open Flask directly in a browser)
# ---------------------------------------------------------------------------
@app.route("/")
def page_index():
    return render_template("index.html")


@app.route("/students")
def page_students():
    return render_template("students.html")


@app.route("/courses")
def page_courses():
    return render_template("courses.html")


@app.route("/enrollment")
def page_enrollment():
    return render_template("enrollment.html")


@app.route("/announcements")
def page_announcements():
    return render_template("announcements.html")


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(500)
def server_error(_error):
    return jsonify({"error": "The server encountered an unexpected error."}), 500


# Create the database automatically the first time the app starts.
init_db()

if __name__ == "__main__":
    print("Campus Connect Flask API running on http://127.0.0.1:5000")
    print("API base URL: http://127.0.0.1:5000/api")
    print("SQLite database:", DATABASE_PATH)
    app.run(host="127.0.0.1", port=5000, debug=True)
