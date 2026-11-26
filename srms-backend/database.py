"""SQLite storage layer: connection helper and schema creation."""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get(
    "SRMS_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "srms.db"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS admins (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teachers (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id            TEXT PRIMARY KEY,
    roll          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    cls           TEXT NOT NULL,
    dob           TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subjects (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    max_marks  INTEGER NOT NULL CHECK (max_marks > 0),
    teacher_id TEXT REFERENCES teachers(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS marks (
    student_id TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    marks      INTEGER,
    PRIMARY KEY (student_id, subject_id)
);

CREATE TABLE IF NOT EXISTS result_status (
    subject_id TEXT PRIMARY KEY REFERENCES subjects(id) ON DELETE CASCADE,
    status     TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'submitted', 'approved'))
);

CREATE INDEX IF NOT EXISTS idx_marks_subject ON marks(subject_id);
CREATE INDEX IF NOT EXISTS idx_subjects_teacher ON subjects(teacher_id);
"""


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    """Transaction helper: commits on success, rolls back on error."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.executescript(SCHEMA)


def next_id(conn, table, prefix):
    """Next sequential id, continuing the existing pattern (S107, SUB7, ...).

    Ids are never reused: marks rows reference them, and reusing one would
    silently attach an old subject's marks to a brand new subject.
    """
    highest = 0
    for row in conn.execute(f"SELECT id FROM {table}"):
        suffix = row["id"][len(prefix):]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{prefix}{highest + 1}"


def insert_student(conn, *, roll, name, cls, dob, password):
    """Create a student row. Raises sqlite3.IntegrityError on a duplicate roll.

    Shared by admin roster management and student self-registration so both
    paths apply identical rules.
    """
    from security import hash_password  # imported here to avoid a circular import

    roll = roll.strip().upper()
    conn.execute(
        "INSERT INTO students (id, roll, name, cls, dob, password_hash)"
        " VALUES (?,?,?,?,?,?)",
        (
            next_id(conn, "students", "S"),
            roll,
            name.strip(),
            cls.strip(),
            dob,
            hash_password(password),
        ),
    )