"""
VeriAttend — Shared Utilities

Common helper functions used across multiple routers.
"""

import numpy as np
import base64
import cv2


def decode_frame(frame_data: str) -> np.ndarray:
    """Decode a base64-encoded image to numpy RGB array.

    Handles both raw base64 and data URI format (``data:image/...;base64,...``).

    Args:
        frame_data: base64-encoded image string

    Returns:
        RGB image as numpy array (H, W, 3)

    Raises:
        ValueError: if the image cannot be decoded
    """
    # Handle data URI prefix
    if "," in frame_data:
        frame_data = frame_data.split(",", 1)[1]

    img_bytes = base64.b64decode(frame_data)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
