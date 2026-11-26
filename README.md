# Student Result Management System (SRMS) - BCA

A role-based Student Result Management System built with **FastAPI**, **SQLite**, and **Vanilla HTML/CSS/JavaScript**.

## 🚀 Key Features

* **Role-Based Access Control:**
  * **Admin:** Dashboard analytics, student CRUD, subject management, teacher assignment, and result approval workflow.
  * **Teacher:** Subject marks entry with real-time grade calculations, save draft, submit for approval, and class performance metrics.
  * **Student:** Subject-wise scorecards, overall percentage, CGPA calculation, and downloadable/printable PDF report cards.
* **Student Self-Registration:** Students can register directly with their roll number and password.
* **Modern Security:** PBKDF2 password hashing (200,000 iterations) and JWT Bearer token authentication.
* **Single-Origin Architecture:** FastAPI serves both the REST API endpoints (`/api/...`) and the frontend UI, eliminating CORS friction in development.

## 🛠️ Tech Stack

* **Backend:** Python 3.12+ / FastAPI, Uvicorn, Pydantic, PyJWT, SQLite3
* **Frontend:** HTML5, CSS3, JavaScript (Fetch API, responsive layout, print-ready report card styles)

## ⚡ Quick Start

### 1. One-Click Launch (Windows)
Simply double-click:
```bat
start.bat
```
This automatically initializes the virtual environment, installs dependencies, launches the server on port 8000, and opens `http://127.0.0.1:8000` in your browser.

### 2. Manual Setup
```bash
cd srms-backend
run.bat
```
Or with Python:
```bash
cd srms-backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn main:app --reload --port 8000
```
Then visit:
* **Application:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **API Documentation (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## 🔑 Demo Credentials

| Role | Username / ID | Password |
| :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` |
| **Teacher** | `T1` or `T2` | `teach123` |
| **Student** | `CS101` to `CS106` | `stud123` |

*(Note: Passwords are case-sensitive.)*

## 📁 Project Structure

```text
├── start.bat             # One-click startup script for Windows
├── README.md             # Project documentation
├── .gitignore            # Git ignore configuration
├── srms-backend/         # FastAPI backend
│   ├── main.py           # Application entry point & static files mounting
│   ├── database.py       # SQLite connection and schema management
│   ├── grading.py        # Grading criteria and CGPA calculation engine
│   ├── security.py       # PBKDF2 password hashing & JWT token handling
│   ├── schemas.py        # Pydantic request & response validation schemas
│   ├── seed.py           # Demo dataset seeder
│   ├── test_api.py       # API smoke test suite (88 test cases)
│   ├── requirements.txt  # Python package dependencies
│   ├── run.bat           # Backend launcher
│   └── routers/          # API route controllers (admin, auth, student, teacher)
└── srms-frontend/        # Vanilla web frontend
    ├── index.html        # Single-page UI shell
    ├── css/style.css     # Responsive design & print stylesheet
    └── js/app.js         # Single-page application router & API client
```
