"""
VeriAttend — Liveness Verification Service

Independent liveness module that distinguishes a live person from
presentation attacks (printed photos, phone screens, static images).

Two approaches implemented:
1. Passive anti-spoofing: texture analysis (Laplacian variance, edge density)
2. Challenge-based: blink detection and head turn using dlib 68-point landmarks

The module is designed to be swappable — the underlying algorithm can be
replaced without changing the attendance workflow.
"""

import numpy as np
import cv2
import uuid
import time
import logging
from scipy.spatial import distance as dist

from config import settings
from services.face_detection import get_face_landmarks, detect_faces

logger = logging.getLogger(__name__)

# ── Challenge Store (in-memory for simplicity) ──
_active_challenges: dict[str, dict] = {}

# Challenge types
CHALLENGE_TYPES = ["BLINK", "TURN_LEFT", "TURN_RIGHT"]


# ══════════════════════════════════════
# Passive Liveness (Anti-Spoofing)
# ══════════════════════════════════════

def check_passive_liveness(image_np: np.ndarray) -> dict:
    """
    Passive anti-spoofing checks using image texture analysis.

    Printed photos and screens tend to have:
    - Lower texture variation (smoother surfaces)
    - Different edge patterns (moiré patterns on screens)
    - Less micro-texture detail

    We use Laplacian variance as a proxy for texture complexity.
    Real faces have more fine texture detail than flat prints.

    Args:
        image_np: RGB image as numpy array

    Returns:
        dict with liveness, score, message
    """
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

    # Laplacian variance — measures texture sharpness/detail
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    texture_score = laplacian.var()

    # Edge density — Canny edge detection
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.count_nonzero(edges) / edges.size

    # Combined heuristic score
    # Higher texture + reasonable edge density = more likely real
    texture_threshold = settings.LIVENESS_TEXTURE_THRESHOLD

    if texture_score >= texture_threshold and edge_density > 0.02:
        # Normalize score to 0-1 range
        score = min(1.0, texture_score / (texture_threshold * 3))
        return {
            "liveness": "PASS",
            "score": round(score, 3),
            "method": "PASSIVE_TEXTURE",
            "message": "Passive liveness check passed.",
        }
    elif texture_score >= texture_threshold * 0.6:
        score = texture_score / (texture_threshold * 3)
        return {
            "liveness": "UNCERTAIN",
            "score": round(score, 3),
            "method": "PASSIVE_TEXTURE",
            "message": "Liveness uncertain. Consider challenge-based verification.",
        }
    else:
        return {
            "liveness": "FAIL",
            "score": round(texture_score / (texture_threshold * 3), 3),
            "method": "PASSIVE_TEXTURE",
            "message": "Possible presentation attack detected. Image lacks natural texture.",
        }


# ══════════════════════════════════════
# Challenge-Based Liveness
# ══════════════════════════════════════

def create_challenge(group_mode: bool = False) -> dict:
    """
    Generate a random liveness challenge for the user.

    Returns:
        dict with challenge_id, challenge_type, instruction, timeout_seconds
    """
    import random

    now = time.time()
    for expired_id, existing in list(_active_challenges.items()):
        if now - existing["created_at"] > existing["timeout_seconds"]:
            del _active_challenges[expired_id]

    challenge_type = random.choice(CHALLENGE_TYPES)
    challenge_id = str(uuid.uuid4())

    instructions = {
        "BLINK": "Please blink your eyes naturally",
        "TURN_LEFT": "Please turn your head slightly to the left",
        "TURN_RIGHT": "Please turn your head slightly to the right",
    }
    instruction = instructions[challenge_type]
    if group_mode:
        instruction = f"Everyone: {instruction.lower()}"

    challenge = {
        "challenge_id": challenge_id,
        "challenge_type": challenge_type,
        "instruction": instruction,
        "timeout_seconds": settings.LIVENESS_CHALLENGE_TIMEOUT,
        "created_at": time.time(),
        "frames": [],  # Will store frame analysis results
        "completed": False,
        "result": None,
        "state": "START",
        "closed_frames": 0,
        "open_frames": 0,
        "group_mode": group_mode,
        "group_face_count": None,
        "group_states": [],
    }

    _active_challenges[challenge_id] = challenge

    return {
        "challenge_id": challenge_id,
        "challenge_type": challenge_type,
        "instruction": instruction,
        "timeout_seconds": settings.LIVENESS_CHALLENGE_TIMEOUT,
    }


def _compute_ear(landmarks, eye_indices) -> float:
    """
    Compute Eye Aspect Ratio (EAR) for blink detection.

    EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)

    When the eye is open, EAR is ~0.25-0.30.
    When the eye closes, EAR drops below ~0.20.

    Args:
        landmarks: dlib shape with 68 points
        eye_indices: list of 6 landmark indices for one eye

    Returns:
        float EAR value
    """
    points = []
    for i in eye_indices:
        p = landmarks.part(i)
        points.append(np.array([p.x, p.y], dtype=np.float64))

    # Vertical distances
    v1 = dist.euclidean(points[1], points[5])
    v2 = dist.euclidean(points[2], points[4])
    # Horizontal distance
    h = dist.euclidean(points[0], points[3])

    if h == 0:
        return 0.0

    ear = (v1 + v2) / (2.0 * h)
    return ear


def _compute_head_yaw(landmarks) -> float:
    """
    Estimate head yaw angle from facial landmarks.

    Uses the horizontal asymmetry between nose tip and face edges.
    When facing forward, the nose tip is roughly centered.
    When turning, the ratio shifts.

    Args:
        landmarks: dlib shape with 68 points

    Returns:
        float estimated yaw in degrees (negative = left, positive = right)
    """
    # Key points: nose tip (30), left jaw (0), right jaw (16)
    nose_tip = np.array([landmarks.part(30).x, landmarks.part(30).y])
    left_jaw = np.array([landmarks.part(0).x, landmarks.part(0).y])
    right_jaw = np.array([landmarks.part(16).x, landmarks.part(16).y])

    # Distance from nose to each jaw edge
    d_left = dist.euclidean(nose_tip, left_jaw)
    d_right = dist.euclidean(nose_tip, right_jaw)

    face_width = dist.euclidean(left_jaw, right_jaw)
    if face_width == 0:
        return 0.0

    # Ratio-based yaw estimate
    ratio = (d_right - d_left) / face_width
    yaw_estimate = ratio * 90  # rough conversion to degrees

    return yaw_estimate


def verify_challenge_frame(challenge_id: str, image_np: np.ndarray) -> dict:
    """
    Process a frame for an active liveness challenge.

    For BLINK: detects if EAR drops below threshold (eye closure)
    For TURN_LEFT/TURN_RIGHT: detects head yaw angle change

    Args:
        challenge_id: ID of the active challenge
        image_np: RGB image as numpy array

    Returns:
        dict with liveness result if challenge completed, or progress update
    """
    if challenge_id not in _active_challenges:
        return {
            "liveness": "FAIL",
            "score": 0.0,
            "challenge": None,
            "message": "Invalid or expired challenge.",
        }

    challenge = _active_challenges[challenge_id]

    if challenge["completed"]:
        return challenge["result"]

    # Check timeout
    elapsed = time.time() - challenge["created_at"]
    if elapsed > challenge["timeout_seconds"]:
        del _active_challenges[challenge_id]
        return {
            "liveness": "FAIL",
            "score": 0.0,
            "challenge": challenge["challenge_type"],
            "message": "Challenge timed out.",
        }

    # Detect face
    detection = detect_faces(image_np)
    if challenge.get("group_mode"):
        return _verify_group_frame(challenge, detection, image_np)

    if detection["status"] != "ONE_FACE":
        return {
            "liveness": "UNCERTAIN",
            "score": 0.0,
            "challenge": challenge["challenge_type"],
            "message": detection["message"],
        }

    face_rect = detection["faces"][0]
    landmarks = get_face_landmarks(image_np, face_rect)

    challenge_type = challenge["challenge_type"]

    if challenge_type == "BLINK":
        return _verify_blink(challenge, landmarks)
    elif challenge_type in ("TURN_LEFT", "TURN_RIGHT"):
        return _verify_head_turn(challenge, landmarks, challenge_type)

    return {"liveness": "FAIL", "score": 0.0, "message": "Unknown challenge type."}


def _new_face_challenge_state() -> dict:
    return {
        "frames": [], "completed": False, "result": None,
        "state": "START", "closed_frames": 0, "open_frames": 0,
    }


def _verify_group_frame(challenge: dict, detection: dict, image_np: np.ndarray) -> dict:
    """Require every visible face to complete the same random live action."""
    faces = detection.get("faces", [])
    if not faces:
        return {
            "liveness": "UNCERTAIN", "score": 0.0,
            "challenge": challenge["challenge_type"],
            "message": "Keep all students' faces visible in the camera.",
        }

    if len(faces) > 8:
        return {
            "liveness": "FAIL", "score": 0.0,
            "challenge": challenge["challenge_type"],
            "message": "Group attendance supports up to 8 faces at a time.",
        }

    # Keep participant slots stable by ordering faces from left to right.
    faces = sorted(faces, key=lambda face: (face.left() + face.right()) / 2)
    if challenge["group_face_count"] != len(faces):
        challenge["group_face_count"] = len(faces)
        challenge["group_states"] = [_new_face_challenge_state() for _ in faces]
        return {
            "liveness": "UNCERTAIN", "score": 0.0,
            "challenge": challenge["challenge_type"],
            "message": f"Keep all {len(faces)} faces visible. Everyone: follow the instruction.",
        }

    challenge_type = challenge["challenge_type"]
    for face, state in zip(faces, challenge["group_states"]):
        if state["completed"]:
            continue
        landmarks = get_face_landmarks(image_np, face)
        if challenge_type == "BLINK":
            _verify_blink(state, landmarks)
        else:
            _verify_head_turn(state, landmarks, challenge_type)

    completed_count = sum(1 for state in challenge["group_states"] if state["completed"])
    if completed_count == len(faces):
        result = {
            "liveness": "PASS", "score": 1.0,
            "challenge": challenge_type,
            "face_count": len(faces),
            "message": f"All {len(faces)} students completed the liveness check.",
        }
        challenge["completed"] = True
        challenge["verified_face_count"] = len(faces)
        challenge["result"] = result
        return result

    return {
        "liveness": "UNCERTAIN", "score": 0.0,
        "challenge": challenge_type,
        "message": f"{completed_count} of {len(faces)} students verified. Everyone: follow the instruction.",
    }


def _verify_blink(challenge: dict, landmarks) -> dict:
    """Verify blink challenge using Eye Aspect Ratio."""
    # dlib 68-point landmark indices for eyes
    LEFT_EYE = [36, 37, 38, 39, 40, 41]
    RIGHT_EYE = [42, 43, 44, 45, 46, 47]

    left_ear = _compute_ear(landmarks, LEFT_EYE)
    right_ear = _compute_ear(landmarks, RIGHT_EYE)
    avg_ear = (left_ear + right_ear) / 2.0

    threshold = settings.LIVENESS_EAR_THRESHOLD
    challenge["frames"].append(avg_ear)
    if challenge["state"] == "START":
        if avg_ear >= threshold:
            challenge["state"] = "OPEN"
    elif challenge["state"] == "OPEN":
        if avg_ear < threshold:
            challenge["closed_frames"] += 1
            if challenge["closed_frames"] >= settings.LIVENESS_BLINK_CONSEC_FRAMES:
                challenge["state"] = "CLOSED"
        else:
            challenge["closed_frames"] = 0
    elif challenge["state"] == "CLOSED" and avg_ear >= threshold:
        challenge["open_frames"] += 1

    if challenge["state"] == "CLOSED" and challenge["open_frames"] >= 2:
        challenge["completed"] = True
        score = 1.0
        result = {
            "liveness": "PASS",
            "score": round(score, 3),
            "challenge": "BLINK",
            "message": "Blink detected. Liveness verified.",
        }
        challenge["result"] = result
        return result

    return {
        "liveness": "UNCERTAIN",
        "score": 0.0,
        "challenge": "BLINK",
        "message": f"Waiting for blink... ({len(challenge['frames'])} frames analyzed)",
    }


def _verify_head_turn(challenge: dict, landmarks, direction: str) -> dict:
    """Verify head turn challenge using yaw estimation."""
    yaw = _compute_head_yaw(landmarks)
    threshold = settings.LIVENESS_HEAD_TURN_THRESHOLD

    frames = challenge["frames"]
    frames.append(yaw)

    if challenge["state"] == "START":
        if abs(yaw) <= threshold * 0.5:
            challenge["state"] = "NEUTRAL"
            challenge["baseline_yaw"] = yaw
        return {
            "liveness": "UNCERTAIN",
            "score": 0.0,
            "challenge": direction,
            "message": "Face forward briefly, then follow the head-turn instruction.",
        }

    movement = yaw - challenge.get("baseline_yaw", 0.0)

    if direction == "TURN_LEFT" and movement < -threshold:
        challenge["completed"] = True
        score = min(1.0, abs(movement) / (threshold * 2) + 0.3)
        result = {
            "liveness": "PASS",
            "score": round(score, 3),
            "challenge": direction,
            "message": f"Head turn {direction.split('_')[1].lower()} detected. Liveness verified.",
        }
        challenge["result"] = result
        return result

    elif direction == "TURN_RIGHT" and movement > threshold:
        challenge["completed"] = True
        score = min(1.0, abs(movement) / (threshold * 2) + 0.3)
        result = {
            "liveness": "PASS",
            "score": round(score, 3),
            "challenge": direction,
            "message": f"Head turn {direction.split('_')[1].lower()} detected. Liveness verified.",
        }
        challenge["result"] = result
        return result

    return {
        "liveness": "UNCERTAIN",
        "score": 0.0,
        "challenge": direction,
        "message": f"Please turn your head {direction.split('_')[1].lower()}... (yaw: {yaw:.1f}°)",
    }


def consume_successful_challenge(challenge_id: str | None, expected_face_count: int | None = None) -> bool:
    """Consume a completed, unexpired challenge exactly once for attendance."""
    if not challenge_id:
        return False
    challenge = _active_challenges.pop(challenge_id, None)
    if not challenge or not challenge.get("completed"):
        return False
    if time.time() - challenge["created_at"] > challenge["timeout_seconds"]:
        return False
    if expected_face_count is not None and challenge.get("verified_face_count") != expected_face_count:
        return False
    return True


def get_combined_liveness(image_np: np.ndarray, challenge_result: dict | None = None) -> dict:
    """
    Combine passive and challenge-based liveness results.

    If a challenge was completed, its result takes priority.
    Otherwise, fall back to passive texture analysis.

    Args:
        image_np: RGB image
        challenge_result: result from challenge verification, if any

    Returns:
        Final liveness result dict
    """
    if challenge_result and challenge_result.get("liveness") == "PASS":
        return challenge_result

    # Fall back to passive check
    passive_result = check_passive_liveness(image_np)

    if challenge_result and challenge_result.get("liveness") == "FAIL":
        # Challenge explicitly failed — override passive
        return challenge_result

    return passive_result
