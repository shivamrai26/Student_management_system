"""Grading rules and the result summary shared by every report."""
from database import connect

# percentage floor, grade letter, grade points
GRADE_SCALE = [
    (90, "A+", 10),
    (80, "A", 9),
    (70, "B+", 8),
    (60, "B", 7),
    (50, "C", 6),
    (40, "D", 5),
    (0, "F", 0),
]
PASS_PERCENT = 40


def grade_for(percentage):
    for floor, letter, points in GRADE_SCALE:
        if percentage >= floor:
            return {"letter": letter, "points": points}
    return {"letter": "F", "points": 0}


def subject_stats(values, max_marks):
    """Class average, highest score and pass rate for one subject."""
    values = [v for v in values if v is not None]
    count = len(values) or 1
    return {
        "average": round(sum(values) / count / max_marks * 100, 1),
        "highest": max(values) if values else 0,
        "pass_rate": round(
            sum(1 for v in values if grade_for(v / max_marks * 100)["letter"] != "F")
            / count
            * 100,
            1,
        ),
        "entered": len(values),
    }


def subject_marks(conn, subject_id):
    rows = conn.execute(
        "SELECT marks FROM marks WHERE subject_id = ? AND marks IS NOT NULL",
        (subject_id,),
    ).fetchall()
    return [r["marks"] for r in rows]


def result_summary(conn, student_id):
    """A student's rows for approved subjects, plus totals, CGPA and pass/fail."""
    rows = conn.execute(
        """
        SELECT s.id, s.name, s.max_marks, m.marks
        FROM subjects s
        LEFT JOIN marks m ON m.subject_id = s.id AND m.student_id = ?
        LEFT JOIN result_status r ON r.subject_id = s.id
        WHERE r.status = 'approved'
        ORDER BY s.id
        """,
        (student_id,),
    ).fetchall()

    out = []
    total = 0
    max_total = 0
    entered = 0
    points = 0
    for row in rows:
        marks = row["marks"]
        grade = (
            grade_for(marks / row["max_marks"] * 100) if marks is not None else None
        )
        out.append(
            {
                "subject_id": row["id"],
                "name": row["name"],
                "max": row["max_marks"],
                "marks": marks,
                "grade": grade["letter"] if grade else None,
                "points": grade["points"] if grade else None,
            }
        )
        if marks is not None:
            total += marks
            max_total += row["max_marks"]
            entered += 1
            points += grade["points"]

    pending = conn.execute(
        """
        SELECT COUNT(*) AS n FROM subjects s
        LEFT JOIN result_status r ON r.subject_id = s.id
        WHERE r.status IS NULL OR r.status != 'approved'
        """
    ).fetchone()["n"]

    return {
        "rows": out,
        "total": total,
        "max": max_total,
        "percentage": round(total / max_total * 100, 1) if max_total else 0.0,
        "cgpa": round(points / entered, 2) if entered else 0.0,
        "declared": entered > 0,
        "pass": entered > 0 and all(r["grade"] != "F" for r in out if r["marks"] is not None),
        "pending_subjects": pending,
    }