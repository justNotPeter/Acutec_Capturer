import os
import time

os.environ["PI_SIM"] = "1"

from app.state_machine import PiOrchestrator, State
from app.communication_interface.pi_io import fanuc, GPIO
from app.config.digital_io import DIGITAL_INPUTS_FROM_FANUC
from app.config.gpio_setup import init_gpio_pins

def fake_decode_qr_code(frame):
    return {
        "part_id": "SIM123",
        "part_type": "A_001_PLATE"
    }


def fake_compute_qc_metrics(frame):
    return {"sharpness": 1.0, "brightness": 1.0}


def fake_check_quality(metrics):
    return True


def set_pin(name: str, high: bool):
    """Helper to set a simulated input pin from Fanuc to Pi."""
    pin = DIGITAL_INPUTS_FROM_FANUC[name]
    GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)
    print(f"[SIM] {name} set to {'HIGH' if high else 'LOW'} (pin {pin})")


def print_status():
    fanuc.report_connection_alive_status()
    fanuc.is_fanuc_in_position_for_capture()
    fanuc.is_every_part_view_capured()

    print("\n================= PI STATE MACHINE =================")
    print(f" Current state     : {PiOrchestrator.current_state}")
    print(f" Current part      : {PiOrchestrator.current_part or '{}'}")
    print(f" View index        : {PiOrchestrator.image_view_index}")
    print(f" Fanuc heartbeat   : {fanuc.is_connected}")
    print(f" In position flag  : {fanuc.is_in_position_for_capture}")
    print(f" Part seq done     : {fanuc.part_sequence_done}")
    print("====================================================\n")


def print_menu():
    print("Actions:")
    print(" 1) Set HEARTBEAT - HIGH")
    print(" 2) Set HEARTBEAT - LOW")
    print(" 3) Set ROBOT_IN_POSITION_FOR_CAPTURE - HIGH")
    print(" 4) Set ROBOT_IN_POSITION_FOR_CAPTURE - LOW")
    print(" 5) Set PART_SEQUENCE_DONE - HIGH")
    print(" 6) Set PART_SEQUENCE_DONE - LOW")
    print(" s) Step state machine once")
    print(" f) Forward 10 steps quickly")
    print(" a) Automate the sequence")
    print(" r) Reset to initial state")
    print(" q) Quit")


def main():
    print("=== PI CAPTURER INTERACTIVE SIMULATION ===")
    
    from app.config.gpio_setup import init_gpio_pins

    PiOrchestrator.init_pi_capturer_system()

    while True:
        print_status()
        print_menu()
        choice = input("\nChoose action: ").strip().lower()

        if choice == "q":
            print("Exiting simulation...")
            fanuc.cleanup()
            break

        elif choice == "1":
            set_pin("HEARTBEAT", True)
        elif choice == "2":
            set_pin("HEARTBEAT", False)

        elif choice == "3":
            set_pin("ROBOT_IN_POSITION_FOR_CAPTURE", True)
        elif choice == "4":
            set_pin("ROBOT_IN_POSITION_FOR_CAPTURE", False)

        elif choice == "5":
            set_pin("PART_SEQUENCE_DONE", True)
        elif choice == "6":
            set_pin("PART_SEQUENCE_DONE", False)

        elif choice == "s":
            print("Running one state-machine step...")
            PiOrchestrator.step_once()

        elif choice == "f":
            print("Running 10 steps...")
            for _ in range(10):
                PiOrchestrator.step_once()
                time.sleep(0.05)
                
        elif choice == "a":
            print("Automating State Machine...")
            PiOrchestrator.automate_sequence()
            
        elif choice == "r":
            print("Reseting state!")
            PiOrchestrator.handle_reset_state()

        else:
            print("Unknown option, try again.")


if __name__ == "__main__":
    main()