# Student Result Management System - Backend

FastAPI + SQLite REST API for the SRMS front-end. Plain `sqlite3` (no ORM) and
JWT bearer tokens, so there is nothing to learn beyond SQL and HTTP.

## Run it

Easiest - one click, starts the server and opens your browser:

```
..\start.bat
```

Or by hand, from this folder:

```
run.bat                     <- Windows: creates .venv, installs deps, starts the server
```

Or by hand:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn main:app --reload --port 8000
```

Then open **http://127.0.0.1:8000** - the API serves the `srms-frontend` folder
too, so the front-end and API share one origin and no CORS setup is needed.

| What | Where |
|------|-------|
| App + front-end | http://127.0.0.1:8000 |
| Interactive API docs | http://127.0.0.1:8000/docs |
| Health check | http://127.0.0.1:8000/api/health |

## Demo logins

| Role | ID | Password |
|------|----|----------|
| Admin | `admin` | `admin123` |
| Teacher | `T1`, `T2` | `teach123` |
| Student | `CS101` - `CS106` | `stud123` |

The demo data is inserted automatically the first time the database file is
created. Delete `srms.db` to start over.

Passwords are **case sensitive**. A mobile keyboard that capitalises the first
letter turns `stud123` into `Stud123`, which is rejected - the sign-in form
disables autocapitalisation for this reason.

## Layout

```
main.py        FastAPI app, CORS, static front-end mount
database.py    SQLite connection helper and schema
security.py    PBKDF2 password hashing, JWT issuing, role guards
grading.py     Grade scale, subject stats, per-student result summary
schemas.py     Pydantic request/response models
seed.py        Demo data
routers/       auth, admin, teacher, student endpoints
test_api.py    End-to-end API test (run with the server up)
```

## Database

One file, `srms.db`, created on first run.

| Table | Holds |
|-------|-------|
| `admins` | one row, the administrator account |
| `teachers` | teacher id, name, password hash |
| `students` | id, roll number (unique), name, class, date of birth, password hash |
| `subjects` | id, name, max marks, assigned teacher |
| `marks` | one row per student per subject; a missing row means "not graded" |
| `result_status` | `draft` / `submitted` / `approved` per subject |

`marks` deliberately stores no row for an ungraded student rather than a `NULL`
mark, so "not entered" and "scored zero" stay distinguishable.

## Result workflow

```
draft  --(teacher submits)-->  submitted  --(admin approves)-->  approved
  ^                                                          |
  +---------------(admin returns to teacher)------------------+
```

- A teacher can only edit a subject while it is in `draft`. The API returns 409
  otherwise, so the lock cannot be bypassed by calling the endpoint directly.
- A subject can only be submitted once every student has a mark, and can only be
  approved once every student has a mark in the database.
- Students only ever see subjects that are `approved`.

## Endpoints

**Auth**
```
POST   /api/auth/login                 {"role","identifier","password"}
POST   /api/auth/register              {"roll","name","cls","dob","password"}
GET    /api/auth/me
```

`/api/auth/register` is how a student creates their own account with a chosen
roll number and password. It returns a token, so they land straight on their
results page. Only students can self-register - admin and teacher accounts are
provisioned by an administrator, otherwise anyone could promote themselves.

| Rule | Response |
|------|----------|
| Roll already taken (any letter case) | 409 |
| Password under 6 characters | 422 |
| Name, class or roll is only whitespace | 422 |
| An extra `role` field is sent | ignored, always created as `student` |

**Admin** (admin token required)
```
GET    /api/admin/overview
GET    /api/admin/students
POST   /api/admin/students
DELETE /api/admin/students/{id}
GET    /api/admin/students/{id}/card
GET    /api/admin/subjects
POST   /api/admin/subjects
PATCH  /api/admin/subjects/{id}/teacher
GET    /api/admin/approvals
POST   /api/admin/approvals/{id}/status     {"status": "approved" | "draft"}
```

**Teacher** (teacher token, own subjects only)
```
GET    /api/teacher/subjects
GET    /api/teacher/marks?subject_id=SUB1
PUT    /api/teacher/marks      {"subject_id", "action": "draft"|"submitted", "marks": [...]}
GET    /api/teacher/performance
```

**Student** (student token, own record only)
```
GET    /api/student/result
GET    /api/student/card
```

Send the token as `Authorization: Bearer <token>`. Tokens expire after 8 hours.

## Tests

With the server running:

```
.venv\Scripts\python test_api.py
```

68 checks covering login, role isolation (403s), CRUD, duplicate roll numbers,
validation errors, the draft/submitted/approved workflow, mark range limits,
deleting a student whose token is still valid, and a student added after marks
were seeded being graded in the same submit.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SRMS_DB` | `./srms.db` | database file path |
| `SRMS_SECRET` | `change-this-in-production` | JWT signing key - **set this in production** |
| `SRMS_FRONTEND` | auto-detected | folder served at `/` |

`SRMS_FRONTEND` is optional: the server probes `../srms-frontend`, then
`./srms-frontend`, then the project folder itself, and takes the first one with
an `index.html`. It prints which folder it chose at startup. If none is found
it logs a warning and `/` answers **503** instead of pretending everything is
fine.

Example:

```
$env:SRMS_SECRET = "a-long-random-string"
.venv\Scripts\python -m uvicorn main:app --port 8000
```

## Security notes

- Passwords are stored as PBKDF2-HMAC-SHA256 with a random salt and 200,000
  iterations. Plaintext passwords are never written to the database.
- Password hashes are never included in an API response, including to admins.
- Student self-registration cannot set a role, so it cannot be used to gain
  admin or teacher access.
- Login answers the same 401 for an unknown ID and a wrong password, so it does
  not reveal which accounts exist.
- Every endpoint re-checks the role and the row ownership from the token, so a
  teacher cannot read another teacher's subject by changing an id.
- CORS is open (`allow_origins=["*"]`) because the front-end is served from the
  same origin in development. Lock it down before deploying.