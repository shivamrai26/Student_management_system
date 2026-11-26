"""Admin-only endpoints: students, subjects, teacher assignment, approvals."""
from fastapi import APIRouter, Depends, HTTPException

from database import db, insert_student, next_id
from grading import GRADE_SCALE, result_summary, subject_marks, subject_stats
from schemas import AssignTeacherIn, StatusIn, StudentIn, SubjectIn
from security import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------- overview
@router.get("/overview")
def overview(user: dict = Depends(require_admin)):
    with db() as conn:
        students = conn.execute("SELECT id FROM students").fetchall()
        summary = [result_summary(conn, s["id"]) for s in students]
        subjects = conn.execute(
            """
            SELECT s.id, s.name, s.max_marks,
                   COALESCE(r.status, 'draft') AS status,
                   t.name AS teacher
            FROM subjects s
            LEFT JOIN result_status r ON r.subject_id = s.id
            LEFT JOIN teachers t ON t.id = s.teacher_id
            ORDER BY s.id
            """
        ).fetchall()

        distribution = {letter: 0 for _floor, letter, _pts in GRADE_SCALE}
        for m in summary:
            for row in m["rows"]:
                if row["grade"]:
                    distribution[row["grade"]] += 1

        averages = []
        for subject in subjects:
            stats = subject_stats(
                subject_marks(conn, subject["id"]), subject["max_marks"]
            )
            averages.append(
                {
                    "id": subject["id"],
                    "name": subject["name"],
                    "average": stats["average"],
                }
            )

        teachers = conn.execute("SELECT COUNT(*) AS n FROM teachers").fetchone()["n"]
        passed = sum(1 for m in summary if m["pass"])

    return {
        "students": len(students),
        "teachers": teachers,
        "subjects": len(subjects),
        "pass_rate": round(passed / len(students) * 100) if students else 0,
        "distribution": distribution,
        "subject_averages": averages,
    }


# ---------------------------------------------------------------- students
@router.get("/students")
def list_students(user: dict = Depends(require_admin)):
    with db() as conn:
        rows = conn.execute(
            "SELECT id, roll, name, cls, dob FROM students ORDER BY roll"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/students", status_code=201)
def add_student(payload: StudentIn, user: dict = Depends(require_admin)):
    roll = payload.roll.strip().upper()
    with db() as conn:
        if conn.execute("SELECT 1 FROM students WHERE roll = ?", (roll,)).fetchone():
            raise HTTPException(409, "That roll number already exists.")
        insert_student(
            conn,
            roll=roll,
            name=payload.name,
            cls=payload.cls,
            dob=payload.dob,
            password=payload.password,
        )
        student_id = conn.execute(
            "SELECT id FROM students WHERE roll = ?", (roll,)
        ).fetchone()["id"]
    return {"id": student_id, "roll": roll}


@router.delete("/students/{student_id}", status_code=204)
def remove_student(student_id: str, user: dict = Depends(require_admin)):
    with db() as conn:
        cursor = conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        if cursor.rowcount == 0:
            raise HTTPException(404, "Student not found.")


@router.get("/students/{student_id}/card")
def student_card(student_id: str, user: dict = Depends(require_admin)):
    with db() as conn:
        row = conn.execute(
            "SELECT id, roll, name, cls, dob FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Student not found.")
        summary = result_summary(conn, student_id)
    return {"student": dict(row), "result": summary}


# ---------------------------------------------------------------- subjects
@router.get("/subjects")
def list_subjects(user: dict = Depends(require_admin)):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.name, s.max_marks, s.teacher_id, t.name AS teacher
            FROM subjects s
            LEFT JOIN teachers t ON t.id = s.teacher_id
            ORDER BY s.id
            """
        ).fetchall()
        teachers = conn.execute(
            "SELECT id, name FROM teachers ORDER BY id"
        ).fetchall()
    return {
        "subjects": [dict(r) for r in rows],
        "teachers": [dict(t) for t in teachers],
    }


@router.post("/subjects", status_code=201)
def add_subject(payload: SubjectIn, user: dict = Depends(require_admin)):
    with db() as conn:
        if payload.teacher_id and not conn.execute(
            "SELECT 1 FROM teachers WHERE id = ?", (payload.teacher_id,)
        ).fetchone():
            raise HTTPException(404, "Teacher not found.")
        subject_id = next_id(conn, "subjects", "SUB")
        conn.execute(
            "INSERT INTO subjects (id, name, max_marks, teacher_id) VALUES (?,?,?,?)",
            (subject_id, payload.name.strip(), payload.max_marks, payload.teacher_id),
        )
        conn.execute(
            "INSERT INTO result_status (subject_id, status) VALUES (?,'draft')",
            (subject_id,),
        )
    return {"id": subject_id}


@router.patch("/subjects/{subject_id}/teacher")
def assign_teacher(
    subject_id: str, payload: AssignTeacherIn, user: dict = Depends(require_admin)
):
    with db() as conn:
        if not conn.execute(
            "SELECT 1 FROM teachers WHERE id = ?", (payload.teacher_id,)
        ).fetchone():
            raise HTTPException(404, "Teacher not found.")
        cursor = conn.execute(
            "UPDATE subjects SET teacher_id = ? WHERE id = ?",
            (payload.teacher_id, subject_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "Subject not found.")
    return {"ok": True}


# ---------------------------------------------------------------- approvals
@router.get("/approvals")
def list_approvals(user: dict = Depends(require_admin)):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.name, s.max_marks,
                   COALESCE(r.status, 'draft') AS status,
                   t.name AS teacher
            FROM subjects s
            LEFT JOIN result_status r ON r.subject_id = s.id
            LEFT JOIN teachers t ON t.id = s.teacher_id
            ORDER BY s.id
            """
        ).fetchall()
        out = []
        for row in rows:
            stats = subject_stats(subject_marks(conn, row["id"]), row["max_marks"])
            out.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "teacher": row["teacher"] or "-",
                    "status": row["status"],
                    "average": stats["average"],
                }
            )
    return out


@router.post("/approvals/{subject_id}/status")
def set_status(
    subject_id: str, payload: StatusIn, user: dict = Depends(require_admin)
):
    with db() as conn:
        if not conn.execute(
            "SELECT 1 FROM subjects WHERE id = ?", (subject_id,)
        ).fetchone():
            raise HTTPException(404, "Subject not found.")
        if payload.status == "approved":
            ungraded = conn.execute(
                """
                SELECT COUNT(*) AS n FROM students s
                LEFT JOIN marks m ON m.student_id = s.id AND m.subject_id = ?
                WHERE m.marks IS NULL
                """,
                (subject_id,),
            ).fetchone()["n"]
            if ungraded:
                raise HTTPException(
                    409,
                    f"{ungraded} student(s) still have no marks for this subject.",
                )
        conn.execute(
            "INSERT INTO result_status (subject_id, status) VALUES (?,?)"
            " ON CONFLICT(subject_id) DO UPDATE SET status = excluded.status",
            (subject_id, payload.status),
        )
    return {"id": subject_id, "status": payload.status}