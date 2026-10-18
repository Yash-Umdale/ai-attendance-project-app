"""
VeriAttend — Student Routes

POST /api/students           — Register a new student
GET  /api/students           — List all students
GET  /api/students/{id}      — Get student by ID
PUT  /api/students/{id}      — Update student profile
POST /api/students/{id}/enroll-face — Enroll/re-enroll face embedding
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import numpy as np
import logging
import re

from models.database import AttendanceRecord, Student, Subject, SubjectStudent, Teacher, get_db
from models.schemas import (
    StudentRegisterRequest, StudentResponse, StudentUpdateRequest,
    EnrollFaceRequest, EnrollFaceResponse, ErrorResponse, SuccessResponse,
    StudentLoginRequest, StudentTokenResponse, DeregisterStudentRequest,
    AttendanceRecordResponse,
)
from services.face_detection import detect_faces, get_face_landmarks, compute_face_embedding
from services.face_recognition_service import invalidate_classifier_cache
from services.auth import hash_password, verify_password, create_access_token, get_current_student, get_current_teacher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/students", tags=["Students"])


def _student_response(student: Student) -> StudentResponse:
    """Keep active/deregistered status visible in admin and profile responses."""
    active = bool(student.is_active)
    return StudentResponse(
        student_id=student.student_id, student_code=student.student_code,
        name=student.name, email=student.email,
        mobile_number=getattr(student, 'mobile_number', None),
        department=student.department,
        year=student.year, has_face_embedding=student.face_embedding is not None,
        is_active=active, account_status="Active" if active else "Deregistered",
        created_at=student.created_at,
    )


from utils import decode_frame as _decode_frame


@router.post(
    "",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student",
    responses={409: {"model": ErrorResponse, "description": "Student ID already exists"}},
)
def register_student(req: StudentRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new student with their details.
    Face enrollment is done separately via the enroll-face endpoint.
    """
    # Prevent duplicate student codes
    student_code = req.student_code.strip()
    email = req.email.strip().lower() if req.email and req.email.strip() else None

    existing = db.query(Student).filter(Student.student_code == student_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student ID '{student_code}' already exists.",
        )

    if email and db.query(Student).filter(Student.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email address is already registered to another student.",
        )

    student = Student(
        student_code=student_code,
        name=req.name.strip(),
        email=email,
        mobile_number=req.mobile_number.strip() if req.mobile_number and req.mobile_number.strip() else None,
        department=req.department.strip() if req.department and req.department.strip() else None,
        year=req.year.strip() if req.year and req.year.strip() else None,
        password_hash=hash_password(req.password) if req.password else None,
    )
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A student with this ID or email address already exists.",
        )
    db.refresh(student)

    return _student_response(student)


@router.post("/login", response_model=StudentTokenResponse, summary="Student account login")
def login_student(req: StudentLoginRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.student_code == req.student_code.strip()).first()
    if not student or not student.password_hash or not verify_password(req.password, student.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid student ID or password.")
    if not student.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This student account has been deregistered.")
    return StudentTokenResponse(
        access_token=create_access_token(data={"sub": str(student.student_id), "role": "student"}),
        student_id=student.student_id, name=student.name,
    )


@router.get("/me", response_model=StudentResponse, summary="Get the current student profile")
def get_my_profile(student: Student = Depends(get_current_student)):
    return _student_response(student)


@router.get(
    "/me/attendance",
    response_model=list[AttendanceRecordResponse],
    summary="Get the signed-in student's attendance for one month",
)
def get_my_monthly_attendance(
    month: str,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Return only the caller's attendance records for ``YYYY-MM``.

    A student token is required, so changing a URL or request parameter cannot
    reveal another student's attendance history.
    """
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise HTTPException(status_code=400, detail="Month must use YYYY-MM format.")

    records = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.student_id == student.student_id,
            AttendanceRecord.date.like(f"{month}-%"),
        )
        .order_by(AttendanceRecord.date.desc(), AttendanceRecord.timestamp.desc())
        .all()
    )

    results = []
    for record in records:
        subject = db.query(Subject).filter(Subject.subject_id == record.subject_id).first()
        results.append(AttendanceRecordResponse(
            attendance_id=record.attendance_id,
            student_id=student.student_id,
            student_code=student.student_code,
            student_name=student.name,
            subject_id=record.subject_id,
            subject_name=subject.name if subject else "Unknown subject",
            session_id=record.session_id,
            date=record.date,
            timestamp=record.timestamp,
            recognition_confidence=record.recognition_confidence,
            liveness_score=record.liveness_score,
            liveness_status=record.liveness_status,
            status=record.status,
            verification_method=record.verification_method,
            review_status=record.review_status,
        ))
    return results


@router.get(
    "/me/attendance-summary",
    summary="Get attendance statistics for the current student",
)
def get_my_attendance_summary(
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Return overall and per-subject attendance percentages for the dashboard."""
    from models.database import AttendanceSession

    # All attendance records for this student
    all_records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.student_id == student.student_id)
        .all()
    )

    # Total sessions the student could have attended (subjects they are enrolled in)
    enrolled_subject_ids = [
        row.subject_id
        for row in db.query(SubjectStudent)
        .filter(SubjectStudent.student_id == student.student_id)
        .all()
    ]

    # Per-subject stats
    subject_stats = []
    total_sessions_count = 0
    total_present_count = 0

    for sub_id in enrolled_subject_ids:
        subject = db.query(Subject).filter(Subject.subject_id == sub_id).first()
        if not subject:
            continue
        # Count total unique sessions for this subject
        sessions_count = (
            db.query(AttendanceSession)
            .filter(
                AttendanceSession.subject_id == sub_id,
                AttendanceSession.is_deleted.is_(False),
            )
            .count()
        )
        present_count = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.student_id == student.student_id,
                AttendanceRecord.subject_id == sub_id,
                AttendanceRecord.status == "PRESENT",
            )
            .count()
        )
        percentage = round((present_count / sessions_count * 100), 1) if sessions_count > 0 else 0.0
        subject_stats.append({
            "subject_id": sub_id,
            "subject_name": subject.name,
            "subject_code": subject.subject_code,
            "section": subject.section,
            "total_sessions": sessions_count,
            "present_count": present_count,
            "absent_count": sessions_count - present_count,
            "percentage": percentage,
        })
        total_sessions_count += sessions_count
        total_present_count += present_count

    overall_percentage = round((total_present_count / total_sessions_count * 100), 1) if total_sessions_count > 0 else 0.0

    # Recent attendance history (last 50)
    recent = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.student_id == student.student_id)
        .order_by(AttendanceRecord.timestamp.desc())
        .limit(50)
        .all()
    )
    history = []
    for r in recent:
        subj = db.query(Subject).filter(Subject.subject_id == r.subject_id).first()
        history.append({
            "date": r.date,
            "subject_name": subj.name if subj else "Unknown",
            "status": r.status,
            "confidence": r.recognition_confidence,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        })

    return {
        "student_name": student.name,
        "student_code": student.student_code,
        "overall_percentage": overall_percentage,
        "total_sessions": total_sessions_count,
        "total_present": total_present_count,
        "total_absent": total_sessions_count - total_present_count,
        "subjects": subject_stats,
        "history": history,
    }


@router.delete("/me", response_model=SuccessResponse, summary="Deregister the current student account")
def deregister_my_account(
    req: DeregisterStudentRequest,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Soft-deactivate only the caller, retaining reportable attendance history."""
    if req.confirmation.strip().upper() != "DEREGISTER":
        raise HTTPException(status_code=400, detail="Type DEREGISTER to confirm account removal.")
    if not verify_password(req.password, student.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password confirmation is incorrect.")
    # Delete only active associations/biometrics. Attendance and review FKs stay intact.
    db.query(SubjectStudent).filter(SubjectStudent.student_id == student.student_id).delete()
    student.face_embedding = None
    student.is_active = False
    from datetime import datetime
    student.deregistered_at = datetime.utcnow()
    db.commit()
    invalidate_classifier_cache()
    logger.info("Student %s deregistered their account", student.student_id)
    return SuccessResponse(message="Account deregistered. Attendance history has been retained for reports.")


@router.get(
    "",
    response_model=list[StudentResponse],
    summary="List all registered students",
)
def list_students(db: Session = Depends(get_db)):
    """Get all registered students."""
    students = db.query(Student).all()
    return [_student_response(s) for s in students]


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Get a student by ID",
    responses={404: {"model": ErrorResponse}},
)
def get_student(student_id: int, db: Session = Depends(get_db)):
    """Get a specific student's profile."""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    return _student_response(student)


@router.put(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Update student profile",
    responses={404: {"model": ErrorResponse}},
)
def update_student(student_id: int, req: StudentUpdateRequest, db: Session = Depends(get_db)):
    """Update student profile fields."""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    # `model_fields_set` distinguishes an omitted field from an explicit null,
    # allowing an optional value such as email to be deliberately cleared.
    fields_set = req.model_fields_set
    if "name" in fields_set and req.name is not None:
        student.name = req.name.strip()
    if "email" in fields_set:
        email = req.email.strip().lower() if req.email and req.email.strip() else None
        if email:
            email_owner = db.query(Student).filter(
                Student.email == email,
                Student.student_id != student_id,
            ).first()
            if email_owner:
                raise HTTPException(status_code=409, detail="This email address is already registered to another student.")
        student.email = email
    if "department" in fields_set:
        student.department = req.department.strip() if req.department and req.department.strip() else None
    if "year" in fields_set:
        student.year = req.year.strip() if req.year and req.year.strip() else None

    db.commit()
    db.refresh(student)

    return _student_response(student)


@router.delete(
    "/{student_id}/face",
    response_model=SuccessResponse,
    summary="Administrator removes a student's enrolled face data",
)
def remove_student_face(
    student_id: int,
    subject_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Permanently erase face/voice biometrics for a student in the teacher's class.

    The student is also removed from that subject so they cannot mark attendance
    there. Their profile and historical attendance remain available for reports.
    """
    subject = db.query(Subject).filter(
        Subject.subject_id == subject_id,
        Subject.teacher_id == teacher.teacher_id,
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found or not managed by you.")

    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    enrollment = db.query(SubjectStudent).filter(
        SubjectStudent.subject_id == subject_id,
        SubjectStudent.student_id == student_id,
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Student is not enrolled in this subject.")

    db.delete(enrollment)
    student.face_embedding = None
    db.commit()
    invalidate_classifier_cache()
    logger.info("Teacher %s removed face data for student %s", teacher.teacher_id, student_id)
    return SuccessResponse(message="Face data erased and student removed from this subject. Attendance history was retained.")


@router.post(
    "/{student_id}/enroll-face",
    response_model=EnrollFaceResponse,
    summary="Enroll or re-enroll a student's face",
    description=(
        "Captures a face from the provided image frame, validates that exactly one face "
        "is present, generates a 128D embedding, and stores it for the student. "
        "Can be used for initial enrollment or re-enrollment."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid image or multiple faces"},
        404: {"model": ErrorResponse, "description": "Student not found"},
    },
)
def enroll_face(student_id: int, req: EnrollFaceRequest, db: Session = Depends(get_db)):
    """
    Enroll a student's face from a camera frame.

    Workflow:
        1. Decode the base64 image
        2. Detect faces — reject if 0 or >1 faces
        3. Check image quality
        4. Extract 68-point landmarks
        5. Compute 128D face embedding
        6. Store embedding (overwrites previous if re-enrolling)
        7. Invalidate classifier cache
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    if not student.is_active:
        raise HTTPException(status_code=403, detail="Deregistered students cannot enroll biometric data.")

    # Decode frame
    try:
        image_np = _decode_frame(req.frame_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")

    # Detect faces
    detection = detect_faces(image_np)

    if detection["status"] == "NO_FACE":
        raise HTTPException(status_code=400, detail="No face detected in the image.")
    if detection["status"] == "MULTIPLE_FACES":
        raise HTTPException(
            status_code=400,
            detail=f"Multiple faces detected ({detection['num_faces']}). Please capture with only one face.",
        )
    if detection["status"] == "LOW_QUALITY":
        raise HTTPException(status_code=400, detail="Image quality too low. Please try again.")

    # Get landmarks and compute embedding
    # Use high num_jitters (100) for enrollment — this is a one-time operation
    # per student and produces a much more stable/accurate reference embedding
    # that reduces misidentification during attendance.
    face_rect = detection["faces"][0]
    landmarks = get_face_landmarks(image_np, face_rect)
    embedding = compute_face_embedding(image_np, landmarks, num_jitters=100)

    # Store embedding (as list of floats)
    student.face_embedding = embedding.tolist()
    db.commit()

    # Invalidate classifier cache so it rebuilds with new embedding
    invalidate_classifier_cache()

    logger.info(f"Face enrolled for student {student.student_code} (id={student_id})")

    return EnrollFaceResponse(
        success=True,
        message="Face enrolled successfully.",
        student_id=student_id,
    )
