# Student Result Management System - Frontend

Plain HTML, CSS and JavaScript. No install or build step.

**Start it:** run `..\start.bat` - that starts the backend and opens
**http://127.0.0.1:8000** in your browser.

The UI talks to the FastAPI backend in `../srms-backend` over `fetch`. The
backend serves this folder, so front-end and API share one origin. This folder
must stay a sibling of `srms-backend`; the server probes for it and will print
a warning and answer 503 if it is missing.

To run this folder on its own instead, set the API base URL before loading the
page, e.g. in `index.html`:

```html
<script>window.SRMS_API = 'http://127.0.0.1:8000';</script>
```

## Demo logins
| Role | ID | Password |
|---------|----|----------|
| Admin | `admin` | `admin123` |
| Teacher | `T1` / `T2` | `teach123` |
| Student | `CS101`-`CS106` | `stud123` |

Passwords are case sensitive - `stud123` works, `Stud123` does not.

**No account?** "Create a student account" on the sign-in page. A student picks
their own roll number and password and is signed in immediately. Only students
can self-register; admin and teacher accounts come from the administrator.

## What is included
- Student self-registration, plus role-based login (Admin, Teacher, Student) with JWT bearer tokens
- Admin: overview, student CRUD, subject and teacher assignment, result approval
- Teacher: marks entry with live grading, save draft, submit for approval, class performance
- Student: subject-wise results, percentage, CGPA, printable report card (Save as PDF)

Grading: 90+ A+, 80+ A, 70+ B+, 60+ B, 50+ C, 40+ D, below 40 F (fail). Pass needs 40% in every subject.

## How it is put together
- `js/app.js` - one file: a small `api()` fetch wrapper, the page renderers, and
  delegated click/submit/change/input handlers. All markup is built as template
  strings and injected into `#app`.
- `css/style.css` - one file, custom properties for the colour palette, plus a
  print stylesheet for the report card.
- State is deliberately tiny: the signed-in user, the current page, and the
  selected subject. Everything else comes from the API on each render, so the
  page always reflects what the server actually holds.

The grade scale is duplicated in `js/app.js` for instant feedback while a teacher
types. The server re-grades every result and is the source of truth.

## Working on it
The API contract is documented in `../srms-backend/README.md`, and
`../srms-backend/test_api.py` exercises every endpoint.