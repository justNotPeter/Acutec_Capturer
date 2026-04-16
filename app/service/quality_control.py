import cv2
import numpy as np
from typing import Optional, Dict

def compute_qc_metrics(frame: np.ndarray, simulated_result: Optional[Dict[str, int]] = None) -> dict:
    
    if simulated_result:
        return simulated_result
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Sharpness: variance of Laplacian (focus measure)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = lap.var()

    # Brightness: mean pixel value
    brightness = float(gray.mean())

    # Contrast: simple normalized range
    min_val, max_val, _, _ = cv2.minMaxLoc(gray)
    if (max_val + min_val) == 0:
        contrast = 0.0
    else:
        contrast = (max_val - min_val) / (max_val + min_val)

    return {
        "sharpness": sharpness,
        "brightness": brightness,
        "contrast": contrast,
    }
    
def check_quality(
    metrics: dict,
    min_sharpness_threshold: float = 100.0,
    min_brightness_threshold: float = 50.0,
    max_brightness_threshold: float = 200.0,
    min_contrast_threshold: float = 0.20
) -> bool:
    
    if metrics["sharpness"] < min_sharpness_threshold: 
        print(f"Failed: Image is blurry. Sharpness ({metrics['sharpness']:.1f}) is below threshold ({min_sharpness_threshold:.1f})!")
        return False

    if not (min_brightness_threshold < metrics["brightness"] < max_brightness_threshold):
        print(f"Failed: Exposure incorrect. Brightness ({metrics['brightness']:.1f}) is outside [{min_brightness_threshold:.1f}, {max_brightness_threshold:.1f}]!")
        return False
        
    if metrics["contrast"] < min_contrast_threshold:
        print(f"Failed: Image contrast is too low ({metrics['contrast']:.2f}). Possible haze/glare!")
        return False
        
    print("Pass: Image quality meets technical requirements!")
    return True