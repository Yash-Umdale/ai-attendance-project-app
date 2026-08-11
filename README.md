# 📸 SnapClass — AI-Powered Smart Attendance System

<p align="center">
  <img src="https://i.ibb.co/YTYGn5qV/logo.png" alt="SnapClass Logo" width="120"/>
</p>

<p align="center">
  <b>Making classroom attendance faster, smarter, and contact-free using AI</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Supabase-Database-3ECF8E?logo=supabase&logoColor=white" />
  <img src="https://img.shields.io/badge/dlib-Face%20Recognition-orange" />
  <img src="https://img.shields.io/badge/License-Academic-lightgrey" />
</p>

---

## 📌 Table of Contents

- [About the Project](#-about-the-project)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [System Architecture](#-system-architecture)
- [Database Schema](#-database-schema)
- [AI Pipelines](#-ai-pipelines)
- [Project Structure](#-project-structure)
- [Installation & Setup](#-installation--setup)
- [How to Run](#-how-to-run)
- [Usage Guide](#-usage-guide)
- [Screenshots](#-screenshots)
- [Team Members](#-team-members)

---

## 🎯 About the Project

**SnapClass** is an AI-powered attendance management system designed as a Final Year Project. It eliminates the need for traditional roll calls by using **Face Recognition** and **Voice Recognition** technologies to automatically detect and mark student attendance from classroom photos or audio recordings.

### Problem Statement

Traditional attendance methods are:
- ⏱️ Time-consuming (5–10 minutes per class)
- 📝 Prone to proxy attendance
- 📊 Difficult to analyze and track over time

### Our Solution

SnapClass provides:
- 📸 **Face-based attendance** — Upload or capture classroom photos; AI identifies enrolled students
- 🎤 **Voice-based attendance** — Record classroom audio; AI matches student voiceprints
- 📱 **QR Code enrollment** — Students scan a QR code to instantly join a subject
- 📊 **Attendance analytics** — Teachers view real-time attendance records and statistics

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔐 **Face ID Login** | Students log in using their face — no passwords needed |
| 👨‍🏫 **Teacher Dashboard** | Create subjects, take attendance, view records |
| 👩‍🎓 **Student Dashboard** | Enroll in subjects, view attendance stats |
| 📸 **AI Face Attendance** | Upload classroom photos → AI marks present/absent |
| 🎤 **AI Voice Attendance** | Record audio → AI identifies speakers by voiceprint |
| 📱 **QR Code Sharing** | Teachers generate QR codes for easy student enrollment |
| 🔒 **Secure Auth** | Teacher passwords hashed with bcrypt |
| 📊 **Attendance Records** | Time-stamped records with present/absent stats |

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Streamlit | Web UI framework |
| **Backend** | Python 3.10+ | Application logic |
| **Database** | Supabase (PostgreSQL) | Cloud database & storage |
| **Face Recognition** | dlib + face_recognition_models | Face detection & 128D embeddings |
| **Face Classification** | scikit-learn (SVM) | Classify face embeddings to student IDs |
| **Voice Recognition** | Resemblyzer + Librosa | Speaker identification via voice embeddings |
| **Authentication** | bcrypt | Password hashing for teachers |
| **QR Codes** | Segno + Pillow | Generate shareable QR codes |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    STREAMLIT WEB APP                     │
│                                                         │
│   ┌──────────┐   ┌──────────────┐   ┌──────────────┐   │
│   │   Home   │   │   Teacher    │   │   Student    │   │
│   │  Screen  │   │   Screen     │   │   Screen     │   │
│   └────┬─────┘   └──────┬───────┘   └──────┬───────┘   │
│        │                │                   │           │
│   ┌────▼────────────────▼───────────────────▼────────┐  │
│   │              COMPONENT LAYER                     │  │
│   │  Dialogs · Headers · Footers · Subject Cards     │  │
│   └──────────────────────┬───────────────────────────┘  │
│                          │                              │
│   ┌──────────────────────▼───────────────────────────┐  │
│   │              AI PIPELINE LAYER                   │  │
│   │                                                  │  │
│   │  ┌─────────────────┐   ┌──────────────────────┐  │  │
│   │  │ Face Pipeline   │   │  Voice Pipeline      │  │  │
│   │  │ dlib → SVM      │   │  Resemblyzer         │  │  │
│   │  │ 128D Embeddings │   │  Speaker Embedding   │  │  │
│   │  └─────────────────┘   └──────────────────────┘  │  │
│   └──────────────────────┬───────────────────────────┘  │
│                          │                              │
│   ┌──────────────────────▼───────────────────────────┐  │
│   │              DATABASE LAYER                      │  │
│   │         Supabase (PostgreSQL Cloud)              │  │
│   └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│   teachers   │       │    subjects      │       │   students   │
├──────────────┤       ├──────────────────┤       ├──────────────┤
│ teacher_id   │──┐    │ subject_id       │    ┌──│ student_id   │
│ username     │  │    │ subject_code     │    │  │ name         │
│ password     │  └───▶│ name             │    │  │ face_embedding│
│ name         │       │ section          │    │  │ voice_embedding│
└──────────────┘       │ teacher_id (FK)  │    │  └──────────────┘
                       └────────┬─────────┘    │
                                │              │
                    ┌───────────▼──────────┐   │
                    │  subject_students    │   │
                    ├──────────────────────┤   │
                    │ subject_id (FK)      │◀──┘
                    │ student_id (FK)      │
                    └───────────┬──────────┘
                                │
                    ┌───────────▼──────────┐
                    │  attendance_logs     │
                    ├──────────────────────┤
                    │ student_id (FK)      │
                    │ subject_id (FK)      │
                    │ timestamp            │
                    │ is_present           │
                    └──────────────────────┘
```

### Table Descriptions

| Table | Description |
|-------|-------------|
| `teachers` | Stores teacher accounts with hashed passwords |
| `students` | Stores student profiles with 128D face embeddings and voice embeddings |
| `subjects` | Courses/subjects created by teachers |
| `subject_students` | Many-to-many junction table linking students ↔ subjects |
| `attendance_logs` | Individual attendance records with timestamps |

---

## 🤖 AI Pipelines

### Face Recognition Pipeline

```
Classroom Photo
      │
      ▼
┌─────────────┐     ┌───────────────┐     ┌──────────────┐
│ dlib Face   │────▶│ Shape         │────▶│ 128D Face    │
│ Detector    │     │ Predictor     │     │ Descriptor   │
└─────────────┘     └───────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │  SVM Linear  │
                                          │  Classifier  │
                                          └──────┬───────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │ Distance     │
                                          │ Threshold    │
                                          │ (≤ 0.6)     │
                                          └──────┬───────┘
                                                  │
                                                  ▼
                                          Student ID(s)
```

**How it works:**
1. **Detection** — dlib's frontal face detector locates faces in the image
2. **Landmark Prediction** — 68-point facial landmarks are extracted using a shape predictor
3. **Embedding** — Each face is converted into a 128-dimensional feature vector
4. **Classification** — An SVM classifier (trained on enrolled students) predicts the student ID
5. **Verification** — Euclidean distance between predicted and stored embeddings must be ≤ 0.6

### Voice Recognition Pipeline

```
Classroom Audio
      │
      ▼
┌─────────────┐     ┌───────────────┐     ┌──────────────┐
│ Librosa     │────▶│ Voice Activity│────▶│ Resemblyzer  │
│ Audio Load  │     │ Detection     │     │ Embedding    │
│ (16kHz)     │     │ (split @30dB) │     │ (per segment)│
└─────────────┘     └───────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │ Cosine       │
                                          │ Similarity   │
                                          │ (≥ 0.65)    │
                                          └──────┬───────┘
                                                  │
                                                  ▼
                                          Student ID(s)
```

**How it works:**
1. **Loading** — Audio is loaded at 16kHz using Librosa
2. **Segmentation** — Voice Activity Detection splits audio into speech segments (≥ 0.5s)
3. **Embedding** — Each segment is converted to a voice embedding using Resemblyzer
4. **Matching** — Cosine similarity is computed against enrolled students' voice profiles
5. **Threshold** — Similarity score ≥ 0.65 confirms a match

---

## 📁 Project Structure

```
ai-attendance-project-app/
│
├── app.py                          # Main entry point
├── requirements.txt                # Python dependencies
├── README.md                       # This file
│
├── .streamlit/
│   └── secrets.toml                # Supabase credentials (not committed)
│
└── src/
    ├── screens/
    │   ├── home_screen.py          # Landing page (Student / Teacher selection)
    │   ├── teacher_screen.py       # Teacher login, register & dashboard
    │   └── student_screen.py       # Student Face-ID login & dashboard
    │
    ├── components/
    │   ├── header.py               # App logo & header components
    │   ├── footer.py               # Footer with credits
    │   ├── subject_card.py         # Reusable subject card widget
    │   ├── dialog_create_subject.py    # Create new subject dialog
    │   ├── dialog_share_subject.py     # QR code sharing dialog
    │   ├── dialog_add_photo.py         # Camera/upload photo dialog
    │   ├── dialog_enroll.py            # Manual enrollment dialog
    │   ├── dialog_auto_enroll.py       # QR-based auto enrollment
    │   ├── dialog_attendance_results.py # Attendance results review
    │   └── dialog_voice_attendance.py  # Voice attendance dialog
    │
    ├── pipelines/
    │   ├── face_pipeline.py        # Face detection, embedding & classification
    │   └── voice_pipeline.py       # Voice embedding & speaker identification
    │
    ├── database/
    │   ├── config.py               # Supabase client initialization
    │   └── db.py                   # All database CRUD operations
    │
    └── ui/
        └── base_layout.py          # Global CSS styles & theming
```

---

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- A [Supabase](https://supabase.com) account (free tier works)
- CMake (required for dlib compilation)

### Step 1: Clone the Repository

```bash
git clone https://github.com/Yash-Umdale/ai-attendance-project-app.git
cd ai-attendance-project-app
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** Installing `dlib` requires CMake. On Windows, install [CMake](https://cmake.org/download/) and add it to PATH before running pip install.

### Step 4: Set Up Supabase

1. Create a new project on [Supabase](https://supabase.com)
2. Create the following tables in the SQL Editor:

```sql
-- Teachers table
CREATE TABLE teachers (
    teacher_id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    name TEXT NOT NULL
);

-- Students table
CREATE TABLE students (
    student_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    face_embedding JSONB,
    voice_embedding JSONB
);

-- Subjects table
CREATE TABLE subjects (
    subject_id BIGSERIAL PRIMARY KEY,
    subject_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    section TEXT NOT NULL,
    teacher_id BIGINT REFERENCES teachers(teacher_id)
);

-- Subject-Student enrollment (many-to-many)
CREATE TABLE subject_students (
    id BIGSERIAL PRIMARY KEY,
    subject_id BIGINT REFERENCES subjects(subject_id),
    student_id BIGINT REFERENCES students(student_id),
    UNIQUE(subject_id, student_id)
);

-- Attendance logs
CREATE TABLE attendance_logs (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT REFERENCES students(student_id),
    subject_id BIGINT REFERENCES subjects(subject_id),
    timestamp TIMESTAMPTZ NOT NULL,
    is_present BOOLEAN DEFAULT FALSE
);
```

### Step 5: Configure Secrets

Create `.streamlit/secrets.toml` with your Supabase credentials:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key-here"
```

---

## 🚀 How to Run

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 📖 Usage Guide

### For Teachers

1. **Register** — Create an account with username and password
2. **Login** — Access the teacher dashboard
3. **Create Subject** — Add subjects with code, name, and section
4. **Share Subject** — Generate QR codes for students to scan and enroll
5. **Take Attendance** — Choose a method:
   - 📸 **Face Attendance**: Upload/capture classroom photos → AI identifies students
   - 🎤 **Voice Attendance**: Record classroom audio → AI matches voiceprints
6. **Review & Confirm** — Check AI results and save attendance
7. **View Records** — Browse historical attendance data with statistics

### For Students

1. **Face-ID Login** — Use the camera to log in with your face
2. **First-Time Registration** — Capture face photo + optional voice enrollment
3. **Enroll in Subjects** — Enter subject code or scan teacher's QR code
4. **View Dashboard** — Check enrolled subjects and attendance stats

---

## 📸 Screenshots

> Screenshots can be added here after running the application.

| Screen | Description |
|--------|-------------|
| Home Screen | Student/Teacher portal selection |
| Teacher Dashboard | Subject management & attendance tabs |
| Face Attendance | Upload photos for AI-powered attendance |
| Voice Attendance | Record audio for voiceprint matching |
| Student Dashboard | Enrolled subjects & attendance stats |
| QR Code Sharing | Shareable QR codes for subject enrollment |

---

## 👥 Team Members

| Name | Role |
|------|------|
| Yash Umdale | Developer |

> **Final Year Project**
> *Walchand Institute of Technology, Solapur*
> *Department of Computer Science / Information Technology*

---

## 📜 License

This project is developed for academic purposes as a Final Year Project.

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/Yash-Umdale">Yash Umdale</a> using Streamlit & AI
</p>