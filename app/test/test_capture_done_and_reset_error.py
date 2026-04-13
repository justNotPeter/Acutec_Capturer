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
        description="Test capture done + error signal + reset signal!"
    )
    return parser.parse_args()


def send_capture_signal() -> None:
    capture_pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["CAPTURE_DONE"]

    time.sleep(0.01)

    GPIO.output(capture_pin, GPIO.HIGH if capture_pin else GPIO.LOW)

    print("Capture signal sent!")
    
def send_reset_signal() -> None:
    reset_pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RESET_SIGNAL"]
    
    time.sleep(0.01)

    GPIO.output(reset_pin, GPIO.HIGH if reset_pin else GPIO.LOW)

    print("RESET signal sent!")
    
def send_error_signal() -> None:
    error_pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["ERROR_SIGNAL"]
    
    time.sleep(0.01)

    GPIO.output(error_pin, GPIO.HIGH if error_pin else GPIO.LOW)

    print("Error signal sent!")

def main() -> int:
    args = parse_args()

    print("Initializing capture + reset + error pins testing...")
    init_gpio_pins()

    try:
        send_capture_signal()
        send_reset_signal()
        send_error_signal()

    except KeyboardInterrupt:
        print("\nStopped by user.")

    return 0


if __name__ == "__main__":
    sys.exit(main())