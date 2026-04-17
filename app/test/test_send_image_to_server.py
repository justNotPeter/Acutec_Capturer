import argparse
import sys
from pathlib import Path

import cv2
from dotenv import load_dotenv

from app.service.dispatcher import dispatch_to_jetson
from app.service.quality_control import compute_qc_metrics


VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load an image from disk and send it to the server using the Capturer dispatcher."
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Path to the image file to upload.",
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
        "--captured-time-utc",
        required=True,
        help="Capture timestamp in UTC ISO 8601 format, for example 2026-04-16T14:22:31Z.",
    )
    return parser.parse_args()


def encode_to_jpeg(image_path: Path) -> tuple[bytes, dict]:
    frame = cv2.imread(str(image_path))
    if frame is None:
        raise RuntimeError(f"Could not load image: {image_path}")

    success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not success:
        raise RuntimeError(f"Could not JPEG-encode image: {image_path}")

    metrics = compute_qc_metrics(frame)
    return encoded.tobytes(), metrics


def main() -> int:
    args = parse_args()
    image_path = Path(args.image).expanduser().resolve()

    if not image_path.exists():
        print(f"Image does not exist: {image_path}")
        return 2

    if image_path.suffix.lower() not in VALID_EXTENSIONS:
        print(f"Unsupported image extension: {image_path.suffix}")
        return 2

    try:
        jpeg_bytes, metrics = encode_to_jpeg(image_path)
    except Exception as exc:
        print(f"Failed preparing image: {exc}")
        return 1

    current_view_metadata = {
        "part_id": args.part_id,
        "part_type": args.part_type,
        "view_index": args.view_index,
        "qc_sharpness": float(metrics["sharpness"]),
        "qc_brightness": float(metrics["brightness"]),
        "qc_contrast": float(metrics["contrast"]),
        "captured_time_utc": args.captured_time_utc,
    }

    print("Sending image to server with metadata:")
    print(current_view_metadata)

    dispatch_to_jetson(jpeg_bytes, current_view_metadata)
    print("Dispatch completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
