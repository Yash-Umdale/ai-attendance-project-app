"""
VeriAttend — Admin Routes

GET  /api/admin/dashboard     — Dashboard statistics
POST /api/admin/subjects      — Create a subject
GET  /api/admin/subjects      — List teacher's subjects
GET  /api/admin/attendance    — Get detailed attendance report
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from models.database import (
    Teacher, Student, Subject, SubjectStudent,
    AttendanceRecord, AttendanceSession, get_db,
)
from models.schemas import (
    DashboardStats, SubjectCreateRequest, SubjectResponse,
    AttendanceRecordResponse, StudentResponse, SuccessResponse,
    AdminStudentPasswordResetRequest, AdminClearDataRequest,
)
from services.auth import get_current_teacher, hash_password, verify_password

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])


@router.get(
    "/students",
    response_model=list[StudentResponse],
    summary="Administrator student information",
)
def get_student_information(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Return student profile information for the administrator dashboard.

    Passwords and biometric vectors are intentionally excluded. Passwords are
    securely hashed and must never be retrievable by any user or administrator.
    """
    students = db.query(Student).order_by(Student.name.asc()).all()
    return [
        StudentResponse(
            student_id=student.student_id,
            student_code=student.student_code,
            name=student.name,
            email=student.email,
            mobile_number=getattr(student, 'mobile_number', None),
            department=student.department,
            year=student.year,
            has_face_embedding=student.face_embedding is not None,
            is_active=bool(student.is_active),
            account_status="Active" if student.is_active else "Deregistered",
            created_at=student.created_at,
        )
        for student in students
    ]


@router.put(
    "/students/{student_id}/password",
    response_model=SuccessResponse,
    summary="Set a student's password",
)
def reset_student_password(
    student_id: int,
    req: AdminStudentPasswordResetRequest,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Set a new password for a student from the authenticated admin dashboard."""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    if not student.is_active:
        raise HTTPException(status_code=400, detail="Deregistered student accounts cannot sign in.")

    student.password_hash = hash_password(req.password)
    db.commit()
    return SuccessResponse(message="Student password updated. Share the new password with the student securely.")


@router.delete(
    "/data",
    response_model=SuccessResponse,
    summary="Clear student, class, session, and attendance data",
)
def clear_application_data(
    req: AdminClearDataRequest,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Delete operational data only after password and typed-phrase confirmation."""
    if not verify_password(req.password, teacher.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Administrator password is incorrect.")
    if req.confirmation.strip() != "DELETE ALL DATA":
        raise HTTPException(status_code=400, detail="Type DELETE ALL DATA exactly to confirm.")

    # Delete children before parents to satisfy the database foreign keys.
    db.query(AttendanceRecord).delete(synchronize_session=False)
    db.query(AttendanceSession).delete(synchronize_session=False)
    db.query(SubjectStudent).delete(synchronize_session=False)
    db.query(Subject).delete(synchronize_session=False)
    db.query(Student).delete(synchronize_session=False)
    db.commit()

    return SuccessResponse(message="Student, class, session, and attendance data cleared. Administrator accounts were kept.")


@router.get(
    "/dashboard",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
    description="Returns aggregate statistics for the admin dashboard.",
)
def get_dashboard_stats(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Get overview statistics for the admin dashboard."""
    today = datetime.now().strftime("%Y-%m-%d")

    teacher_subject_ids = [
        row[0] for row in db.query(Subject.subject_id).filter(
            Subject.teacher_id == teacher.teacher_id
        ).all()
    ]
    enrolled_student_ids = [
        row[0] for row in db.query(SubjectStudent.student_id).filter(
            SubjectStudent.subject_id.in_(teacher_subject_ids)
        ).distinct().all()
    ]
    total_students = len(enrolled_student_ids)

    # Students marked present today
    present_today = db.query(AttendanceRecord.student_id).filter(
        AttendanceRecord.subject_id.in_(teacher_subject_ids),
        AttendanceRecord.date == today,
        AttendanceRecord.status == "PRESENT",
    ).distinct().count()

    # Students with face embeddings but not present today
    enrolled_students_with_face = db.query(Student).filter(
        Student.student_id.in_(enrolled_student_ids),
        Student.face_embedding.isnot(None)
    ).count()
    absent_today = max(0, enrolled_students_with_face - present_today)

    pending_reviews = 0  # Simplified: manual review queue removed

    total_sessions = db.query(AttendanceSession).filter(
        AttendanceSession.created_by == teacher.teacher_id
    ).count()

    return DashboardStats(
        total_students=total_students,
        present_today=present_today,
        absent_today=absent_today,
        pending_reviews=pending_reviews,
        total_sessions=total_sessions,
    )


@router.post(
    "/subjects",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new subject",
)
def create_subject(
    req: SubjectCreateRequest,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Create a new subject/course for this teacher."""
    existing = db.query(Subject).filter(Subject.subject_code == req.subject_code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Subject code '{req.subject_code}' already exists.")

    subject = Subject(
        subject_code=req.subject_code,
        name=req.name,
        section=req.section,
        teacher_id=teacher.teacher_id,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)

    return SubjectResponse(
        subject_id=subject.subject_id,
        subject_code=subject.subject_code,
        name=subject.name,
        section=subject.section,
        teacher_id=subject.teacher_id,
        enrolled_count=0,
        created_at=subject.created_at,
    )


@router.get(
    "/subjects",
    response_model=list[SubjectResponse],
    summary="List teacher's subjects",
)
def list_subjects(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Get all subjects belonging to the authenticated teacher."""
    subjects = db.query(Subject).filter(
        Subject.teacher_id == teacher.teacher_id
    ).all()

    results = []
    for s in subjects:
        count = db.query(SubjectStudent).filter(
            SubjectStudent.subject_id == s.subject_id
        ).count()

        results.append(SubjectResponse(
            subject_id=s.subject_id,
            subject_code=s.subject_code,
            name=s.name,
            section=s.section,
            teacher_id=s.teacher_id,
            enrolled_count=count,
            created_at=s.created_at,
        ))

    return results


@router.get(
    "/attendance",
    response_model=list[AttendanceRecordResponse],
    summary="Get detailed attendance report",
    description="Filterable attendance report for admin dashboard.",
)
def get_attendance_report(
    subject_id: int = None,
    session_id: int = None,
    date: str = None,
    student_name: str = None,
    status_filter: str = None,
    limit: int = 200,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Get attendance records, deriving absences for enrolled students after a session ends."""
    # Only show records for teacher's subjects
    teacher_subject_ids = [
        s.subject_id for s in
        db.query(Subject).filter(Subject.teacher_id == teacher.teacher_id).all()
    ]

    query = db.query(AttendanceRecord).filter(
        AttendanceRecord.subject_id.in_(teacher_subject_ids)
    )

    if subject_id:
        query = query.filter(AttendanceRecord.subject_id == subject_id)
    if session_id:
        query = query.filter(AttendanceRecord.session_id == session_id)
    if date:
        query = query.filter(AttendanceRecord.date == date)
    if status_filter:
        query = query.filter(AttendanceRecord.status == status_filter.upper())

    records = query.order_by(AttendanceRecord.timestamp.desc()).limit(limit).all()

    results = []
    for r in records:
        student = db.query(Student).filter(Student.student_id == r.student_id).first()
        subject = db.query(Subject).filter(Subject.subject_id == r.subject_id).first()

        # Filter by student name if provided
        if student_name and student:
            if student_name.lower() not in student.name.lower():
                continue

        results.append(AttendanceRecordResponse(
            attendance_id=r.attendance_id,
            student_id=r.student_id,
            student_code=student.student_code if student else None,
            student_name=student.name if student else None,
            subject_id=r.subject_id,
            subject_name=subject.name if subject else None,
            session_id=r.session_id,
            date=r.date,
            timestamp=r.timestamp,
            recognition_confidence=r.recognition_confidence,
            liveness_score=r.liveness_score,
            liveness_status=r.liveness_status,
            status=r.status,
            verification_method=r.verification_method,
            review_status=r.review_status,
        ))

    # For the Absent filter, also show enrolled students with no attendance
    # attempt in a completed session. Do not synthesize absences for sessions
    # that are still in progress or scheduled for later.
    if status_filter and status_filter.upper() == "ABSENT":
        completed_sessions_query = db.query(AttendanceSession).filter(
            AttendanceSession.subject_id.in_(teacher_subject_ids),
            AttendanceSession.is_deleted.is_(False),
            AttendanceSession.end_time <= datetime.now(),
        )
        if subject_id:
            completed_sessions_query = completed_sessions_query.filter(
                AttendanceSession.subject_id == subject_id
            )
        if session_id:
            completed_sessions_query = completed_sessions_query.filter(
                AttendanceSession.session_id == session_id
            )
        if date:
            completed_sessions_query = completed_sessions_query.filter(
                AttendanceSession.date == date
            )

        completed_sessions = completed_sessions_query.order_by(
            AttendanceSession.end_time.desc()
        ).all()
        subject_names = {
            subject.subject_id: subject.name
            for subject in db.query(Subject).filter(
                Subject.subject_id.in_({session.subject_id for session in completed_sessions})
            ).all()
        } if completed_sessions else {}
        session_ids = [session.session_id for session in completed_sessions]
        recorded_pairs = set()
        if session_ids:
            recorded_pairs = {
                (record.session_id, record.student_id)
                for record in db.query(AttendanceRecord).filter(
                    AttendanceRecord.session_id.in_(session_ids)
                ).all()
            }

        for session in completed_sessions:
            enrollments = db.query(SubjectStudent).filter(
                SubjectStudent.subject_id == session.subject_id
            ).all()
            enrolled_ids = [enrollment.student_id for enrollment in enrollments]
            if not enrolled_ids:
                continue

            enrolled_students = db.query(Student).filter(
                Student.student_id.in_(enrolled_ids),
                Student.is_active.is_(True),
            ).all()
            for student in enrolled_students:
                if (session.session_id, student.student_id) in recorded_pairs:
                    continue
                if student_name and student_name.lower() not in student.name.lower():
                    continue

                results.append(AttendanceRecordResponse(
                    attendance_id=None,
                    student_id=student.student_id,
                    student_code=student.student_code,
                    student_name=student.name,
                    subject_id=session.subject_id,
                    subject_name=subject_names.get(session.subject_id),
                    session_id=session.session_id,
                    date=session.date,
                    timestamp=session.end_time,
                    recognition_confidence=None,
                    liveness_score=None,
                    liveness_status="NOT_CHECKED",
                    status="ABSENT",
                    verification_method="AUTO_ABSENT",
                    review_status="APPROVED",
                    is_derived_absence=True,
                ))

    results.sort(key=lambda record: record.timestamp, reverse=True)
    results = results[:max(1, min(limit, 500))]

    return results


@router.put(
    "/attendance/{attendance_id}/status",
    response_model=SuccessResponse,
    summary="Manually update attendance status (Present/Absent)",
)
def update_attendance_status(
    attendance_id: int,
    new_status: str,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Allow teachers to manually change an attendance record between PRESENT and ABSENT."""
    allowed = {"PRESENT", "ABSENT"}
    status_upper = new_status.strip().upper()
    if status_upper not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(allowed)}")

    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.attendance_id == attendance_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found.")

    # Only allow editing records for teacher's subjects
    teacher_subject_ids = [
        s.subject_id for s in
        db.query(Subject).filter(Subject.teacher_id == teacher.teacher_id).all()
    ]
    if record.subject_id not in teacher_subject_ids:
        raise HTTPException(status_code=403, detail="You can only edit records for your own subjects.")

    record.status = status_upper
    record.verification_method = "ADMIN_OVERRIDE"
    record.review_status = "APPROVED"
    db.commit()

    return SuccessResponse(message=f"Attendance updated to {status_upper}.")
