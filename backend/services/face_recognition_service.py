"""
VeriAttend — Face Recognition Service

Identity recognition pipeline: compares a face embedding against
registered student embeddings to find the best match.

Uses Euclidean distance as the similarity metric.

Similarity metric:
    Euclidean distance between 128D face embeddings (dlib ResNet).
    - Same person: typically distance < 0.6
    - Different person: typically distance > 0.6
    - Confidence = max(0, 1.0 - distance / threshold)

Recognition approach:
    Pure nearest-neighbor search across all registered embeddings.
    An SVM is NOT used — with few students and one embedding each,
    nearest-neighbor is more reliable and deterministic.

    A margin check ensures the best match is significantly closer
    than the second-best to avoid ambiguous misidentification.
"""

import numpy as np
from sqlalchemy.orm import Session
import logging

from config import settings
from models.database import Student

logger = logging.getLogger(__name__)

# ── Embedding Cache ──
# Stores all registered embeddings so we don't hit the DB on every frame.
# Invalidated whenever a student enrolls/unenrolls their face.
_embedding_cache = None


def _build_embedding_cache(db: Session) -> dict | None:
    """
    Load all registered student embeddings from the database.

    Always rebuilds from the database to prevent stale data from causing
    misidentification. dlib's face-recognition threshold is calibrated for
    its original, unnormalised 128D descriptors.

    Returns:
        dict with 'embeddings', 'student_ids', 'student_map' or None if no students.
    """
    global _embedding_cache

    students = db.query(Student).filter(
        Student.face_embedding.isnot(None), Student.is_active.is_(True)
    ).all()

    if not students:
        logger.warning("No students with face embeddings found.")
        _embedding_cache = None
        return None

    embeddings = []
    student_ids = []
    student_map = {}

    for student in students:
        embedding = student.face_embedding
        if embedding and len(embedding) == 128:
            emb = np.array(embedding, dtype=np.float64)
            embeddings.append(emb)
            student_ids.append(student.student_id)
            student_map[student.student_id] = {
                "student_code": student.student_code,
                "name": student.name,
            }
        else:
            logger.warning(
                f"Student {student.student_code} (id={student.student_id}) "
                f"has invalid embedding (length={len(embedding) if embedding else 0}). Skipped."
            )

    if len(embeddings) == 0:
        logger.warning("No valid 128D embeddings found after filtering.")
        _embedding_cache = None
        return None

    _embedding_cache = {
        "embeddings": embeddings,
        "student_ids": student_ids,
        "student_map": student_map,
    }

    logger.info(
        f"Embedding cache built with {len(embeddings)} student(s): "
        f"{[student_map[sid]['name'] for sid in student_ids]}"
    )
    return _embedding_cache


def invalidate_classifier_cache():
    """Clear the cached embeddings so they will be reloaded on next recognition."""
    global _embedding_cache
    _embedding_cache = None
    logger.info("Embedding cache invalidated.")


def recognize_face(face_embedding: np.ndarray, db: Session) -> dict:
    """
    Recognize a face by comparing its embedding against registered students.

    Pipeline:
        1. Load or use cached student embeddings
        2. Compute Euclidean distance to EVERY registered embedding
        3. Find the nearest neighbor (smallest distance)
        4. Apply margin check: best match must be significantly closer
           than the second-best to avoid ambiguous matches
        5. Apply distance threshold check
        6. Calculate confidence score
        7. Return structured result

    Args:
        face_embedding: 128D numpy array from face detection service
        db: database session

    Returns:
        dict with keys:
            - recognized: bool
            - student_id: int or None
            - student_code: str or None
            - name: str or None
            - confidence: float (0.0 - 1.0)
            - distance: float (raw Euclidean distance)
            - message: str
    """
    global _embedding_cache

    # Always rebuild from DB to prevent stale embeddings from causing
    # misidentification (e.g. after a student re-enrolls their face).
    cache = _build_embedding_cache(db)

    if cache is None:
        return {
            "recognized": False,
            "student_id": None,
            "student_code": None,
            "name": None,
            "confidence": 0.0,
            "distance": float("inf"),
            "message": "No registered students found.",
        }

    stored_embeddings = cache["embeddings"]
    stored_ids = cache["student_ids"]
    student_map = cache["student_map"]
    threshold = settings.RECOGNITION_THRESHOLD  # default 0.6

    # ── Step 1: Compute distance to EVERY registered embedding ──
    distances = []
    for i, stored_emb in enumerate(stored_embeddings):
        dist = float(np.linalg.norm(stored_emb - face_embedding))
        distances.append((dist, stored_ids[i]))

    # Sort by distance (closest first)
    distances.sort(key=lambda x: x[0])

    best_distance, best_id = distances[0]
    best_info = student_map.get(best_id, {})

    # Log all distances for debugging
    logger.info(
        f"Recognition distances: "
        + ", ".join(
            f"{student_map.get(sid, {}).get('name', '?')}={d:.4f}"
            for d, sid in distances
        )
    )

    # ── Step 2: Margin / ambiguity check ──
    # If there are multiple students, the best match must be clearly
    # better than the second-best.  Without this check, two students
    # with similar embeddings can swap identities on every frame.
    if len(distances) >= 2:
        second_distance, second_id = distances[1]

        # The margin is the gap between the second-best and the best.
        # If the gap is too small relative to the best distance,
        # we consider the match ambiguous.
        margin = second_distance - best_distance
        # Require the best to be at least 20% closer than the second-best,
        # OR have an absolute margin of at least 0.12.
        # These tighter values prevent Student A from being identified as
        # Student B when their embeddings happen to be close.
        min_relative_margin = 0.20  # 20% of second_distance
        min_absolute_margin = 0.12

        is_ambiguous = (
            margin < min_absolute_margin
            and margin < second_distance * min_relative_margin
        )

        if is_ambiguous and best_distance > threshold * 0.4:
            # Only flag ambiguity when the best match isn't extremely close
            # (i.e., if best_distance is very low, we're very confident anyway).
            # Lowered the exemption bar from 0.5 → 0.4 of threshold so only
            # truly strong matches skip the ambiguity check.
            logger.warning(
                f"Ambiguous match: "
                f"best={best_info.get('name')} (d={best_distance:.4f}), "
                f"second={student_map.get(second_id, {}).get('name')} (d={second_distance:.4f}), "
                f"margin={margin:.4f}"
            )
            return {
                "recognized": False,
                "student_id": None,
                "student_code": None,
                "name": None,
                "confidence": 0.0,
                "distance": best_distance,
                "message": (
                    "Face match is ambiguous — could not confidently determine identity. "
                    "Please try again with better lighting or positioning."
                ),
            }

        logger.info(
            f"Margin check: best={best_info.get('name')} (d={best_distance:.4f}), "
            f"second={student_map.get(second_id, {}).get('name')} (d={second_distance:.4f}), "
            f"margin={margin:.4f} — {'CLEAR' if not is_ambiguous else 'AMBIGUOUS'}"
        )

    # ── Step 3: Threshold check ──
    if best_distance > threshold:
        confidence = max(0.0, 1.0 - (best_distance / threshold))
        logger.info(
            f"No match above threshold: best={best_info.get('name')} "
            f"(d={best_distance:.4f}, threshold={threshold})"
        )
        return {
            "recognized": False,
            "student_id": None,
            "student_code": None,
            "name": None,
            "confidence": round(confidence, 4),
            "distance": round(best_distance, 4),
            "message": "Face not recognized. No match above the confidence threshold.",
        }

    # ── Step 4: Confidence score ──
    # Confidence = 1.0 - (distance / threshold), clamped to [0, 1]
    confidence = max(0.0, min(1.0, 1.0 - (best_distance / threshold)))

    logger.info(
        f"RECOGNIZED: {best_info.get('name')} (id={best_id}, "
        f"d={best_distance:.4f}, confidence={confidence:.2%})"
    )

    return {
        "recognized": True,
        "student_id": best_id,
        "student_code": best_info.get("student_code"),
        "name": best_info.get("name"),
        "confidence": round(confidence, 4),
        "distance": round(best_distance, 4),
        "message": f"Recognized as {best_info.get('name', 'Unknown')} with {confidence:.0%} confidence.",
    }
