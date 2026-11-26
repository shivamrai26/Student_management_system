"""Student-only endpoints: own result and report card."""
from fastapi import APIRouter, Depends, HTTPException

from database import db
from grading import result_summary
from security import require_student

router = APIRouter(prefix="/api/student", tags=["student"])


def _profile(conn, student_id):
    row = conn.execute(
        "SELECT id, roll, name, cls, dob FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Student record not found.")
    return dict(row)


@router.get("/result")
def my_result(user: dict = Depends(require_student)):
    with db() as conn:
        return {
            "student": _profile(conn, user["id"]),
            "result": result_summary(conn, user["id"]),
        }


@router.get("/card")
def my_card(user: dict = Depends(require_student)):
    with db() as conn:
        return {
            "student": _profile(conn, user["id"]),
            "result": result_summary(conn, user["id"]),
        }