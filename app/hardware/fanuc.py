import os
import time
from app.config.digital_io import (
    DIGITAL_INPUTS_FROM_FANUC, 
    DIGITAL_OUTPUTS_FROM_PI, 
)

from app.config.part_recipe import PART_TYPE_TO_RECIPE_CODE

SIMULATION_MODE = os.getenv("PI_SIM", "1") == "1"

if not SIMULATION_MODE:
    import RPi.GPIO as GPIO
    print("Using Raspberry Pi GPIO")
else:
    from app.external.dummy_gpio import GPIO
    print("Using DummyGPIO (Simulation Mode)")


class Fanuc:
    def __init__(self):
        self.initialized = False
        self.is_connected = False
        self.is_in_position_for_capture = False
        self.part_type_recipe = None
        self.part_sequence_done = False
        

        self.digital_io_from_fanuc_to_pi = DIGITAL_INPUTS_FROM_FANUC
        self.digital_io_from_pi_to_fanuc = DIGITAL_OUTPUTS_FROM_PI

    def init_GPIO(self):
        if self.initialized:
            return
        
        try:
            GPIO.setmode(GPIO.BCM)

            GPIO.setup(
                self.digital_io_from_fanuc_to_pi["HEARTBEAT"], 
                GPIO.IN, pull_up_down=GPIO.PUD_DOWN
            )
            GPIO.setup(
                self.digital_io_from_fanuc_to_pi["ROBOT_IN_POSITION_FOR_CAPTURE"], 
                GPIO.IN, pull_up_down=GPIO.PUD_DOWN
            )

            GPIO.setup(self.digital_io_from_pi_to_fanuc["CAPTURE_DONE"], GPIO.OUT)
            GPIO.setup(self.digital_io_from_pi_to_fanuc["ERROR_SIGNAL"], GPIO.OUT)
            GPIO.setup(self.digital_io_from_pi_to_fanuc["RECIPE_BIT_2"], GPIO.OUT)
            GPIO.setup(self.digital_io_from_pi_to_fanuc["RECIPE_BIT_1"], GPIO.OUT)
            GPIO.setup(self.digital_io_from_pi_to_fanuc["RECIPE_BIT_0"], GPIO.OUT)

            self.initialized = True
            print("GPIO initialized successfully!")

        except Exception as e:
            print(f"Failed to initialize GPIO: {e}")
            self.initialized = False

    # Reading Fanuc from Pi
    def report_connection_alive_status(self) -> bool:
        try:
            pin = self.digital_io_from_fanuc_to_pi["HEARTBEAT"]
            status = GPIO.input(pin)
            self.is_connected = (status == GPIO.HIGH)
            return self.is_connected

        except Exception as e:
            print(f"Failed reading HEARTBEAT: {e}")
            self.is_connected = False
            return False

    def is_fanuc_in_position_for_capture(self) -> bool:
        try:
            pin = self.digital_io_from_fanuc_to_pi["ROBOT_IN_POSITION_FOR_CAPTURE"]
            status = GPIO.input(pin)
            self.is_in_position_for_capture = (status == GPIO.HIGH)
            return self.is_in_position_for_capture

        except Exception as e:
            print(f"Failed reading ROBOT_IN_POSITION_FOR_CAPTURE: {e}")
            self.is_in_position_for_capture = False
            return False
        
    def is_every_part_view_capured(self) -> bool:
        try:
            pin = self.digital_io_from_fanuc_to_pi["PART_SEQUENCE_DONE"]
            status = GPIO.input(pin)

            self.part_sequence_done = (status == GPIO.HIGH)

            return self.part_sequence_done

        except Exception as e:
            print(f"[ERROR] Failed reading PART_SEQUENCE_DONE: {e}")
            self.part_sequence_done = False
            return False
        
    # Outputting from Pi to Fanuc
    def send_capture_done(self, pulse_seconds: float = 0.05):
        try:
            pin = self.digital_io_from_pi_to_fanuc["CAPTURE_DONE"]

            GPIO.output(pin, GPIO.HIGH)
            time.sleep(pulse_seconds)
            GPIO.output(pin, GPIO.LOW)

            print(f"PULSE CAPTURE_DONE ({pulse_seconds}s)")

        except Exception as e:
            print(f"Failed to send CAPTURE_DONE: {e}")
            self.send_error_signal()

    def send_required_recipe(self, part_type: str) -> bool:
        try:
            code = PART_TYPE_TO_RECIPE_CODE.get(part_type)
            
            if code is None:
                print(f"Unknown part type '{part_type}'!")
                self.send_error_signal()
                return False
            
            bit2_pin = self.digital_io_from_pi_to_fanuc["RECIPE_BIT_2"]
            bit1_pin = self.digital_io_from_pi_to_fanuc["RECIPE_BIT_1"]
            bit0_pin = self.digital_io_from_pi_to_fanuc["RECIPE_BIT_0"]

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

            print(f"Sent recipe code {code:03b} for part '{part_type}'!")
            return True

        except Exception as e:
            print(f"Failed to send recipe bits: {e}")
            self.send_error_signal()
            return False
        
    def send_reset_signal(self, pulse_seconds: float = 0.05):
        try:
            pin = self.digital_io_from_pi_to_fanuc["RESET_SIGNAL"]
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(pulse_seconds)
            GPIO.output(pin, GPIO.LOW)
            
            print(f"RESET signal sent for ({pulse_seconds}s)!")
            
        except Exception as e:
            print(f"Failed to send RESET_SEQUENCE: {e}")
            self.send_error_signal()
        
    def send_error_signal(self):
        try:
            pin = self.digital_io_from_pi_to_fanuc["ERROR_SIGNAL"]
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output(pin, GPIO.LOW)
            print("ERROR signal sent!")
            
        except Exception as e:
            print(f"Could not send ERROR signal: {e}")

    def cleanup(self):
        try:
            GPIO.cleanup()
            print("GPIO cleanup complete!")
            
        except Exception as e:
            print(f"GPIO cleanup failed: {e}")

fanuc = Fanuc()