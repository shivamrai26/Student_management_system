"""Login, self-registration and session endpoints."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from database import db, insert_student
from schemas import LoginIn, RegisterIn, TokenOut, UserOut
from security import create_token, current_user, lookup_user, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Spelled out per role because the sign-in form has a role switcher, and the
# most common mistake is typing an admin username while the Student tab is active.
HINT = {
    "student": "Enter your roll number (for example CS101).",
    "teacher": "Enter your teacher ID (T1 or T2).",
    "admin": "Enter the admin username.",
}


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn):
    user = lookup_user(payload.role, payload.identifier)
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            401,
            f"{HINT[payload.role]} ID or password is incorrect."
            f" (You are on the {payload.role} tab.)",
        )
    token = create_token(user)
    return {
        "token": token,
        "user": {"id": user["id"], "role": user["role"], "name": user["name"]},
    }


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn):
    """Let a student create their own account with a chosen roll and password.

    Only students can self-register. Admin and teacher accounts are provisioned
    by an administrator, otherwise anyone could promote themselves.
    """
    roll = payload.roll.strip().upper()
    with db() as conn:
        try:
            insert_student(
                conn,
                roll=roll,
                name=payload.name,
                cls=payload.cls,
                dob=payload.dob,
                password=payload.password,
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                409,
                f"Roll number {roll} is already registered. Sign in instead, "
                "or pick a different roll number.",
            )
        row = conn.execute(
            "SELECT id, name FROM students WHERE roll = ?", (roll,)
        ).fetchone()

    user = {"id": row["id"], "role": "student", "name": row["name"]}
    # Signed in straight away: no need to type the password twice.
    return {"token": create_token(user), "user": user}


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(current_user)):
    return user