from app.config.digital_io import (
    DIGITAL_OUTPUTS_FROM_FANUC_TO_PI,
    DIGITAL_OUTPUTS_FROM_PI_TO_FANUC,
)

from app.config.gpio_setup import GPIO

class FanucRobotIO:
    def __init__(self):
        self.in_position_for_capture = False
        self.part_sequence_done = False
        self.ack = False

        self.capture_done = False
        self.reset_requested = False
        self.recipe_code = 0
        
        self.digital_io_from_fanuc_to_pi = DIGITAL_OUTPUTS_FROM_FANUC_TO_PI
        self.digital_io_from_pi_to_fanuc = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC

    # Robot sends to Pi
    def set_in_position_for_capture(self, high: bool) -> bool:
        pin = self.digital_io_from_fanuc_to_pi["ROBOT_IN_POSITION_FOR_CAPTURE"]
        GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)
        self.in_position_for_capture = high
        return self.in_position_for_capture

    def set_part_sequence_done(self, high: bool) -> bool:
        pin = self.digital_io_from_fanuc_to_pi["PART_SEQUENCE_DONE"]
        GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)
        self.part_sequence_done = high
        return self.part_sequence_done

    def set_ack(self, high: bool) -> bool:
        pin = self.digital_io_from_fanuc_to_pi["ACKNOWLEDGEMENT"]
        GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)
        self.ack = high
        return self.ack


    # Robot reads Pi 
    def read_capture_done(self) -> bool:
        """Read CAPTURE_DONE from Pi, update internal state, and return it."""
        pin = self.digital_io_from_pi_to_fanuc["CAPTURE_DONE"]
        status = GPIO.input(pin) == GPIO.HIGH
        self.capture_done = status
        return self.capture_done

    def read_reset_signal(self) -> bool:
        """Read RESET_SIGNAL from Pi, update internal state, and return it."""
        pin = self.digital_io_from_pi_to_fanuc["RESET_SIGNAL"]
        status = GPIO.input(pin) == GPIO.HIGH
        self.reset_requested = status
        return self.reset_requested

    def read_recipe_code(self) -> int:
        """
        Read the 3 recipe bits from Pi, combine into a code (0–7),
        store it on self.recipe_code, and return it.
        """
        bit2_pin = self.digital_io_from_pi_to_fanuc["RECIPE_BIT_2"]
        bit1_pin = self.digital_io_from_pi_to_fanuc["RECIPE_BIT_1"]
        bit0_pin = self.digital_io_from_pi_to_fanuc["RECIPE_BIT_0"]

        b2 = GPIO.input(bit2_pin)
        b1 = GPIO.input(bit1_pin)
        b0 = GPIO.input(bit0_pin)

        code = (b2 << 2) | (b1 << 1) | b0
        self.recipe_code = code
        return self.recipe_code


FanucRobotIOInterface = FanucRobotIO()