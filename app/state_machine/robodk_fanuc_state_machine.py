import time
from enum import Enum, auto

from robodk import robolink
from robodk import robomath as rm

from app.communication.pi_io import GPIO
from app.config.digital_io import (
    DIGITAL_OUTPUTS_FROM_CONVEYOR_TO_FANUC,
    DIGITAL_OUTPUTS_FROM_FANUC_TO_PI,
    DIGITAL_OUTPUTS_FROM_PI_TO_FANUC,
)
from app.config.part_recipe import RECIPE_CODE_TO_PART_TYPE


class State(Enum):
    WAITING_FOR_PART = auto()
    WAITING_FOR_RECIPE = auto()
    MOVING_TO_VIEW = auto()
    IN_CAPTURE_POSE = auto()
    SEQUENCE_DONE = auto()
    AT_INITIAL_POSITION = auto()


class RoboDKFanuc:
    def __init__(self, max_views_for_demo: int = 3):
        self.RDK = robolink.Robolink()
        self.robot = self.RDK.Item("Fanuc CRX-10iA/L")

        self.max_views_for_demo = max_views_for_demo

        self.current_state = State.AT_INITIAL_POSITION
        self._is_part_presence = False
        self.current_part_type: str | None = None
        self.current_view_idx: int = 0

        hb_pin = DIGITAL_OUTPUTS_FROM_FANUC_TO_PI["HEARTBEAT"]
        GPIO.output(hb_pin, 1)

        self._set_in_position_for_capture(False)
        self._set_part_sequence_done(False)
        self._set_ack(False)

        self._handlers = {
            State.AT_INITIAL_POSITION: self._handle_moving_to_initial_position,
            State.WAITING_FOR_PART: self._handle_waiting_for_part,
            State.WAITING_FOR_RECIPE: self._handle_waiting_for_recipe,
            State.MOVING_TO_VIEW: self._handle_moving_to_view,
            State.IN_CAPTURE_POSE: self._handle_in_capturing_pose,
            State.SEQUENCE_DONE: self._handle_sequence_done,
        }

        print("[ROBO_SIM] RoboDKFanuc initialized. State = AT_INITIAL_POSITION")

    def _confirm_part_presence(self) -> bool:
        try:
            pin = DIGITAL_OUTPUTS_FROM_CONVEYOR_TO_FANUC["PD_CONVEYOR_STOPPED"]
            status = GPIO.input(pin)
            self._is_part_presence = status == GPIO.HIGH
            return self._is_part_presence
        except Exception as e:
            print(f"Failed reading PD_CONVEYOR_STOPPED: {e}")
            self._is_part_presence = False
            return False

    def _set_in_position_for_capture(self, high: bool):
        pin = DIGITAL_OUTPUTS_FROM_FANUC_TO_PI["ROBOT_IN_POSITION_FOR_CAPTURE"]
        GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)

    def _set_part_sequence_done(self, high: bool):
        pin = DIGITAL_OUTPUTS_FROM_FANUC_TO_PI["PART_SEQUENCE_DONE"]
        GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)

    def _set_ack(self, high: bool):
        pin = DIGITAL_OUTPUTS_FROM_FANUC_TO_PI["ACKNOWLEDGEMENT"]
        GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)

    def _read_capture_done(self) -> int:
        pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["CAPTURE_DONE"]
        return GPIO.input(pin)

    def _read_reset_signal(self) -> int:
        pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RESET_SIGNAL"]
        return GPIO.input(pin)

    def _read_recipe_code(self) -> int:
        bit2_pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RECIPE_BIT_2"]
        bit1_pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RECIPE_BIT_1"]
        bit0_pin = DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RECIPE_BIT_0"]

        b2 = GPIO.input(bit2_pin)
        b1 = GPIO.input(bit1_pin)
        b0 = GPIO.input(bit0_pin)

        code = (b2 << 2) | (b1 << 1) | b0

        print("\n[ROBO_SIM] --- RECIPE DEBUG ---")
        print(f"  Raw GPIO bits: b2={b2}, b1={b1}, b0={b0}")
        print(f"  Combined recipe code (int): {code}")
        print(f"  Combined recipe code (bin): {code:03b}")

        return code

    def _check_capture_done(self) -> bool:
        """Level-based: CAPTURE_DONE == HIGH means Pi says 'capture done'."""
        return self._read_capture_done() == GPIO.HIGH

    def _move_to_initial_pose(self):
        initial_joints_deg = [1.0, 0.0, 0.0, 0.0, -89.76, -0.51]
        print(
            f"[ROBO_SIM] Moving robot to INITIAL / QR pose (hard-coded joints)... "
            f"{initial_joints_deg}"
        )
        try:
            self.robot.MoveJ(initial_joints_deg)
        except Exception as e:
            print(f"[ROBO_SIM] ERROR: Failed to move to initial pose: {e}")
        time.sleep(0.2)

    def _move_to_capture_view(self, view_idx: int):
        print(f"[ROBO_SIM] Moving to capture pose for view #{view_idx}...")
        # target_name = f"{self.current_part_type}_VIEW_{view_idx}"
        # target = self.RDK.Item(target_name)
        # self.robot.MoveJ(target)
        time.sleep(0.3)


    def step_once(self):
        if self._read_reset_signal():
            self._handle_reset_from_pi()

        handler = self._handlers[self.current_state]
        next_state = handler()

        if next_state is not None and next_state != self.current_state:
            print(f"[ROBO_SIM] Transition: {self.current_state.name} -> {next_state.name}")
            self.current_state = next_state


    def _handle_moving_to_initial_position(self) -> State | None:
        self._move_to_initial_pose()
        self._set_part_sequence_done(False)
        self._set_in_position_for_capture(False)
        self._set_ack(False)

        print("[ROBO_SIM] At INITIAL/QR pose. in_position=FALSE.")
        print(
            "[ROBO_SIM] Waiting for conveyor/sensor to signal PART_PRESENT "
            "(conveyor stopped with part)."
        )
        return State.WAITING_FOR_PART

    def _handle_waiting_for_part(self) -> State | None:
        if not self._confirm_part_presence():
            return None

        print("[ROBO_SIM] Part detected & conveyor stopped. Setting in_position=HIGH.")
        self._set_in_position_for_capture(True)
        return State.WAITING_FOR_RECIPE

    def _handle_waiting_for_recipe(self) -> State | None:
        code = self._read_recipe_code()
        part_type = RECIPE_CODE_TO_PART_TYPE.get(code)

        if not part_type:
            return None

        self.current_part_type = part_type
        self.current_view_idx = 0

        # ACK=1: "recipe confirmed"
        self._set_ack(True)
        print(f"[ROBO_SIM] Recipe received: code={code:03b}, part_type={part_type}")

        self._set_in_position_for_capture(False)
        return State.MOVING_TO_VIEW

    def _handle_moving_to_view(self) -> State | None:
        # We are now moving; clear ACK so it can be reused for capture ack
        self._set_ack(False)

        self._move_to_capture_view(self.current_view_idx)
        self._set_in_position_for_capture(True)
        print(
            f"[ROBO_SIM] Reached capture pose for view #{self.current_view_idx}, "
            "in_position=HIGH"
        )
        return State.IN_CAPTURE_POSE

    def _handle_in_capturing_pose(self) -> State | None:
        # Level check: wait until Pi sets CAPTURE_DONE = HIGH
        if not self._check_capture_done():
            return None

        print(f"[ROBO_SIM] Got CAPTURE_DONE for view #{self.current_view_idx} from Pi.")
        self._set_in_position_for_capture(False)

        # ACK=1: "capture done processed"
        self._set_ack(True)

        # If more views, move on
        if self.current_view_idx < self.max_views_for_demo - 1:
            self.current_view_idx += 1
            print(f"[ROBO_SIM] Preparing to move to next view #{self.current_view_idx}...")
            return State.MOVING_TO_VIEW

        # Last view: PART_SEQUENCE_DONE=HIGH
        self._set_part_sequence_done(True)
        print("[ROBO_SIM] All views captured. PART_SEQUENCE_DONE=HIGH (latched).")
        return State.SEQUENCE_DONE

    def _handle_sequence_done(self) -> State | None:
        # Wait for RESET from Pi
        return None

    def _handle_reset_from_pi(self):
        """
        Pi calls fanuc.send_reset_signal(), which pulses RESET_SIGNAL.

        In response, RoboSim:
          - clears PART_SEQUENCE_DONE;
          - clears ACK;
          - clears current_part_type and current_view_idx;
          - goes back to AT_INITIAL_POSITION.
        """
        print("[ROBO_SIM] RESET_SIGNAL from Pi received. Resetting sequence.")
        self._set_part_sequence_done(False)
        self._set_ack(False)
        self.current_part_type = None
        self.current_view_idx = 0
        self.current_state = State.AT_INITIAL_POSITION