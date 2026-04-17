import os
import sys
import time

os.environ.setdefault("PI_SIM", "0")

from app.config.digital_io import DIGITAL_OUTPUTS_FROM_FANUC_TO_PI
from app.config.gpio_setup import init_gpio_pins
from app.handshake_interface.pi_io import PiCapturerIOInterface


POLL_INTERVAL_SECONDS = 0.1


def main() -> int:
    heartbeat_pin = DIGITAL_OUTPUTS_FROM_FANUC_TO_PI["HEARTBEAT"]

    print(f"Initializing GPIO and waiting for HEARTBEAT on BCM pin {heartbeat_pin}...")
    init_gpio_pins()

    print("Waiting for robot heartbeat...")

    try:
        while True:
            if PiCapturerIOInterface.report_connection_alive_status():
                print(f"Heartbeat detected on BCM pin {heartbeat_pin}.")
                return 0

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nStopped while waiting for heartbeat.")
        return 130


if __name__ == "__main__":
    sys.exit(main())