"""
VeriAttend — SQLAlchemy Database Models

All database tables and their relationships. Uses SQLite by default,
configurable to PostgreSQL via DATABASE_URL environment variable.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, Text, JSON, ForeignKey, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy import inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from config import settings

# ── Database Engine ──
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Enums ──

class AttendanceStatus(str, enum.Enum):
    """Status of an attendance record."""
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REJECTED = "REJECTED"




class VerificationMethod(str, enum.Enum):
    """How attendance was verified."""
    AUTO_HIGH_CONFIDENCE = "AUTO_HIGH_CONFIDENCE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    ADMIN_OVERRIDE = "ADMIN_OVERRIDE"


class LivenessResult(str, enum.Enum):
    """Result of liveness verification."""
    PASS_ = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"
    NOT_CHECKED = "NOT_CHECKED"


# ── Models ──

class Teacher(Base):
    """Teacher/admin accounts with password authentication."""
    __tablename__ = "teachers"

    teacher_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    subjects = relationship("Subject", back_populates="teacher")


class Student(Base):
    """Student profiles with biometric embeddings."""
    __tablename__ = "students"

    student_id = Column(Integer, primary_key=True, autoincrement=True)
    student_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=True)
    mobile_number = Column(String(20), nullable=True)
    department = Column(String(200), nullable=True)
    year = Column(String(50), nullable=True)
    # Student credentials and account lifecycle.  Attendance rows deliberately
    # remain related to this profile after it is deactivated.
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    deregistered_at = Column(DateTime, nullable=True)

    # Face embedding stored as JSON array of 128 floats
    face_embedding = Column(JSON, nullable=True)


    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    enrollments = relationship("SubjectStudent", back_populates="student")
    attendance_records = relationship("AttendanceRecord", back_populates="student")


class Subject(Base):
    """Courses/subjects created by teachers."""
    __tablename__ = "subjects"

    subject_id = Column(Integer, primary_key=True, autoincrement=True)
    subject_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    section = Column(String(50), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.teacher_id"), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    teacher = relationship("Teacher", back_populates="subjects")
    enrollments = relationship("SubjectStudent", back_populates="subject")
    sessions = relationship("AttendanceSession", back_populates="subject")
    attendance_records = relationship("AttendanceRecord", back_populates="subject")


class SubjectStudent(Base):
    """Many-to-many junction: students enrolled in subjects."""
    __tablename__ = "subject_students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False)
    enrolled_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint("subject_id", "student_id", name="uq_subject_student"),
    )

    # Relationships
    subject = relationship("Subject", back_populates="enrollments")
    student = relationship("Student", back_populates="enrollments")


class AttendanceSession(Base):
    """Attendance session — a time window during which attendance can be taken."""
    __tablename__ = "attendance_sessions"

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id"), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")
    deleted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("teachers.teacher_id"), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    subject = relationship("Subject", back_populates="sessions")
    teacher = relationship("Teacher")
    attendance_records = relationship("AttendanceRecord", back_populates="session")


class AttendanceRecord(Base):
    """
    Individual attendance record with full verification metadata.

    Every attendance attempt is recorded with:
    - Recognition confidence score
    - Liveness verification result
    - How the decision was made (auto vs manual review)
    - Review status if manual review was required
    """
    __tablename__ = "attendance_records"

    attendance_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id"), nullable=False)
    session_id = Column(Integer, ForeignKey("attendance_sessions.session_id"), nullable=True)

    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    timestamp = Column(DateTime, nullable=False, default=func.now())

    # Recognition metadata
    recognition_confidence = Column(Float, nullable=True)
    liveness_score = Column(Float, nullable=True)
    liveness_status = Column(String(20), default="NOT_CHECKED")

    # Decision
    status = Column(String(20), nullable=False, default="PRESENT")
    verification_method = Column(String(30), nullable=False, default="AUTO_HIGH_CONFIDENCE")
    review_status = Column(String(20), default="PENDING")

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        # Prevent duplicate attendance per student per session
        UniqueConstraint("student_id", "session_id", name="uq_student_session_attendance"),
    )

    # Relationships
    student = relationship("Student", back_populates="attendance_records")
    subject = relationship("Subject", back_populates="attendance_records")
    session = relationship("AttendanceSession", back_populates="attendance_records")



# ── Database Initialization ──

def init_db():
    """Create tables and apply the small backwards-compatible SQLite migration."""
    Base.metadata.create_all(bind=engine)
    # This project does not use Alembic yet.  Existing copied databases need
    # these additive columns; no attendance data is altered by this migration.
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("students")}
    additions = {
        "password_hash": "VARCHAR(255)",
        "is_active": "BOOLEAN NOT NULL DEFAULT 1",
        "deregistered_at": "DATETIME",
        "mobile_number": "VARCHAR(20)",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE students ADD COLUMN {name} {definition}"))
        connection.execute(text("UPDATE students SET is_active = 1 WHERE is_active IS NULL"))
    session_columns = {column["name"] for column in inspector.get_columns("attendance_sessions")}
    with engine.begin() as connection:
        if "is_deleted" not in session_columns:
            connection.execute(text("ALTER TABLE attendance_sessions ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0"))
        if "deleted_at" not in session_columns:
            connection.execute(text("ALTER TABLE attendance_sessions ADD COLUMN deleted_at DATETIME"))


def get_db():
    """Dependency for FastAPI: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
