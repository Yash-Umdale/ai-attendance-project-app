"""
VeriAttend — Liveness Routes

POST /api/liveness/challenge       — Create a new liveness challenge
POST /api/liveness/verify          — Verify a frame against an active challenge
POST /api/liveness/passive-check   — Run passive anti-spoofing check
"""

from fastapi import APIRouter, HTTPException
import numpy as np
import base64
import cv2

from models.schemas import LivenessChallenge, LivenessResult
from services.liveness import create_challenge, verify_challenge_frame, check_passive_liveness

router = APIRouter(prefix="/api/liveness", tags=["Liveness Verification"])


def _decode_frame(frame_data: str) -> np.ndarray:
    """Decode base64 image to numpy RGB array."""
    if "," in frame_data:
        frame_data = frame_data.split(",", 1)[1]
    img_bytes = base64.b64decode(frame_data)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


@router.post(
    "/challenge",
    response_model=LivenessChallenge,
    summary="Create a new liveness challenge",
    description=(
        "Generates a random liveness challenge (BLINK, TURN_LEFT, or TURN_RIGHT). "
        "The challenge must be completed within the timeout period by sending "
        "frames to the /verify endpoint."
    ),
)
def create_liveness_challenge(body: dict | None = None):
    """Issue a new randomized liveness challenge."""
    challenge = create_challenge(group_mode=bool((body or {}).get("group_mode", False)))
    return LivenessChallenge(**challenge)


@router.post(
    "/verify",
    response_model=LivenessResult,
    summary="Verify a frame against an active liveness challenge",
    description=(
        "Submit a camera frame for verification against an active challenge. "
        "For BLINK: the system detects eye closure using Eye Aspect Ratio. "
        "For TURN_LEFT/TURN_RIGHT: the system measures head yaw angle. "
        "Send multiple frames until the challenge is completed (PASS) or times out (FAIL)."
    ),
)
def verify_liveness(body: dict):
    """Process a frame for the active liveness challenge."""
    challenge_id = body.get("challenge_id")
    frame_data = body.get("frame_data")

    if not challenge_id or not frame_data:
        raise HTTPException(status_code=400, detail="challenge_id and frame_data are required.")

    try:
        image_np = _decode_frame(frame_data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image data.")

    result = verify_challenge_frame(challenge_id, image_np)

    return LivenessResult(
        liveness=result["liveness"],
        score=result["score"],
        challenge=result.get("challenge"),
        message=result["message"],
    )


@router.post(
    "/passive-check",
    response_model=LivenessResult,
    summary="Run passive anti-spoofing check",
    description=(
        "Analyzes the image texture to detect potential presentation attacks "
        "(printed photos, phone screens). Uses Laplacian variance and edge "
        "density as heuristics. No user interaction required."
    ),
)
def passive_liveness_check(body: dict):
    """Run passive liveness analysis on a single frame."""
    frame_data = body.get("frame_data")
    if not frame_data:
        raise HTTPException(status_code=400, detail="frame_data is required.")

    try:
        image_np = _decode_frame(frame_data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image data.")

    result = check_passive_liveness(image_np)

    return LivenessResult(
        liveness=result["liveness"],
        score=result["score"],
        message=result["message"],
    )
