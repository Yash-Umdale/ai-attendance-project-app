# 🔐 VeriAttend — AI-Powered Face Recognition Attendance Platform

<p align="center">
  <img src="https://i.ibb.co/YTYGn5qV/logo.png" alt="VeriAttend Logo" width="100"/>
</p>

<p align="center">
  <b>Contactless attendance verification with face detection, liveness verification, and confidence-based review</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-18-61dafb?logo=react&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/dlib-Face%20Recognition-orange" />
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" />
</p>

---

## 📌 Table of Contents

- [Project Overview](#-project-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Features](#-features)
- [System Workflow](#-system-workflow)
- [Installation](#-installation)
- [Environment Variables](#-environment-variables)
- [How to Start Backend](#-how-to-start-backend)
- [How to Start Frontend](#-how-to-start-frontend)
- [Student Enrollment](#-student-enrollment)
- [How Attendance Works](#-how-attendance-works)
- [Face Recognition Approach](#-face-recognition-approach)
- [Liveness Approach](#-liveness-approach)
- [Confidence-Based Review](#-confidence-based-review)
- [API Documentation](#-api-documentation)
- [Testing](#-testing)
- [Known Limitations](#-known-limitations)

---

## 🎯 Project Overview

**VeriAttend** is an AI-powered face recognition attendance platform that provides a reliable contactless attendance workflow. Unlike simple face-detection-equals-attendance systems, VeriAttend implements a multi-step verification pipeline:

1. **Face Detection** — Detect and validate exactly one face
2. **Liveness Verification** — Distinguish live person from photo/screen
3. **Face Recognition** — Identify the student with confidence scoring
4. **Attendance Decision** — Route to auto-approve, manual review, or reject
5. **Admin Review** — Teachers review borderline cases

This is a Final Year Project developed at Walchand Institute of Technology, Solapur.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────┐
│                  REACT FRONTEND                       │
│          (Vite + React Router + WebRTC)               │
│                                                       │
│  ┌─────────┐ ┌──────────┐ ┌────────────┐ ┌────────┐ │
│  │  Login  │ │ Register │ │ Attendance │ │ Admin  │ │
│  │  Page   │ │   Page   │ │   Page     │ │Dashboard│ │
│  └────┬────┘ └────┬─────┘ └─────┬──────┘ └───┬────┘ │
│       └───────────┴─────────────┴─────────────┘       │
│                        │ Axios API Client              │
└────────────────────────┼──────────────────────────────┘
                         │ REST API (JSON)
┌────────────────────────┼──────────────────────────────┐
│                  FASTAPI BACKEND                       │
│                                                       │
│  ┌──────────────────────────────────────────────────┐ │
│  │              API ROUTER LAYER                     │ │
│  │  /auth  /students  /recognition  /liveness       │ │
│  │  /attendance  /sessions  /reviews  /admin        │ │
│  └───────────────────┬──────────────────────────────┘ │
│                      │                                │
│  ┌───────────────────┴──────────────────────────────┐ │
│  │              SERVICE LAYER                        │ │
│  │  Face Detection → Liveness → Recognition →       │ │
│  │  Attendance Decision Engine                       │ │
│  └───────────────────┬──────────────────────────────┘ │
│                      │                                │
│  ┌───────────────────┴──────────────────────────────┐ │
│  │         DATA LAYER (SQLAlchemy + SQLite)          │ │
│  │  Teachers | Students | Subjects | Sessions       │ │
│  │  Attendance Records | Manual Reviews             │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + Vite | Single-page application |
| **Camera** | WebRTC (getUserMedia) | Live camera access |
| **Styling** | Vanilla CSS (dark mode) | Premium glassmorphism UI |
| **Backend** | FastAPI (Python) | REST API server |
| **Face Detection** | dlib | Frontal face detector + 68-point landmarks |
| **Face Embeddings** | dlib ResNet | 128-dimensional face descriptors |
| **Classification** | scikit-learn SVM | Face embedding classifier |
| **Liveness** | dlib landmarks + OpenCV | Blink detection (EAR) + head pose + texture analysis |
| **Database** | SQLite (SQLAlchemy ORM) | Relational data storage |
| **Auth** | JWT + bcrypt | Token-based authentication |
| **API Docs** | Swagger / ReDoc | Auto-generated from FastAPI |

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📸 **Face Registration** | Webcam-based face enrollment with quality validation |
| 🔍 **Face Detection** | Separate detection layer (NO_FACE, ONE_FACE, MULTIPLE_FACES) |
| 🧠 **Face Recognition** | 128D embedding comparison with confidence scores |
| ✨ **Liveness Verification** | Passive (texture) + Challenge-based (blink, head turn) |
| 📊 **Confidence-Based Routing** | Auto-approve / Manual review / Reject |
| 📋 **Manual Review** | Admin reviews identified faces below the confidence threshold |
| 📅 **Attendance Sessions** | Time-bounded sessions with activate/deactivate |
| 🔒 **Duplicate Prevention** | Same student can't mark twice per session |
| 👨‍🏫 **Admin Dashboard** | Stats, attendance tables, search/filter, student password resets |
| 🗓️ **Absent Student Reporting** | Lists enrolled students with no attendance attempt after a session ends |
| 🧹 **Clear Application Data** | Password and typed-phrase protected removal of student/class/attendance data |
| 🔐 **JWT Authentication** | Secure teacher login with token-based auth |

---

## 🔄 System Workflow

```
Student → Open Camera → WebRTC → Capture Frame
                                       │
                           ┌───────────┴────────────┐
                           │    FACE DETECTION       │
                           │ (NO_FACE? MULTIPLE?)    │
                           └───────────┬─────────────┘
                                       │ ONE_FACE
                           ┌───────────┴────────────┐
                           │  LIVENESS VERIFICATION  │
                           │ (texture + anti-spoof)  │
                           └───────────┬─────────────┘
                                       │ PASS
                           ┌───────────┴────────────┐
                           │   FACE RECOGNITION      │
                           │ (128D embedding + SVM)  │
                           └───────────┬─────────────┘
                                       │ confidence
                        ┌──────────────┼──────────────┐
                        │              │              │
                   ≥ 40%         < 40% with match     No match or
                   AUTO              MANUAL          liveness failure
                  APPROVE            REVIEW              REJECT
```

---

## ⚙️ Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- CMake (required for dlib)

### Step 1: Clone

```bash
git clone https://github.com/Yash-Umdale/ai-attendance-project-app.git
cd ai-attendance-project-app
```

### Step 2: Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

# Windows PowerShell
Copy-Item .env.example .env

# macOS/Linux
cp .env.example .env
```

### Step 3: Frontend Setup

```bash
cd frontend
npm install
```

> The React/FastAPI application is the supported VeriAttend interface. The
> older Streamlit prototype has been removed from this repository; do not run
> different application interfaces against the same database.

---

## 🔑 Environment Variables

All configuration is in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./veriattend.db` | Database connection string |
| `JWT_SECRET_KEY` | (dev default) | JWT signing secret — **change in production** |
| `RECOGNITION_THRESHOLD` | `0.6` | Euclidean distance threshold for face matching |
| `CONFIDENCE_HIGH_THRESHOLD` | `0.40` | Auto-approve identified matches at or above 40%; lower identified matches go to manual review |
| `CONFIDENCE_BORDERLINE_THRESHOLD` | `0.40` | Legacy compatibility setting; the decision engine no longer uses a second confidence band |
| `LIVENESS_EAR_THRESHOLD` | `0.21` | Eye Aspect Ratio threshold for blink detection |
| `LIVENESS_CHALLENGE_TIMEOUT` | `15` | Seconds before a liveness challenge expires |
| `CAMERA_SAMPLE_INTERVAL_MS` | `1500` | Milliseconds between frame captures |

---

## 🚀 How to Start Backend

```bash
cd backend
# Activate virtual environment first
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API available at: `http://localhost:8000`
Swagger docs at: `http://localhost:8000/docs`

---

## 🚀 How to Start Frontend

```bash
cd frontend
npm run dev
```

App available at: `http://localhost:5173`

> The Vite dev server proxies `/api/*` requests to the backend at port 8000.

---

## 📸 Student Enrollment

1. Navigate to `/register`
2. Enter student details (ID, name, email, department, year)
3. Camera opens for face capture
4. System validates: exactly one face, acceptable quality
5. 128D face embedding is generated and stored
6. Registration complete — student can now use attendance

**Requirements enforced:**
- Zero faces → rejected
- Multiple faces → rejected
- Poor quality → rejected
- Duplicate student ID → rejected

---

## 📋 How Attendance Works

1. Admin creates an **Attendance Session** (name, subject, date, time window)
2. Student opens `/attendance`, selects active session
3. Camera captures frame → sent to backend
4. Backend runs the **full pipeline**:
   - Face Detection → Liveness Check → Face Recognition → Decision Engine
5. Result displayed to student:
   - ✅ **Approved** — identified match at or above 40%, auto-marked present
   - 📋 **Manual Review** — identified match below 40%, saved as pending for an administrator
   - ❌ **Rejected / Unknown** — liveness failure or no student identity could be matched

### Reporting absent students

In the admin dashboard's **Attendance** tab, choose a subject and date, set **Status** to **Absent**, and select **Filter**. For each completed session, the report compares the enrolled roster with attendance attempts and shows enrolled students who have no attendance record as **ABSENT · No attendance**. A session is considered complete after its scheduled end time. These derived rows are calculated for the report and are not written to the attendance database. A student with a recorded attendance attempt, including one pending manual review, is not treated as absent.

### Student account recovery and data clearing

- An administrator can set a new student password from the **Students** tab. The student enters the new password on the Student Portal sign-in page; the existing password is never displayed.
- The **Clear all data** action in the **Students** tab requires the administrator's password and the exact phrase `DELETE ALL DATA`. It permanently deletes student profiles and face data, enrollments, subjects/classes, sessions, and attendance records. Administrator accounts are retained so the dashboard remains accessible.

---

## 🧠 Face Recognition Approach

**Model**: dlib's ResNet-based face recognition model

**Pipeline**:
1. **Detection**: dlib's frontal face HOG detector
2. **Landmarks**: 68-point facial landmark predictor
3. **Embedding**: 128-dimensional face descriptor (ResNet)
4. **Classification**: Linear SVM (scikit-learn) for candidate selection
5. **Verification**: Euclidean distance between embeddings

**Metric**: Euclidean distance
- Same person: typically < 0.6
- Different person: typically > 0.6
- Confidence = `max(0, 1.0 - distance / threshold)`

The system uses **both** SVM prediction and nearest-neighbor verification for robustness.

---

## ✨ Liveness Approach

Two complementary approaches:

### 1. Passive Anti-Spoofing
- **Laplacian variance** — measures texture complexity (real faces have more micro-texture than prints)
- **Edge density** — Canny edge analysis
- No user interaction required

### 2. Challenge-Based (Interactive)
- **Blink detection** — Eye Aspect Ratio (EAR) using dlib landmarks (indices 36-47)
- **Head turn** — Yaw angle estimation from nose/jaw landmark asymmetry
- Random challenge selection: BLINK, TURN_LEFT, TURN_RIGHT
- Configurable timeout

> **Limitation**: These are heuristic methods. They provide a reasonable defense against casual attacks (printed photos, static screens) but are not equivalent to commercial anti-spoofing solutions with depth cameras or infrared sensors.

---

## 📊 Confidence-Based Review

| Confidence Range | Decision | Action |
|-----------------|----------|--------|
| ≥ 40%, identified match | `APPROVED` | Auto-marked present |
| < 40%, identified match | `MANUAL_REVIEW` | Saved pending an administrator decision |
| Identity not matched | `UNKNOWN` | No attendance record is created |
| Liveness failure | `REJECTED` | Attendance denied |

The auto-approval threshold is configurable with `CONFIDENCE_HIGH_THRESHOLD`. The `CONFIDENCE_BORDERLINE_THRESHOLD` setting remains in older environment files for compatibility but is no longer used by the decision engine. Administrators can review pending rows in the dashboard's **Attendance** tab and change their status to Present or Absent.

---

## 📖 API Documentation

Full interactive API docs are auto-generated by FastAPI:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register teacher |
| POST | `/api/auth/login` | Login (get JWT) |
| POST | `/api/students` | Register student |
| POST | `/api/students/{id}/enroll-face` | Enroll face |
| POST | `/api/recognition/detect` | Detect faces |
| POST | `/api/recognition/recognize` | Recognize identity |
| POST | `/api/liveness/challenge` | Create liveness challenge |
| POST | `/api/liveness/verify` | Verify liveness frame |
| POST | `/api/attendance/mark` | Full attendance pipeline |
| POST | `/api/sessions` | Create session |
| GET | `/api/admin/dashboard` | Dashboard stats |
| GET | `/api/admin/attendance` | Attendance report; derives absences for completed sessions when filtering by Absent |
| PUT | `/api/admin/students/{id}/password` | Set a student's password (teacher/admin authentication required) |
| DELETE | `/api/admin/data` | Clear operational data (password and phrase confirmation required) |

---

## 🧪 Testing

### Run Decision Engine Tests
```bash
cd backend
python -m pytest tests/test_decision_engine.py -v
```

### Run API Tests
```bash
cd backend
python -m pytest tests/test_api.py -v
```

### Run All Tests
```bash
cd backend
python -m pytest tests/ -v
```

Tests cover:
- ✅ Student registration & duplicate prevention
- ✅ Face detection (no face, multiple faces, low quality)
- ✅ Recognition (success, unknown)
- ✅ Liveness (pass, fail)
- ✅ High-confidence auto-approve
- ✅ Low-confidence manual review for identified matches
- ✅ Unknown-face and liveness-failure handling
- ✅ Duplicate attendance prevention
- ✅ Session validation
- ✅ Invalid API requests (422, 401, 404)

---

## ⚠️ Known Limitations

1. **Liveness detection is heuristic-based** — texture analysis and EAR are not foolproof against sophisticated attacks (e.g., video replay, 3D masks). Commercial-grade liveness requires depth cameras or IR sensors.

2. **Single embedding per student** — currently stores one face embedding per student. Multiple embeddings (different angles, lighting) would improve robustness.

3. **SVM requires 2+ students** — the SVM classifier needs at least 2 registered students. With 1 student, it falls back to direct distance comparison.

4. **dlib model size** — the face recognition models are ~100MB. First startup may be slow.

5. **No real-time video streaming** — the system captures individual frames at intervals rather than streaming continuous video. This is by design to reduce server load.

6. **SQLite for production** — SQLite is suitable for development and small deployments. For larger deployments, configure `DATABASE_URL` for PostgreSQL.

---

## 👥 Team

| Name | Role |
|------|------|
| Yash Umdale | Developer |

> **Final Year Project**
> *Walchand Institute of Technology, Solapur*

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/Yash-Umdale">Yash Umdale</a>
</p>
