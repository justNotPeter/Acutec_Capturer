import argparse
import sys
from pathlib import Path

import cv2

from app.service.qr_code_reader import decode_qr_code


VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]

    parser = argparse.ArgumentParser(
        description="Load every QR image in a folder and run the QR reader on it."
    )
    parser.add_argument(
        "--folder",
        default=str(repo_root / "qr_codes"),
        help="Folder containing QR images. Defaults to repo_root/qr_codes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    folder = Path(args.folder).expanduser().resolve()

    if not folder.exists():
        print(f"Folder does not exist: {folder}")
        return 2

    image_paths = sorted(
        path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in VALID_EXTENSIONS
    )

    if not image_paths:
        print(f"No image files found in: {folder}")
        return 2

    print(f"Testing QR reader with {len(image_paths)} image(s) from {folder}")

    passed = 0
    failed = 0

    for image_path in image_paths:
        frame = cv2.imread(str(image_path))

        if frame is None:
            failed += 1
            print(f"[FAIL] {image_path.name}: OpenCV could not load the image.")
            continue

        decoded, bbox = decode_qr_code(frame)

        if decoded is None:
            failed += 1
            print(f"[FAIL] {image_path.name}: QR decode returned no valid result.")
            continue

        passed += 1
        bbox_status = "present" if bbox is not None else "missing"
        print(
            f"[PASS] {image_path.name}: "
            f"part_id={decoded['part_id']}, "
            f"part_type={decoded['part_type']}, "
            f"bbox={bbox_status}"
        )

    print(f"\nSummary: {passed} passed, {failed} failed, {len(image_paths)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
