import json
import cv2
import numpy as np
from typing import Optional, Tuple, Dict
from app.config.part_recipe import PART_TYPE_TO_RECIPE_CODE

def _try_decode(detector: cv2.QRCodeDetector, frame: np.ndarray) -> Tuple[str, Optional[np.ndarray]]:
    data, bbox, _ = detector.detectAndDecode(frame)
    return data, bbox

def _parse_payload(data: str) -> Optional[Dict[str, str]]:
    try:
        if data.lstrip().startswith("{"):
            payload = json.loads(data)
            part_id = str(payload["part_id"]).strip()
            part_type = str(payload["part_type"]).strip()
        else:
            part_id, part_type = data.split("|", 1)
            part_id = part_id.strip()
            part_type = part_type.strip()

        if part_type not in PART_TYPE_TO_RECIPE_CODE:
            print(f"Unknown part_type '{part_type}'. No recipe available!")
            return None

        return {
            "part_id": part_id,
            "part_type": part_type,
        }
    except (ValueError, KeyError, json.JSONDecodeError):
        print(f"Format issue. Data = '{data}'")
        return None

def decode_qr_code(frame: np.ndarray, simulated_result: Optional[Dict[str, str]] = None) -> Tuple[Optional[Dict[str, str]], Optional[np.ndarray]]:

    if simulated_result is not None:
        return simulated_result, None

    detector = cv2.QRCodeDetector()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    decode_attempts = [
        ("raw", frame),
        ("gray", gray),
    ]

    for scale in (1.5, 2.0):
        resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        decode_attempts.append((f"gray_x{scale}", resized))

    for attempt_name, candidate in decode_attempts:
        data, bbox = _try_decode(detector, candidate)
        if not data:
            continue

        decoded_object = _parse_payload(data)
        if decoded_object is not None:
            print(f"QR decode succeeded using {attempt_name} frame.")
            return decoded_object, bbox

    return None, None
