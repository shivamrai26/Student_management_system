"""Password hashing (PBKDF2-SHA256) and JWT issuing/verification."""
import hashlib
import hmac
import os
import time

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database import connect

SECRET = os.environ.get("SRMS_SECRET", "change-this-in-production")
ALGORITHM = "HS256"
TOKEN_HOURS = 8
ITERATIONS = 200_000

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, ITERATIONS
    )
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(user: dict) -> str:
    payload = {
        "sub": user["id"],
        "role": user["role"],
        "name": user["name"],
        "exp": int(time.time()) + TOKEN_HOURS * 3600,
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def user_from_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired. Please sign in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token. Please sign in again.")
    return {"id": payload["sub"], "role": payload["role"], "name": payload["name"]}


def current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    if creds is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Not signed in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_from_token(creds.credentials)


def _deny(user):
    raise HTTPException(403, "You do not have access to this action.")


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        _deny(user)
    return user


def require_teacher(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "teacher":
        _deny(user)
    return user


def require_student(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "student":
        _deny(user)
    return user


def lookup_user(role: str, identifier: str):
    """Find an admin/teacher/student row by the id the user types at login."""
    identifier = identifier.strip().upper()
    table = {"admin": "admins", "teacher": "teachers", "student": "students"}.get(role)
    if table is None:
        return None
    column = "roll" if role == "student" else "id"
    conn = connect()
    try:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE UPPER({column}) = ?", (identifier,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "id": row["id"],
        "role": role,
        "name": row["name"],
        "password_hash": row["password_hash"],
    }