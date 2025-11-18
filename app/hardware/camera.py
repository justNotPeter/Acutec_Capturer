import os
import time
import cv2
from dotenv import load_dotenv
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
        self.exposure_us = DEFAULT_CAMERA_CONFIG["exposure_us"]
        self.gain = DEFAULT_CAMERA_CONFIG["gain"]

    def init_camera(self):
        if self.cap is not None:
            return 

        self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            self.cap = None
            raise RuntimeError(f"❌ Could not open camera at index {self.source}!")

        self.apply_settings()
        print("📷 Camera opened!")

    def apply_settings(self):
        if self.cap is None:
            return

        w, h = self.resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

        if self.exposure_us is not None:
            self.cap.set(cv2.CAP_PROP_EXPOSURE, float(self.exposure_us))
        if self.gain is not None:
            self.cap.set(cv2.CAP_PROP_GAIN, float(self.gain))

    def capture_frame(self):
        if self.cap is None:
            raise RuntimeError("Camera not opened!")

        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("❌ Failed to capture frame from camera!")

        return frame

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
            print("📷 Camera released!")

camera = Camera()