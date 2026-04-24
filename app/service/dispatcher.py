import os
import json
import requests

JETSON_URL = os.getenv("JETSON_URL")  

# print("Jetson_URL is: ")

def dispatch_to_jetson(
    jpeg_frame: bytes,
    current_part_metadata: dict,
    jetson_url: str | None = None,
) -> None:
    files = {
        "image": ("frame.jpg", jpeg_frame, "image/jpeg"),
        "current_view_metadata": (
            None,
            json.dumps(current_part_metadata),
            "application/json",
        ),
    }

    try:
        target_url = jetson_url or JETSON_URL
        if not target_url:
            raise RuntimeError("JETSON_URL is not configured.")
        resp = requests.post(target_url, files=files, timeout=10)
        resp.raise_for_status()
        
    except Exception as e:
        print(f"Cannot send to Jetson Analyzer!: {e}")
        return
