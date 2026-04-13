from app.config.digital_io import (
    DIGITAL_OUTPUTS_FROM_FANUC_TO_PI,
    DIGITAL_OUTPUTS_FROM_PI_TO_FANUC,
)

from app.config.gpio_setup import GPIO

class FanucIOInterface:
    def __init__(self):
        self.in_position_for_capture = False
        self.part_sequence_done = False
        self.ack = False

        self.capture_done = False
        self.reset_requested = False
        self.recipe_code = 0
        
        self.digital_io_from_fanuc_to_pi = DIGITAL_OUTPUTS_FROM_FANUC_TO_PI
        self.digital_io_from_pi_to_fanuc = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC
        
    # Fanuc sends to Pi 
    def set_in_position_for_capture(self, high: bool) -> bool:
        try:
            pin = self.digital_io_from_fanuc_to_pi["ROBOT_IN_POSITION_FOR_CAPTURE"]
            GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)
            self.in_position_for_capture = high
            
        except Exception as e:
            print(f"[ERROR] set_in_position_for_capture failed: {e}")
        return self.in_position_for_capture
    
    def set_part_sequence_done(self, high: bool) -> bool:
        try:
            pin = self.digital_io_from_fanuc_to_pi["PART_SEQUENCE_DONE"]
            GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)
            self.part_sequence_done = high
            
        except Exception as e:
            print(f"[ERROR] set_part_sequence_done failed: {e}")
        return self.part_sequence_done
    
    def set_ack(self, high: bool) -> bool:
        try:
            pin = self.digital_io_from_fanuc_to_pi["ACKNOWLEDGEMENT"]
            GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)
            self.ack = high
            
        except Exception as e:
            print(f"[ERROR] set_ack failed: {e}")
        return self.ack

    # Fanuc reads Pi 
    def read_capture_done(self) -> bool:
        try:
            pin = self.digital_io_from_pi_to_fanuc["CAPTURE_DONE"]
            status = GPIO.input(pin) == GPIO.HIGH
            self.capture_done = status
            
        except Exception as e:
            print(f"[ERROR] read_capture_done failed: {e}")
            self.capture_done = False
        return self.capture_done

    def read_reset_signal(self) -> bool:
        try:
            pin = self.digital_io_from_pi_to_fanuc["RESET_SIGNAL"]
            status = GPIO.input(pin) == GPIO.HIGH
            self.reset_requested = status
            
        except Exception as e:
            print(f"[ERROR] read_reset_signal failed: {e}")
            self.reset_requested = False
        return self.reset_requested
    
    def read_recipe_code(self) -> int:
        try:
            bit2_pin = self.digital_io_from_pi_to_fanuc["RECIPE_BIT_2"]
            bit1_pin = self.digital_io_from_pi_to_fanuc["RECIPE_BIT_1"]
            bit0_pin = self.digital_io_from_pi_to_fanuc["RECIPE_BIT_0"]

            b2 = GPIO.input(bit2_pin)
            b1 = GPIO.input(bit1_pin)
            b0 = GPIO.input(bit0_pin)

            code = (b2 << 2) | (b1 << 1) | b0
            self.recipe_code = code

        except Exception as e:
            print(f"[ERROR] read_recipe_code failed: {e}")
            self.recipe_code = 0

        return self.recipe_code

FanucRobotIOInterface = FanucIOInterface()