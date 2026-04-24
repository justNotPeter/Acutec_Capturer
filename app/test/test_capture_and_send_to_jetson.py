import argparse
import os
import sys
from pathlib import Path

import cv2
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("ENV_FILE", str(REPO_ROOT / ".env"))
load_dotenv(REPO_ROOT / ".env")

from app.hardware.camera import camera
from app.service.dispatcher import dispatch_to_jetson
from app.service.quality_control import compute_qc_metrics
from app.service.session_key_generator import generate_inspection_key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open the Pi camera, capture one image, and send it to Jetson."
    )
    parser.add_argument(
        "--part-id",
        required=True,
        help="Part ID to include in current_view_metadata.",
    )
    parser.add_argument(
        "--part-type",
        required=True,
        help="Part type to include in current_view_metadata.",
    )
    parser.add_argument(
        "--view-index",
        type=int,
        default=0,
        help="View index to include in current_view_metadata.",
    )
    parser.add_argument(
        "--inspection-key",
        help="Optional inspection key. If omitted, one is generated from part_id and capture time.",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=92,
        help="JPEG quality for upload encoding.",
    )
    parser.add_argument(
        "--width",
        type=int,
        help="Optional camera width override for this run.",
    )
    parser.add_argument(
        "--height",
        type=int,
        help="Optional camera height override for this run.",
    )
    return parser.parse_args()


def encode_frame_to_jpeg(frame, quality: int) -> bytes:
    success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not success:
        raise RuntimeError("Could not JPEG-encode captured frame.")
    return encoded.tobytes()


def main() -> int:
    args = parse_args()

    try:
        if (args.width is None) != (args.height is None):
            raise RuntimeError("Both --width and --height must be provided together.")

        if args.width is not None and args.height is not None:
            camera.set_resolution(args.width, args.height)

        camera.init_camera()
        frame, captured_time_utc = camera.capture_frame()

        jpeg_bytes = encode_frame_to_jpeg(frame, args.jpeg_quality)
        metrics = compute_qc_metrics(frame)
        inspection_key = args.inspection_key or generate_inspection_key(
            args.part_id,
            captured_time_utc,
        )

        current_view_metadata = {
            "part_id": args.part_id,
            "part_type": args.part_type,
            "inspection_key": inspection_key,
            "view_index": args.view_index,
            "qc_sharpness": float(metrics["sharpness"]),
            "qc_brightness": float(metrics["brightness"]),
            "qc_contrast": float(metrics["contrast"]),
            "captured_time_utc": captured_time_utc,
        }

        print("Sending live camera image to Jetson with metadata:")
        print(current_view_metadata)

        dispatch_to_jetson(jpeg_bytes, current_view_metadata)
        print("Dispatch completed.")
        return 0

    except Exception as exc:
        print(f"Failed capture/send flow: {exc}")
        return 1

    finally:
        try:
            camera.release()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
