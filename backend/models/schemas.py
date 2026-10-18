"""
VeriAttend — Pydantic Schemas

Request/response schemas for all API endpoints.
Validates input data and shapes API output.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


# ══════════════════════════════════════
# Auth Schemas
# ══════════════════════════════════════

class TeacherRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, description="Unique username")
    password: str = Field(..., min_length=4, max_length=100, description="Password")
    name: str = Field(..., min_length=1, max_length=200, description="Full name")

class TeacherLoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    teacher_id: int
    name: str

class TeacherResponse(BaseModel):
    teacher_id: int
    username: str
    name: str

    model_config = ConfigDict(from_attributes=True)


# ══════════════════════════════════════
# Student Schemas
# ══════════════════════════════════════

class StudentRegisterRequest(BaseModel):
    student_code: str = Field(..., min_length=1, max_length=50, description="Unique Student ID")
    name: str = Field(..., min_length=1, max_length=200, description="Full name")
    email: Optional[str] = Field(None, max_length=200, description="Email address")
    mobile_number: Optional[str] = Field(None, max_length=20, description="Mobile number")
    department: Optional[str] = Field(None, max_length=200, description="Department")
    year: Optional[str] = Field(None, max_length=50, description="Class/year info")
    # Optional only to retain compatibility with profiles created before
    # student accounts existed. The current UI always requires it.
    password: Optional[str] = Field(None, min_length=4, max_length=100)

class StudentResponse(BaseModel):
    student_id: int
    student_code: str
    name: str
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    has_face_embedding: bool = False
    is_active: bool = True
    account_status: str = "Active"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class StudentUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None

class StudentLoginRequest(BaseModel):
    student_code: str
    password: str

class AdminStudentPasswordResetRequest(BaseModel):
    password: str = Field(..., min_length=4, max_length=100, description="New student password")

class AdminClearDataRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=100, description="Administrator password")
    confirmation: str = Field(..., description="Must be DELETE ALL DATA")

class StudentTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    student_id: int
    name: str

class DeregisterStudentRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=100)
    confirmation: str = Field(..., description="Must be DEREGISTER")


# ══════════════════════════════════════
# Face Detection Schemas
# ══════════════════════════════════════

class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int

class FaceDetectionResult(BaseModel):
    """Result from the face detection layer."""
    status: str = Field(..., description="NO_FACE | ONE_FACE | MULTIPLE_FACES | LOW_QUALITY")
    num_faces: int
    bounding_boxes: List[BoundingBox] = []
    message: str = ""


# ══════════════════════════════════════
# Face Recognition Schemas
# ══════════════════════════════════════

class RecognitionResult(BaseModel):
    """Result from the face recognition pipeline."""
    recognized: bool
    student_id: Optional[int] = None
    student_code: Optional[str] = None
    name: Optional[str] = None
    confidence: float = Field(..., description="Recognition confidence (0.0-1.0)")
    distance: float = Field(..., description="Raw Euclidean distance from embedding")
    message: str = ""


# ══════════════════════════════════════
# Liveness Schemas
# ══════════════════════════════════════

class LivenessChallenge(BaseModel):
    """A liveness challenge issued to the user."""
    challenge_id: str
    challenge_type: str = Field(..., description="BLINK | TURN_LEFT | TURN_RIGHT")
    instruction: str
    timeout_seconds: int

class LivenessVerificationRequest(BaseModel):
    """Frame data for liveness verification."""
    challenge_id: str
    frame_data: str = Field(..., description="Base64-encoded frame image")

class LivenessResult(BaseModel):
    """Result of liveness verification."""
    liveness: str = Field(..., description="PASS | FAIL | UNCERTAIN")
    score: float = Field(0.0, description="Liveness confidence score")
    challenge: Optional[str] = None
    message: str = ""


# ══════════════════════════════════════
# Enrollment Schemas
# ══════════════════════════════════════

class EnrollFaceRequest(BaseModel):
    """Request to enroll a student's face from a captured frame."""
    student_id: int
    frame_data: str = Field(..., description="Base64-encoded face image")

class EnrollFaceResponse(BaseModel):
    success: bool
    message: str
    student_id: int

class SubjectEnrollRequest(BaseModel):
    student_id: int
    subject_code: str


# ══════════════════════════════════════
# Attendance Decision Schemas
# ══════════════════════════════════════

class AttendanceDecision(BaseModel):
    """
    Complete attendance decision from the decision engine.
    This is the structured output after combining detection + liveness + recognition.
    """
    decision: str = Field(..., description="APPROVED | MANUAL_REVIEW | REJECTED | UNKNOWN | DUPLICATE")
    reason: str
    student_id: Optional[int] = None
    student_code: Optional[str] = None
    student_name: Optional[str] = None
    recognition_confidence: float = 0.0
    liveness_status: str = "NOT_CHECKED"
    liveness_score: float = 0.0
    attendance_id: Optional[int] = None

class AttendanceRequest(BaseModel):
    """Request to process an attendance frame."""
    session_id: int
    frame_data: str = Field(..., description="Base64-encoded camera frame")
    liveness_challenge_id: Optional[str] = None


# ══════════════════════════════════════
# Attendance Session Schemas
# ══════════════════════════════════════

class SessionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    subject_id: int
    date: str = Field(..., description="YYYY-MM-DD")
    start_time: str = Field(..., description="ISO datetime string")
    end_time: str = Field(..., description="ISO datetime string")

class SessionResponse(BaseModel):
    session_id: int
    name: str
    subject_id: int
    subject_name: Optional[str] = None
    date: str
    start_time: datetime
    end_time: datetime
    is_active: bool
    is_deleted: bool = False
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class SessionToggleRequest(BaseModel):
    is_active: bool


# ══════════════════════════════════════
# Attendance Record Schemas
# ══════════════════════════════════════

class AttendanceRecordResponse(BaseModel):
    attendance_id: Optional[int] = None
    student_id: int
    student_code: Optional[str] = None
    student_name: Optional[str] = None
    subject_id: int
    subject_name: Optional[str] = None
    session_id: Optional[int] = None
    date: str
    timestamp: datetime
    recognition_confidence: Optional[float] = None
    liveness_score: Optional[float] = None
    liveness_status: str = "NOT_CHECKED"
    status: str
    verification_method: str
    review_status: str = "PENDING"
    is_derived_absence: bool = False

    model_config = ConfigDict(from_attributes=True)


# ══════════════════════════════════════
# Manual Review Schemas
# ══════════════════════════════════════

class ReviewResponse(BaseModel):
    review_id: int
    attendance_id: int
    student_id: int
    student_code: Optional[str] = None
    student_name: Optional[str] = None
    session_id: Optional[int] = None
    recognition_confidence: float
    liveness_status: str
    liveness_score: Optional[float] = None
    status: str
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ReviewDecisionRequest(BaseModel):
    decision: str = Field(..., description="APPROVED or REJECTED")
    notes: Optional[str] = None


# ══════════════════════════════════════
# Admin Dashboard Schemas
# ══════════════════════════════════════

class DashboardStats(BaseModel):
    total_students: int
    present_today: int
    absent_today: int
    pending_reviews: int
    total_sessions: int

class SubjectCreateRequest(BaseModel):
    subject_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    section: str = Field(..., min_length=1, max_length=50)

class SubjectResponse(BaseModel):
    subject_id: int
    subject_code: str
    name: str
    section: str
    teacher_id: int
    enrolled_count: int = 0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ══════════════════════════════════════
# Generic Schemas
# ══════════════════════════════════════

class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: Optional[str] = None

class SuccessResponse(BaseModel):
    success: bool = True
    message: str
