"""Teacher-only endpoints: marks entry and class performance."""
from fastapi import APIRouter, Depends, HTTPException

from database import db
from grading import grade_for, subject_marks, subject_stats
from schemas import MarksSaveIn
from security import require_teacher

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


def _own_subject(conn, subject_id, teacher_id):
    row = conn.execute(
        "SELECT id, name, max_marks FROM subjects WHERE id = ? AND teacher_id = ?",
        (subject_id, teacher_id),
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Subject not found or not assigned to you.")
    return row


@router.get("/subjects")
def my_subjects(user: dict = Depends(require_teacher)):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.name, s.max_marks, COALESCE(r.status, 'draft') AS status
            FROM subjects s
            LEFT JOIN result_status r ON r.subject_id = s.id
            WHERE s.teacher_id = ?
            ORDER BY s.id
            """,
            (user["id"],),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/marks")
def get_marks(subject_id: str, user: dict = Depends(require_teacher)):
    with db() as conn:
        subject = _own_subject(conn, subject_id, user["id"])
        rows = conn.execute(
            """
            SELECT s.id, s.roll, s.name, m.marks
            FROM students s
            LEFT JOIN marks m ON m.student_id = s.id AND m.subject_id = ?
            ORDER BY s.roll
            """,
            (subject_id,),
        ).fetchall()
        status_row = conn.execute(
            "SELECT status FROM result_status WHERE subject_id = ?", (subject_id,)
        ).fetchone()

    status = status_row["status"] if status_row else "draft"
    entries = []
    for row in rows:
        marks = row["marks"]
        entries.append(
            {
                "student_id": row["id"],
                "roll": row["roll"],
                "name": row["name"],
                "marks": marks,
                "grade": grade_for(marks / subject["max_marks"] * 100)["letter"]
                if marks is not None
                else None,
            }
        )
    return {
        "subject": {
            "id": subject["id"],
            "name": subject["name"],
            "max": subject["max_marks"],
        },
        "status": status,
        "locked": status != "draft",
        "entries": entries,
    }


@router.put("/marks")
def save_marks(payload: MarksSaveIn, user: dict = Depends(require_teacher)):
    with db() as conn:
        subject = _own_subject(conn, payload.subject_id, user["id"])
        status_row = conn.execute(
            "SELECT status FROM result_status WHERE subject_id = ?",
            (payload.subject_id,),
        ).fetchone()
        current = status_row["status"] if status_row else "draft"
        if current != "draft":
            raise HTTPException(
                409,
                "This subject is locked. Ask the admin to return it for changes.",
            )

        known = {
            r["id"]
            for r in conn.execute("SELECT id FROM students").fetchall()
        }
        for entry in payload.marks:
            if entry.student_id not in known:
                raise HTTPException(404, f"Student {entry.student_id} not found.")
            if entry.marks is not None and entry.marks > subject["max_marks"]:
                raise HTTPException(
                    400, f"Marks must be between 0 and {subject['max_marks']}."
                )

        if payload.action == "submitted":
            # Judge completeness on the state *after* this save. A student counts
            # as graded if the incoming payload has marks for them (they may have
            # no marks row yet, e.g. a student just added), or if the payload
            # does not mention them and a stored mark survives. An explicit null
            # clears the mark, so it leaves the subject incomplete.
            incoming = {e.student_id: e.marks for e in payload.marks}
            ungraded = []
            for sid in known:
                if sid in incoming:
                    if incoming[sid] is None:
                        ungraded.append(sid)
                    continue
                stored = conn.execute(
                    "SELECT marks FROM marks"
                    " WHERE student_id = ? AND subject_id = ? AND marks IS NOT NULL",
                    (sid, payload.subject_id),
                ).fetchone()
                if stored is None:
                    ungraded.append(sid)
            if ungraded:
                raise HTTPException(
                    400, "Enter marks for every student before submitting."
                )

        for entry in payload.marks:
            if entry.marks is None:
                conn.execute(
                    "DELETE FROM marks WHERE student_id = ? AND subject_id = ?",
                    (entry.student_id, payload.subject_id),
                )
            else:
                conn.execute(
                    "INSERT INTO marks (student_id, subject_id, marks) VALUES (?,?,?)"
                    " ON CONFLICT(student_id, subject_id)"
                    " DO UPDATE SET marks = excluded.marks",
                    (entry.student_id, payload.subject_id, entry.marks),
                )

        if payload.action != "draft":
            conn.execute(
                "INSERT INTO result_status (subject_id, status) VALUES (?,?)"
                " ON CONFLICT(subject_id) DO UPDATE SET status = excluded.status",
                (payload.subject_id, payload.action),
            )

    return {"ok": True, "status": payload.action}


@router.get("/performance")
def performance(user: dict = Depends(require_teacher)):
    with db() as conn:
        subjects = conn.execute(
            """
            SELECT s.id, s.name, s.max_marks
            FROM subjects s WHERE s.teacher_id = ? ORDER BY s.id
            """,
            (user["id"],),
        ).fetchall()
        out = []
        for subject in subjects:
            values = subject_marks(conn, subject["id"])
            stats = subject_stats(values, subject["max_marks"])
            students = conn.execute(
                """
                SELECT s.name, m.marks FROM students s
                LEFT JOIN marks m ON m.student_id = s.id AND m.subject_id = ?
                ORDER BY s.roll
                """,
                (subject["id"],),
            ).fetchall()
            out.append(
                {
                    "id": subject["id"],
                    "name": subject["name"],
                    "max": subject["max_marks"],
                    "average": stats["average"],
                    "highest": stats["highest"],
                    "pass_rate": stats["pass_rate"],
                    "students": [
                        {
                            "name": r["name"],
                            "marks": r["marks"],
                            "percent": round(r["marks"] / subject["max_marks"] * 100, 1)
                            if r["marks"] is not None
                            else None,
                        }
                        for r in students
                        if r["marks"] is not None
                    ],
                }
            )
    return out