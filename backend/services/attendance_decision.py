"""
VeriAttend — Attendance Decision Engine

Dedicated decision layer that combines:
- Face detection result
- Liveness verification result
- Face recognition result
- Recognition confidence
- Duplicate attendance check
- Session status

Produces an explicit, testable attendance decision.

This module does NOT directly interact with the database for marking attendance.
It only produces the DECISION — the router is responsible for persisting it.
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from config import settings
from models.database import AttendanceRecord, AttendanceSession, SubjectStudent

logger = logging.getLogger(__name__)


class AttendanceDecisionInput:
    """Structured input for the decision engine."""

    def __init__(
        self,
        face_detection_status: str,
        face_count: int,
        liveness_status: str,
        liveness_score: float,
        recognition_result: dict,
        session_id: int | None,
        db: Session,
    ):
        self.face_detection_status = face_detection_status
        self.face_count = face_count
        self.liveness_status = liveness_status
        self.liveness_score = liveness_score
        self.recognition_result = recognition_result
        self.session_id = session_id
        self.db = db


def make_attendance_decision(input_data: AttendanceDecisionInput) -> dict:
    """
    Core attendance decision logic.

    Decision tree:
        1. Check face detection → reject if NO_FACE, MULTIPLE_FACES, LOW_QUALITY
        2. Check liveness → reject if FAIL
        3. Check recognition → reject if not recognized (UNKNOWN)
        4. Check confidence:
            - HIGH (≥ high_threshold) → APPROVED (auto-mark)
            - LOWER (< high_threshold) → MANUAL_REVIEW
        5. Check duplicate → reject if already marked in this session
        6. Check session active → reject if session expired

    Returns:
        dict with decision, reason, and all supporting data
    """
    result = {
        "decision": "REJECTED",
        "reason": "",
        "student_id": None,
        "student_code": None,
        "student_name": None,
        "recognition_confidence": 0.0,
        "liveness_status": input_data.liveness_status,
        "liveness_score": input_data.liveness_score,
        "attendance_id": None,
    }

    # ── Step 1: Face Detection ──
    detection_status = input_data.face_detection_status

    if detection_status == "NO_FACE":
        result["reason"] = "No face detected in the frame."
        result["decision"] = "REJECTED"
        return result

    if detection_status == "MULTIPLE_FACES":
        result["reason"] = f"Multiple faces detected ({input_data.face_count}). Only one face allowed."
        result["decision"] = "REJECTED"
        return result

    if detection_status == "LOW_QUALITY":
        result["reason"] = "Image quality too low for reliable recognition."
        result["decision"] = "REJECTED"
        return result

    # ── Step 2: Liveness ──
    if input_data.liveness_status == "FAIL":
        result["reason"] = "Liveness verification failed. Possible presentation attack."
        result["decision"] = "REJECTED"
        return result

    # ── Step 3: Recognition ──
    rec = input_data.recognition_result
    if not rec.get("recognized"):
        result["reason"] = rec.get("message", "Face not recognized.")
        result["decision"] = "UNKNOWN"
        result["recognition_confidence"] = rec.get("confidence", 0.0)
        return result

    # We have a recognized student
    student_id = rec["student_id"]
    confidence = rec["confidence"]

    result["student_id"] = student_id
    result["student_code"] = rec.get("student_code")
    result["student_name"] = rec.get("name")
    result["recognition_confidence"] = confidence

    # ── Step 4: Check Session ──
    if input_data.session_id:
        session = input_data.db.query(AttendanceSession).filter(
            AttendanceSession.session_id == input_data.session_id,
            AttendanceSession.is_deleted.is_(False),
        ).first()

        if not session:
            result["reason"] = "Attendance session not found."
            result["decision"] = "REJECTED"
            return result

        if not session.is_active:
            result["reason"] = "Attendance session is not active."
            result["decision"] = "REJECTED"
            return result

        now = datetime.now()
        if now < session.start_time or now > session.end_time:
            result["reason"] = "Attendance session is outside its scheduled time window."
            result["decision"] = "REJECTED"
            return result

        enrollment = input_data.db.query(SubjectStudent).filter(
            SubjectStudent.subject_id == session.subject_id,
            SubjectStudent.student_id == student_id,
        ).first()
        if not enrollment:
            result["reason"] = "Student is not enrolled in this subject."
            result["decision"] = "REJECTED"
            return result

    # ── Step 5: Check Duplicate ──
    if settings.PREVENT_DUPLICATE_ATTENDANCE and input_data.session_id:
        existing = input_data.db.query(AttendanceRecord).filter(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.session_id == input_data.session_id,
            AttendanceRecord.status.in_(["PRESENT", "MANUAL_REVIEW"]),
        ).first()

        if existing:
            result["reason"] = "Attendance already marked for this session."
            result["decision"] = "DUPLICATE"
            result["attendance_id"] = existing.attendance_id
            return result

    # ── Step 6: Confidence-Based Decision ──
    high_threshold = settings.CONFIDENCE_HIGH_THRESHOLD

    if confidence >= high_threshold:
        result["decision"] = "APPROVED"
        result["reason"] = f"High confidence recognition ({confidence:.0%}). Attendance auto-approved."
        logger.info(
            f"APPROVED: student_id={student_id}, confidence={confidence:.4f}"
        )

    else:
        result["decision"] = "MANUAL_REVIEW"
        result["reason"] = (
            f"Low recognition confidence ({confidence:.0%}). Sent to manual review."
        )
        logger.info(
            f"MANUAL_REVIEW (low confidence): student_id={student_id}, confidence={confidence:.4f}"
        )

    return result
