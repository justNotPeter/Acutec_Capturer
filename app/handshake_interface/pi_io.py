import os
import time
from app.config.digital_io import (
    DIGITAL_OUTPUTS_FROM_FANUC_TO_PI, 
    DIGITAL_OUTPUTS_FROM_PI_TO_FANUC, 
)

from app.config.part_recipe import PART_TYPE_TO_RECIPE_CODE
from app.config.gpio_setup import GPIO

class PiIOInterface:
    def __init__(self):
        self.initialized = False
        self.is_connected = False
        self.is_in_position_for_capture = False
        self.part_type_recipe = None
        self.part_sequence_done = False
        
        self.digital_io_from_fanuc_to_pi = DIGITAL_OUTPUTS_FROM_FANUC_TO_PI
        self.digital_io_from_pi_to_fanuc = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC
            
    
    # Pi sends to Fanuc
    def set_capture_done(self, high: bool):
        try:
            pin = self.digital_io_from_pi_to_fanuc["CAPTURE_DONE"]
            output_state = GPIO.HIGH if high else GPIO.LOW
            
            GPIO.output(pin, output_state)
            print(f"SEND CAPTURE_DONE: {'HIGH' if high else 'LOW'}")

        except Exception as e:
            print(f"Failed to set CAPTURE_DONE: {e}")
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
        
    def send_reset_signal(self):
        try:
            pin = self.digital_io_from_pi_to_fanuc["RESET_SIGNAL"]
            GPIO.output(pin, GPIO.HIGH)
            
            print(f"RESET signal sent!")
            
        except Exception as e:
            print(f"Failed to send RESET_SEQUENCE: {e}")
            self.send_error_signal()
            
    def clear_reset_signal(cls):
        try:
            pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RESET_SIGNAL"]
            GPIO.output(pin, GPIO.LOW)
            print("RESET signal cleared!")
            
        except Exception as e:
            print(f"Failed to clear RESET_SIGNAL: {e}")
            cls.send_error_signal()
        
    def send_error_signal(self):
        try:
            pin = self.digital_io_from_pi_to_fanuc["ERROR_SIGNAL"]
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output(pin, GPIO.LOW)
            print("ERROR signal sent!")
            
        except Exception as e:
            print(f"Could not send ERROR signal: {e}")
            

    # Pi reads Fanuc
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
        
    # def is_recipe_confirmed(self) -> bool:
    #     try:
    #         pin = self.digital_io_from_fanuc_to_pi["RECIPE_CONFIRMED"]
    #         status = GPIO.input(pin)
    #         return status == GPIO.HIGH
    #     except Exception as e:
    #         print(f"Failed reading RECIPE_CONFIRMED: {e}")
    #         return False
    
    def is_robot_ack(self) -> bool:
        try:
            pin = self.digital_io_from_fanuc_to_pi["ACKNOWLEDGEMENT"]
            status = GPIO.input(pin)
            return status == GPIO.HIGH
        except Exception as e:
            print(f"Failed reading ACKNOWLEDGEMENT: {e}")
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
    

    def cleanup(self):
        try:
            GPIO.cleanup()
            print("GPIO cleanup complete!")
            
        except Exception as e:
            print(f"GPIO cleanup failed: {e}")

PiCapturerIOInterface = PiIOInterface()