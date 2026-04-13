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
        description="Test CAPTURE_DONE, RESET_SIGNAL, or ERROR_SIGNAL from the Pi."
    )
    parser.add_argument(
        "--signal",
        choices=("capture", "reset", "error"),
        required=True,
        help="Which GPIO signal to test.",
    )
    parser.add_argument(
        "--hold-seconds",
        type=float,
        default=2.0,
        help="How long to hold CAPTURE_DONE or RESET_SIGNAL high before clearing it.",
    )
    parser.add_argument(
        "--pulse-seconds",
        type=float,
        default=0.1,
        help="Pulse width for ERROR_SIGNAL.",
    )
    return parser.parse_args()


def set_pin_high(pin: int, name: str) -> None:
    GPIO.output(pin, GPIO.HIGH)
    print(f"{name} asserted HIGH on BCM pin {pin}.")


def set_pin_low(pin: int, name: str) -> None:
    GPIO.output(pin, GPIO.LOW)
    print(f"{name} cleared LOW on BCM pin {pin}.")


def send_capture_done(hold_seconds: float) -> None:
    pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["CAPTURE_DONE"]
    set_pin_high(pin, "CAPTURE_DONE")
    print(f"Holding CAPTURE_DONE high for {hold_seconds} seconds...")
    time.sleep(hold_seconds)
    set_pin_low(pin, "CAPTURE_DONE")


def send_reset_signal(hold_seconds: float) -> None:
    pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RESET_SIGNAL"]
    set_pin_high(pin, "RESET_SIGNAL")
    print(f"Holding RESET_SIGNAL high for {hold_seconds} seconds...")
    time.sleep(hold_seconds)
    set_pin_low(pin, "RESET_SIGNAL")


def send_error_signal(pulse_seconds: float) -> None:
    pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["ERROR_SIGNAL"]
    set_pin_high(pin, "ERROR_SIGNAL")
    print(f"Pulsing ERROR_SIGNAL for {pulse_seconds} seconds...")
    time.sleep(pulse_seconds)
    set_pin_low(pin, "ERROR_SIGNAL")


def clear_all_test_outputs() -> None:
    for name in ("CAPTURE_DONE", "RESET_SIGNAL", "ERROR_SIGNAL"):
        pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC[name]
        GPIO.output(pin, GPIO.LOW)


def main() -> int:
    args = parse_args()

    print("Initializing GPIO for capture/reset/error test...")
    init_gpio_pins()
    clear_all_test_outputs()

    try:
        if args.signal == "capture":
            send_capture_done(args.hold_seconds)
        elif args.signal == "reset":
            send_reset_signal(args.hold_seconds)
        else:
            send_error_signal(args.pulse_seconds)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        clear_all_test_outputs()

    return 0


if __name__ == "__main__":
    sys.exit(main())
