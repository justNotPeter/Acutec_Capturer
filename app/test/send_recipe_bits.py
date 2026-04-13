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
        description="Drive the 3 recipe GPIO bits from the Pi to the robot."
    )
    parser.add_argument(
        "--code",
        type=int,
        required=True,
        help="3-bit recipe code to send (0-7).",
    )
    parser.add_argument(
        "--hold-seconds",
        type=float,
        default=5.0,
        help="How long to hold the recipe bits before clearing them. Use a negative value to hold until Ctrl+C.",
    )
    return parser.parse_args()


def set_recipe_bits(code: int) -> None:
    bit2_pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["CAPTURE_DONE"]
    # bit1_pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RECIPE_BIT_1"]
    # bit0_pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RECIPE_BIT_0"]

    bit2 = (code >> 2) & 1
    bit1 = (code >> 1) & 1
    bit0 = code & 1

    GPIO.output(bit2_pin, GPIO.LOW)
    GPIO.output(bit1_pin, GPIO.LOW)
    GPIO.output(bit0_pin, GPIO.LOW)
    time.sleep(0.01)

    GPIO.output(bit2_pin, GPIO.HIGH if bit2 else GPIO.LOW)
    GPIO.output(bit1_pin, GPIO.HIGH if bit1 else GPIO.LOW)
    GPIO.output(bit0_pin, GPIO.HIGH if bit0 else GPIO.LOW)

    print(
        "Recipe bits sent:"
        f" code={code} ({code:03b}),"
        f" RECIPE_BIT_2 pin {bit2_pin}={bit2},"
        f" RECIPE_BIT_1 pin {bit1_pin}={bit1},"
        f" RECIPE_BIT_0 pin {bit0_pin}={bit0}"
    )


def clear_recipe_bits() -> None:
    for name in ("RECIPE_BIT_2", "RECIPE_BIT_1", "RECIPE_BIT_0"):
        GPIO.output(DIGITAL_OUTPUTS_FROM_PI_TO_FANUC[name], GPIO.LOW)

    print("Recipe bits cleared to LOW.")


def main() -> int:
    args = parse_args()

    if not 0 <= args.code <= 7:
        print("Invalid --code value. Use an integer from 0 to 7.")
        return 2

    print("Initializing GPIO for recipe-bit test...")
    init_gpio_pins()

    try:
        set_recipe_bits(args.code)

        if args.hold_seconds < 0:
            print("Holding recipe bits until Ctrl+C...")
            while True:
                time.sleep(1.0)
        else:
            print(f"Holding recipe bits for {args.hold_seconds} seconds...")
            time.sleep(args.hold_seconds)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        clear_recipe_bits()

    return 0


if __name__ == "__main__":
    sys.exit(main())
