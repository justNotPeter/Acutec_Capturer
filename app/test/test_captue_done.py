import argparse
import os
import sys
import time

# Default to real Raspberry Pi GPIO for this hardware test script.
os.environ.setdefault("PI_SIM", "0")

from app.config.digital_io import DIGITAL_OUTPUTS_FROM_PI_TO_FANUC
from app.config.gpio_setup import GPIO, init_gpio_pins


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test capture done!"
    )
    return parser.parse_args()


def set_recipe_bits(code: int) -> None:
    capture_pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["CAPTURE_DONE"]

    time.sleep(0.01)

    GPIO.output(capture_pin, GPIO.HIGH if capture_pin else GPIO.LOW)

    print("Capture signal sent!")

def main() -> int:
    args = parse_args()

    print("Initializing capture pin testing...")
    init_gpio_pins()

    try:
        set_recipe_bits(args.code)

    except KeyboardInterrupt:
        print("\nStopped by user.")

    return 0


if __name__ == "__main__":
    sys.exit(main())