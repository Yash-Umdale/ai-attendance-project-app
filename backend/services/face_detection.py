"""
VeriAttend — Face Detection Service

Dedicated face detection layer using dlib's frontal face detector.
This module is responsible ONLY for detecting faces — not recognizing them.

Returns structured results: NO_FACE, ONE_FACE, MULTIPLE_FACES, LOW_QUALITY
with bounding box information.
"""

import numpy as np
import dlib
import face_recognition_models
import cv2
import logging

logger = logging.getLogger(__name__)

# ── Model Loading (singleton) ──
_detector = None
_shape_predictor = None
_face_recognizer = None


def _load_models():
    """Load dlib models once and cache them."""
    global _detector, _shape_predictor, _face_recognizer

    if _detector is None:
        logger.info("Loading dlib face detection models...")
        _detector = dlib.get_frontal_face_detector()
        _shape_predictor = dlib.shape_predictor(
            face_recognition_models.pose_predictor_model_location()
        )
        _face_recognizer = dlib.face_recognition_model_v1(
            face_recognition_models.face_recognition_model_location()
        )
        logger.info("dlib models loaded successfully.")

    return _detector, _shape_predictor, _face_recognizer


def get_detector():
    """Get the face detector instance."""
    detector, _, _ = _load_models()
    return detector


def get_shape_predictor():
    """Get the shape predictor instance."""
    _, sp, _ = _load_models()
    return sp


def get_face_recognizer():
    """Get the face recognition model instance."""
    _, _, fr = _load_models()
    return fr


def detect_faces(image_np: np.ndarray) -> dict:
    """
    Detect faces in an image.

    Args:
        image_np: RGB image as numpy array (H, W, 3)

    Returns:
        dict with keys:
            - status: "NO_FACE" | "ONE_FACE" | "MULTIPLE_FACES" | "LOW_QUALITY"
            - num_faces: int
            - bounding_boxes: list of {x, y, width, height}
            - faces: list of dlib rectangle objects (for downstream use)
            - message: human-readable description
    """
    detector = get_detector()

    # Check image quality — reject extremely blurry images
    if len(image_np.shape) == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np

    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 30.0:
        return {
            "status": "LOW_QUALITY",
            "num_faces": 0,
            "bounding_boxes": [],
            "faces": [],
            "message": "Image is too blurry. Please hold the camera steady.",
        }

    # Detect faces (upsample once for better small-face detection)
    faces = detector(image_np, 1)
    num_faces = len(faces)

    bounding_boxes = []
    for face in faces:
        bounding_boxes.append({
            "x": max(0, face.left()),
            "y": max(0, face.top()),
            "width": face.right() - face.left(),
            "height": face.bottom() - face.top(),
        })

    if num_faces == 0:
        return {
            "status": "NO_FACE",
            "num_faces": 0,
            "bounding_boxes": [],
            "faces": [],
            "message": "No face detected. Please position your face in the camera frame.",
        }
    elif num_faces == 1:
        return {
            "status": "ONE_FACE",
            "num_faces": 1,
            "bounding_boxes": bounding_boxes,
            "faces": list(faces),
            "message": "Face detected successfully.",
        }
    else:
        return {
            "status": "MULTIPLE_FACES",
            "num_faces": num_faces,
            "bounding_boxes": bounding_boxes,
            "faces": list(faces),
            "message": f"Multiple faces detected ({num_faces}). Only one face is allowed for attendance.",
        }


def get_face_landmarks(image_np: np.ndarray, face_rect) -> object:
    """
    Get 68-point facial landmarks for a detected face.

    Used by both face recognition (embedding) and liveness (EAR, head pose).

    Args:
        image_np: RGB image as numpy array
        face_rect: dlib rectangle from detect_faces

    Returns:
        dlib shape object with 68 landmark points
    """
    sp = get_shape_predictor()
    return sp(image_np, face_rect)


def compute_face_embedding(image_np: np.ndarray, shape, num_jitters: int = 10) -> np.ndarray:
    """
    Compute a 128-dimensional face embedding from an image and landmarks.

    This is the core biometric vector used for identity comparison.
    Uses dlib's ResNet-based face recognition model.

    Higher num_jitters produces more stable embeddings by averaging over
    multiple random perturbations of the face.  The default of 10 greatly
    reduces misidentification between different people.  Enrollment should
    use an even higher value (e.g. 50) because it only runs once per
    student while recognition runs on every frame.

    Metric: Euclidean distance between embeddings.
    Same person: typically < 0.6
    Different person: typically > 0.6

    Args:
        image_np: RGB image as numpy array
        shape: dlib shape (68-point landmarks)
        num_jitters: Number of random re-samples of the face to average.
            Higher = more accurate but slower.  Default 10 for recognition,
            use 50+ for enrollment.

    Returns:
        numpy array of shape (128,)
    """
    fr = get_face_recognizer()
    face_descriptor = fr.compute_face_descriptor(image_np, shape, num_jitters)
    return np.array(face_descriptor)


def get_all_face_embeddings(image_np: np.ndarray) -> list:
    """
    Detect all faces in an image and return their embeddings.

    Preserved from existing SnapClass face_pipeline.py logic.

    Args:
        image_np: RGB image as numpy array

    Returns:
        list of numpy arrays, each shape (128,)
    """
    detector = get_detector()
    sp = get_shape_predictor()
    fr = get_face_recognizer()

    faces = detector(image_np, 1)
    embeddings = []

    for face in faces:
        shape = sp(image_np, face)
        descriptor = fr.compute_face_descriptor(image_np, shape, 10)
        embeddings.append(np.array(descriptor))

    return embeddings
