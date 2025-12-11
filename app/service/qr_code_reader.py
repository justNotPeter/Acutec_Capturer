import cv2
import numpy as np
from typing import Optional, Tuple, Dict
from app.config.part_recipe import PART_TYPE_TO_RECIPE_CODE

def decode_qr_code(
    frame: np.ndarray,
    simulated_result: Optional[Dict[str, str]] = None
) -> Tuple[Optional[Dict[str, str]], Optional[np.ndarray]]:

    if simulated_result is not None:
        return simulated_result, None

    detector = cv2.QRCodeDetector()
    data, bbox, rectified_img = detector.detectAndDecode(frame)

    if not data:
        return None, None

    try:
        part_id, part_type = data.split("|", 1)

        part_id = part_id.strip()
        part_type = part_type.strip()

        if part_type not in PART_TYPE_TO_RECIPE_CODE:
            print(f"[Unknown part_type '{part_type}'. No recipe available!")
            return None, None

        decoded_object = {
            "part_id": part_id,
            "part_type": part_type,
        }

        return decoded_object, bbox

    except ValueError:
        print(f"Format issue. Data = '{data}'")
        return None, None