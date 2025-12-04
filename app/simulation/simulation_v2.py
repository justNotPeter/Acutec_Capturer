# app/simulation_full.py

import os
import time

# Force simulation mode so Pi + FanucSim both use DummyGPIO
os.environ["PI_SIM"] = "1"

from app.hardware.pi_state_machine import PiOrchestrator
from app.hardware.robodk_fanuc_state_machine import RoboDKFanuc
from app.communication.pi_io import GPIO

from app.config.digital_io import (
    DIGITAL_OUTPUTS_FROM_CONVEYOR_TO_FANUC,
    DIGITAL_OUTPUTS_FROM_FANUC_TO_PI,
    DIGITAL_OUTPUTS_FROM_PI_TO_FANUC,
)


# =====================================================================
# Helper Functions
# =====================================================================

def set_conveyor_part_present(high: bool):
    """
    Simulate the conveyor/sensor telling Fanuc that a part has arrived
    AND the conveyor is stopped.
    """
    pin = DIGITAL_OUTPUTS_FROM_CONVEYOR_TO_FANUC["PD_CONVEYOR_STOPPED"]
    GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)
    print(
        f"[SIM] PD_CONVEYOR_STOPPED set to "
        f"{'HIGH (part present)'}" if high else "LOW (no part)"
    )


def read_pin(mapping: dict, name: str) -> int:
    pin = mapping[name]
    return GPIO.input(pin)


# =====================================================================
# Status Block
# =====================================================================

def print_status(robo: RoboDKFanuc):
    hb = read_pin(DIGITAL_OUTPUTS_FROM_FANUC_TO_PI, "HEARTBEAT")
    in_pos = read_pin(DIGITAL_OUTPUTS_FROM_FANUC_TO_PI, "ROBOT_IN_POSITION_FOR_CAPTURE")
    seq_done = read_pin(DIGITAL_OUTPUTS_FROM_FANUC_TO_PI, "PART_SEQUENCE_DONE")

    capture_done = read_pin(DIGITAL_OUTPUTS_FROM_PI_TO_FANUC, "CAPTURE_DONE")
    reset = read_pin(DIGITAL_OUTPUTS_FROM_PI_TO_FANUC, "RESET_SIGNAL")

    conveyor = read_pin(DIGITAL_OUTPUTS_FROM_CONVEYOR_TO_FANUC, "PD_CONVEYOR_STOPPED")

    print("\n================= FULL SYSTEM STATUS =================")
    print(" PI STATE MACHINE:")
    print(f"   current_state   : {PiOrchestrator.current_state}")
    print(f"   current_part    : {PiOrchestrator.current_part}")
    print(f"   image_view_idx  : {PiOrchestrator.image_view_index}")
    print()
    print(" ROBO SIM (RoboDKFanuc):")
    print(f"   current_state   : {robo.current_state}")
    print(f"   part_type       : {robo.current_part_type}")
    print(f"   view_idx        : {robo.current_view_idx}")
    print()
    print(" GPIO SIGNALS:")
    print(f"   HEARTBEAT (11)                    : {hb}")
    print(f"   ROBOT_IN_POSITION_FOR_CAPTURE(12) : {in_pos}")
    print(f"   PART_SEQUENCE_DONE (13)           : {seq_done}")
    print(f"   CAPTURE_DONE (22)                 : {capture_done}")
    print(f"   RESET_SIGNAL (24)                 : {reset}")
    print(f"   PD_CONVEYOR_STOPPED (10)          : {conveyor}")
    print("======================================================\n")


def print_menu():
    print("Actions:")
    print(" 1) Simulate PART ARRIVAL (PD_CONVEYOR_STOPPED = HIGH)")
    print(" 2) Clear part (PD_CONVEYOR_STOPPED = LOW)")
    print(" s) Step both Pi + Robot once")
    print(" f) Fast-forward 20 steps")
    print(" a) Auto-run 200 steps")
    print(" q) Quit")


# =====================================================================
# Main Simulation Loop
# =====================================================================

def main():
    print("=== ACUTEC FULL-CELL SIMULATION (Pi + RoboDKFanuc + DummyGPIO) ===")

    # 1) Initialize Pi (camera + GPIO)
    PiOrchestrator.init_pi_capturer_system()

    # 2) Initialize Fanuc RoboDK Simulation
    robo = RoboDKFanuc(max_views_for_demo=3)

    # Start simulation with no part present
    set_conveyor_part_present(False)

    while True:
        print_status(robo)
        print_menu()
        choice = input("Choose action: ").strip().lower()

        if choice == "q":
            print("Exiting simulation...")
            break

        elif choice == "1":
            set_conveyor_part_present(True)

        elif choice == "2":
            set_conveyor_part_present(False)

        elif choice == "s":
            print("[SIM] Stepping system once...")
            robo.step_once()
            PiOrchestrator.step_once()

        elif choice == "f":
            print("[SIM] Fast-forward 20 steps...")
            for _ in range(20):
                robo.step_once()
                PiOrchestrator.step_once()
                time.sleep(0.05)

        elif choice == "a":
            print("[SIM] Auto-running 200 steps...")
            for _ in range(200):
                robo.step_once()
                PiOrchestrator.step_once()
                time.sleep(0.03)

        else:
            print("Invalid choice, try again.")


if __name__ == "__main__":
    main()