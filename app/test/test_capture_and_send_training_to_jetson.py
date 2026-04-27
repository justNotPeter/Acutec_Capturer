import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("ENV_FILE", str(REPO_ROOT / ".env"))
load_dotenv(REPO_ROOT / ".env")

from app.hardware.camera import camera
from app.service.quality_control import compute_qc_metrics
from app.service.session_key_generator import generate_inspection_key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open the Pi camera, capture many images, and send them to the Jetson training route."
    )
    parser.add_argument("--part-id", required=True)
    parser.add_argument("--part-type", required=True)
    parser.add_argument("--view-index", type=int, default=0)
    parser.add_argument("--inspection-key")
    parser.add_argument("--count", type=int, default=150)
    parser.add_argument("--delay-ms", type=int, default=0)
    parser.add_argument("--jpeg-quality", type=int, default=92)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--training-url")
    parser.add_argument("--show-preview", action="store_true")
    parser.add_argument("--upload-workers", type=int, default=2)
    parser.add_argument("--timeout-sec", type=float, default=30.0)
    return parser.parse_args()


def encode_frame_to_jpeg(frame, quality: int) -> bytes:
    success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not success:
        raise RuntimeError("Could not JPEG-encode captured frame.")
    return encoded.tobytes()


def derive_training_url(training_url: str | None) -> str:
    if training_url:
        return training_url

    base_url = os.getenv("JETSON_URL")
    if not base_url:
        raise RuntimeError("JETSON_URL is not configured in .env")

    if base_url.endswith("/upload-view"):
        return f"{base_url[:-len('/upload-view')]}/upload-training-view"

    return base_url.rstrip("/") + "/api/psm/upload-training-view"


def post_training_frame(session: requests.Session, url: str, jpeg_bytes: bytes, metadata: dict, timeout_sec: float) -> None:
    files = {
        "image": ("frame.jpg", jpeg_bytes, "image/jpeg"),
        "current_view_metadata": (None, __import__("json").dumps(metadata), "application/json"),
    }
    resp = session.post(url, files=files, timeout=timeout_sec)
    resp.raise_for_status()


def main() -> int:
    args = parse_args()

    try:
        if args.count <= 0:
            raise RuntimeError("--count must be greater than 0.")
        if (args.width is None) != (args.height is None):
            raise RuntimeError("Both --width and --height must be provided together.")
        if args.width is not None and args.height is not None:
            camera.set_resolution(args.width, args.height)

        training_url = derive_training_url(args.training_url)
        camera.init_camera()

        shared_inspection_key = args.inspection_key
        delay_seconds = max(args.delay_ms, 0) / 1000.0

        session = requests.Session()
        futures = []

        with ThreadPoolExecutor(max_workers=args.upload_workers) as pool:
            for capture_idx in range(1, args.count + 1):
                frame, captured_time_utc = camera.capture_frame()

                if shared_inspection_key is None:
                    shared_inspection_key = generate_inspection_key(args.part_id, captured_time_utc)

                jpeg_bytes = encode_frame_to_jpeg(frame, args.jpeg_quality)
                metrics = compute_qc_metrics(frame)

                current_view_metadata = {
                    "part_id": args.part_id,
                    "part_type": args.part_type,
                    "inspection_key": shared_inspection_key,
                    "view_index": args.view_index,
                    "qc_sharpness": float(metrics["sharpness"]),
                    "qc_brightness": float(metrics["brightness"]),
                    "qc_contrast": float(metrics["contrast"]),
                    "captured_time_utc": captured_time_utc,
                }

                if args.show_preview:
                    preview = frame.copy()
                    cv2.putText(
                        preview,
                        f"{capture_idx}/{args.count}",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA,
                    )
                    cv2.imshow("Pi Training Capture", preview)
                    cv2.waitKey(1)

                futures.append(
                    pool.submit(
                        post_training_frame,
                        session,
                        training_url,
                        jpeg_bytes,
                        current_view_metadata,
                        args.timeout_sec,
                    )
                )

                print(f"[queued {capture_idx}/{args.count}]")

                if delay_seconds > 0 and capture_idx < args.count:
                    time.sleep(delay_seconds)

            completed = 0
            for future in as_completed(futures):
                future.result()
                completed += 1
                print(f"[uploaded {completed}/{args.count}]")

        print("Training capture batch completed.")
        return 0

    except Exception as exc:
        print(f"Failed training capture/send flow: {exc}")
        return 1

    finally:
        try:
            camera.release()
        except Exception:
            pass
        if args.show_preview:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    sys.exit(main())
