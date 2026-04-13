import os
import time

os.environ["PI_SIM"] = "1"

from app.state_machine.pi_state_machine import PiOrchestrator
from app.state_machine.robodk_fanuc_state_machine import RoboDKFanuc
from app.config.gpio_setup import GPIO, init_gpio_pins

from app.config.digital_io import (
    DIGITAL_OUTPUTS_FROM_CONVEYOR_TO_FANUC,
    DIGITAL_OUTPUTS_FROM_FANUC_TO_PI,
    DIGITAL_OUTPUTS_FROM_PI_TO_FANUC,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "simulation.txt")


def log_line(log_file, text: str) -> None:
    log_file.write(text + "\n")
    log_file.flush()


def set_conveyor_part_present(high: bool, log_file=None):
    pin = DIGITAL_OUTPUTS_FROM_CONVEYOR_TO_FANUC["PD_CONVEYOR_STOPPED"]
    GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)

    msg = (
        "[SIM] PD_CONVEYOR_STOPPED set to HIGH (part present)"
        if high
        else "[SIM] PD_CONVEYOR_STOPPED set to LOW (no part)"
    )
    print(msg)
    if log_file:
        log_line(log_file, msg)


def read_pin(mapping: dict, name: str) -> int:
    pin = mapping[name]
    return GPIO.input(pin)


def print_status(robo: RoboDKFanuc, log_file=None):
    hb = read_pin(DIGITAL_OUTPUTS_FROM_FANUC_TO_PI, "HEARTBEAT")
    in_pos = read_pin(DIGITAL_OUTPUTS_FROM_FANUC_TO_PI, "ROBOT_IN_POSITION_FOR_CAPTURE")
    seq_done = read_pin(DIGITAL_OUTPUTS_FROM_FANUC_TO_PI, "PART_SEQUENCE_DONE")

    capture_done = read_pin(DIGITAL_OUTPUTS_FROM_PI_TO_FANUC, "CAPTURE_DONE")
    reset = read_pin(DIGITAL_OUTPUTS_FROM_PI_TO_FANUC, "RESET_SIGNAL")

    conveyor = read_pin(DIGITAL_OUTPUTS_FROM_CONVEYOR_TO_FANUC, "PD_CONVEYOR_STOPPED")

    block = [
        "\n================= FULL SYSTEM STATUS =================",
        " PI STATE MACHINE:",
        f"   current_state   : {PiOrchestrator.current_state}",
        f"   current_part    : {PiOrchestrator.current_part}",
        f"   image_view_idx  : {PiOrchestrator.current_part.get('view_index')}",
        "",
        " ROBO SIM (RoboDKFanuc):",
        f"   current_state   : {robo.current_state}",
        f"   part_type       : {robo.current_part_type}",
        f"   view_idx        : {robo.current_view_idx}",
        "",
        " GPIO SIGNALS:",
        f"   HEARTBEAT (11)                    : {hb}",
        f"   ROBOT_IN_POSITION_FOR_CAPTURE(12) : {in_pos}",
        f"   PART_SEQUENCE_DONE (13)           : {seq_done}",
        f"   CAPTURE_DONE (22)                 : {capture_done}",
        f"   RESET_SIGNAL (24)                 : {reset}",
        f"   PD_CONVEYOR_STOPPED (10)          : {conveyor}",
        "======================================================\n",
    ]

    for line in block:
        print(line)
        if log_file:
            log_line(log_file, line)


def print_menu():
    print("Actions:")
    print(" 1) Simulate PART ARRIVAL (PD_CONVEYOR_STOPPED = HIGH)")
    print(" 2) Clear part (PD_CONVEYOR_STOPPED = LOW)")
    print(" s) Step both Pi + Robot once")
    print(" f) Fast-forward 20 steps")
    print(" a) Auto-run 200 steps")
    print(" q) Quit")


def log_sim_step(
    log_file,
    step_counter: int,
    mode: str,
    robo: RoboDKFanuc,
    substep: int | None = None,
) -> int:
    step_counter += 1

    pi_before = PiOrchestrator.current_state
    robo_before = robo.current_state

    robo.step_once()
    PiOrchestrator.step_once()

    pi_after = PiOrchestrator.current_state
    robo_after = robo.current_state

    pi_from = pi_before.name
    pi_to = pi_after.name
    robo_from = robo_before.name
    robo_to = robo_after.name

    if substep is not None:
        header = f"[STEP {step_counter:04d}] Mode={mode} (substep {substep})"
    else:
        header = f"[STEP {step_counter:04d}] Mode={mode}"

    log_line(log_file, header)
    log_line(
        log_file,
        f"  Pi State : {pi_from} -> {pi_to}"
        if pi_from != pi_to
        else f"  Pi State : {pi_from} (no change)",
    )
    log_line(
        log_file,
        f"  Robo State : {robo_from} -> {robo_to}"
        if robo_from != robo_to
        else f"  Robo State : {robo_from} (no change)",
    )

    log_line(
        log_file,
        f"  Pi Context   : part={PiOrchestrator.current_part}, view_idx={PiOrchestrator.current_part.get('view_index')}",
    )
    log_line(
        log_file,
        f"  Robo Context : part_type={robo.current_part_type}, view_idx={robo.current_view_idx}",
    )
    log_line(log_file, "")  

    return step_counter


def main():
    print("ACUTEC FULL-CELL SIMULATION (Pi + RoboDKFanuc + DummyGPIO)")

    with open(LOG_PATH, "w", encoding="utf-8") as log_file:
        log_line(
            log_file,
            "=== ACUTEC FULL-CELL SIMULATION LOG (Pi + RoboDKFanuc + DummyGPIO) ===",
        )
        init_gpio_pins()
        log_line(log_file, "GPIO pins initialized.")

        PiOrchestrator.init_pi_capturer_system()
        log_line(log_file, "Pi capturer system initialized (camera + IO).")

        robo = RoboDKFanuc(max_views_for_demo=3)
        log_line(log_file, "RoboDK Fanuc simulator initialized.")

        set_conveyor_part_present(False, log_file)

        step_counter = 0

        while True:
            print_status(robo, log_file)
            print_menu()
            choice = input("Choose action: ").strip().lower()

            if choice == "q":
                msg = "Exiting simulation..."
                print(msg)
                log_line(log_file, msg)
                break

            elif choice == "1":
                log_line(log_file, "[USER] Action: Simulate PART ARRIVAL.")
                set_conveyor_part_present(True, log_file)

            elif choice == "2":
                log_line(log_file, "[USER] Action: Clear part (no part present).")
                set_conveyor_part_present(False, log_file)

            elif choice == "s":
                print("[SIM] Stepping system once...")
                log_line(log_file, "[USER] Action: Single step (s).")
                step_counter = log_sim_step(
                    log_file, step_counter, mode="single-step", robo=robo
                )

            elif choice == "f":
                print("[SIM] Fast-forward 20 steps...")
                log_line(log_file, "[USER] Action: Fast-forward 20 steps (f).")
                for i in range(1, 21):
                    step_counter = log_sim_step(
                        log_file,
                        step_counter,
                        mode="fast-forward",
                        robo=robo,
                        substep=i,
                    )
                    time.sleep(0.05)

            elif choice == "a":
                print("[SIM] Auto-running 200 steps...")
                log_line(log_file, "[USER] Action: Auto-run 200 steps (a).")
                for i in range(1, 201):
                    step_counter = log_sim_step(
                        log_file,
                        step_counter,
                        mode="auto-run",
                        robo=robo,
                        substep=i,
                    )
                    time.sleep(0.03)

            else:
                print("Invalid choice, try again.")
                log_line(log_file, f"[USER] Invalid menu choice: {choice!r}")


if __name__ == "__main__":
    main()