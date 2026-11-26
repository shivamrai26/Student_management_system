"""Student Result Management System - FastAPI backend."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db
from routers import admin, auth, student, teacher
from seed import seed_if_empty

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(BASE_DIR)


def _find_frontend():
    """Where the plain HTML/CSS/JS front-end lives.

    SRMS_FRONTEND always wins. Otherwise probe the usual places, because the
    folder has been found nested inside the backend more than once.
    """
    override = os.environ.get("SRMS_FRONTEND")
    if override:
        return override
    candidates = [
        os.path.join(_PROJECT, "srms-frontend"),      # ../srms-frontend
        os.path.join(BASE_DIR, "srms-frontend"),      # ./srms-frontend
        _PROJECT,                                     # files sit beside backend
    ]
    for path in candidates:
        if os.path.isfile(os.path.join(path, "index.html")):
            return path
    return candidates[0]


FRONTEND_DIR = _find_frontend()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if seed_if_empty():
        print(
            "Seeded demo data: admin/admin123, T1-T2/teach123, CS101-CS106/stud123",
            flush=True,
        )
    yield


app = FastAPI(
    title="Student Result Management System API",
    version="1.0.0",
    description=(
        "Role based result management: teachers enter marks, admins approve them, "
        "students see graded results and report cards."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def no_cache_frontend(request, call_next):
    """Stop the browser serving a stale app.js after an edit.

    Only the API benefits from caching; during development the front-end files
    must always come from disk, otherwise a reload keeps running old code.
    """
    response = await call_next(request)
    if not request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store, must-revalidate"
    return response


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(student.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve the plain HTML/CSS/JS front-end from the same origin, so no CORS setup
# is needed during development. The API stays available under /api.
if os.path.isdir(FRONTEND_DIR):
    print(f"Serving front-end from {FRONTEND_DIR}", flush=True)
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(
        f"WARNING: front-end folder not found at {FRONTEND_DIR} - "
        "the API works but the pages will not load. "
        "Set SRMS_FRONTEND to the srms-frontend directory.",
        flush=True,
    )

    # 503, not 200: a missing front-end is a broken install, and a 200 here
    # would otherwise make a health check pass while the pages do not load.
    @app.get("/", status_code=503)
    def missing_frontend():
        return {
            "error": "Front-end folder not found.",
            "expected": FRONTEND_DIR,
            "hint": "Set SRMS_FRONTEND to the srms-frontend directory.",
        }