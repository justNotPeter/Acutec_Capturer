import os
import cv2
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Tuple
import numpy as np
from app.config.camera_config import DEFAULT_CAMERA_CONFIG

env_path = os.getenv("ENV_FILE", ".env.local")

if env_path and os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

CAMERA_SOURCE = int(os.getenv("CAMERA_SOURCE", "0"))

class Camera:
    def __init__(self):
        self.source = CAMERA_SOURCE
        self.cap = None
        self.resolution = DEFAULT_CAMERA_CONFIG["resolution"]
        self.fourcc = DEFAULT_CAMERA_CONFIG.get("fourcc")
        self.exposure_us = DEFAULT_CAMERA_CONFIG["exposure_us"]
        self.gain = DEFAULT_CAMERA_CONFIG["gain"]

    def init_camera(self):
        if self.cap is not None:
            return 

        self.cap = cv2.VideoCapture(self.source, cv2.CAP_V4L2)

        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            self.cap = None
            raise RuntimeError(f"❌ Could not open camera at index {self.source}!")

        self.apply_settings()
        print("📷 Camera opened!")
        

    def apply_settings(self):
        if self.cap is None:
            return

        if self.fourcc:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.fourcc))

        w, h = self.resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

        if self.exposure_us is not None:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25) 
            
            exposure_seconds = float(self.exposure_us) / 1_000_000
            self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure_seconds)

        if self.gain is not None:
            self.cap.set(cv2.CAP_PROP_GAIN, float(self.gain))

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Camera resolution applied: {actual_w}x{actual_h}")
        

    def capture_frame(self) -> tuple[np.ndarray, str]:
        if self.cap is None:
            raise RuntimeError("Camera not opened!")

        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("❌ Failed to capture frame from camera!")
        
        capture_time_utc = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace("+00:00", "Z")

        return frame, capture_time_utc
    
    
    def set_resolution(self, width: int, height: int):
        print(f"Default resolution is {width}x{height}!")
     
        self.resolution = (width, height)
        
        if self.cap is not None:
            self.apply_settings()
            print(f"New resolution is set to {width}x{height}!")
            

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
            print("📷 Camera released!")

camera = Camera()