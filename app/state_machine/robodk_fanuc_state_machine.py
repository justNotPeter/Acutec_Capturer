import time
from enum import Enum, auto

from robodk import robolink
from robodk import robomath as rm

from app.config.gpio_setup import GPIO
from app.config.digital_io import (
    DIGITAL_OUTPUTS_FROM_CONVEYOR_TO_FANUC,
    DIGITAL_OUTPUTS_FROM_FANUC_TO_PI,
    DIGITAL_OUTPUTS_FROM_PI_TO_FANUC,
)

from app.config.part_recipe import RECIPE_CODE_TO_PART_TYPE

from app.handshake_interface.fanuc_io import FanucRobotIOInterface

class FanucState(Enum):
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
        
        self.io = FanucRobotIOInterface

        self.max_views_for_demo = max_views_for_demo

        self.current_state = FanucState.AT_INITIAL_POSITION
        self._is_part_presence = False
        self.current_part_type: str | None = None
        self.current_view_idx: int = 0

        hb_pin = DIGITAL_OUTPUTS_FROM_FANUC_TO_PI["HEARTBEAT"]
        GPIO.output(hb_pin, 1)

        self.io.set_in_position_for_capture(False)
        self.io.set_part_sequence_done(False)
        self.io.set_ack(False)

        self._handlers = {
            FanucState.AT_INITIAL_POSITION: self._handle_moving_to_initial_position,
            FanucState.WAITING_FOR_PART: self._handle_waiting_for_part,
            FanucState.WAITING_FOR_RECIPE: self._handle_waiting_for_recipe,
            FanucState.MOVING_TO_VIEW: self._handle_moving_to_view,
            FanucState.IN_CAPTURE_POSE: self._handle_in_capturing_pose,
            FanucState.SEQUENCE_DONE: self._handle_sequence_done,
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
        if self.io.read_reset_signal():
            self._handle_reset_from_pi()

        handler = self._handlers[self.current_state]
        next_state = handler()

        if next_state is not None and next_state != self.current_state:
            print(f"[ROBO_SIM] Transition: {self.current_state.name} -> {next_state.name}")
            self.current_state = next_state


    def _handle_moving_to_initial_position(self) -> FanucState | None:
        self._move_to_initial_pose()
        self.io.set_part_sequence_done(False)
        self.io.set_in_position_for_capture(False)
        self.io.set_ack(False)
        
        print("[ROBO_SIM] At INITIAL/QR pose. in_position=FALSE.")
        print(
            "[ROBO_SIM] Waiting for conveyor/sensor to signal PART_PRESENT "
            "(conveyor stopped with part)."
        )
        return FanucState.WAITING_FOR_PART

    def _handle_waiting_for_part(self) -> FanucState | None:
        if not self._confirm_part_presence():
            return None

        print("[ROBO_SIM] Part detected & conveyor stopped. Setting in_position=HIGH.")
        self.io.set_in_position_for_capture(True)
        return FanucState.WAITING_FOR_RECIPE

    def _handle_waiting_for_recipe(self) -> FanucState | None:
        code = self.io.read_recipe_code()
        part_type = RECIPE_CODE_TO_PART_TYPE.get(code)

        print(f"Combined recipe code (int) from robot: {code}")

        if not part_type:
            return None

        self.current_part_type = part_type
        self.current_view_idx = 0

        self.io.set_ack(True)
        print(f"[ROBO_SIM] Recipe received: code={code:03b}, part_type={part_type}")

        self.io.set_in_position_for_capture(False)
        return FanucState.MOVING_TO_VIEW

    def _handle_moving_to_view(self) -> FanucState | None:
        self.io.set_ack(False)

        self._move_to_capture_view(self.current_view_idx)
        self.io.set_in_position_for_capture(True)
        print(
            f"[ROBO_SIM] Reached capture pose for view #{self.current_view_idx}, "
            "in_position=HIGH"
        )
        return FanucState.IN_CAPTURE_POSE

    def _handle_in_capturing_pose(self) -> FanucState | None:
        if not self.io.read_capture_done():
            return None

        print(f"[ROBO_SIM] Got CAPTURE_DONE for view #{self.current_view_idx} from Pi.")
        self.io.set_in_position_for_capture(False)

        self.io.set_ack(True)

        if self.current_view_idx < self.max_views_for_demo - 1:
            self.current_view_idx += 1
            print(f"[ROBO_SIM] Preparing to move to next view #{self.current_view_idx}...")
            return FanucState.MOVING_TO_VIEW

        self.io.set_part_sequence_done(True)
        print("[ROBO_SIM] All views captured. PART_SEQUENCE_DONE=HIGH (latched).")
        return FanucState.SEQUENCE_DONE

    def _handle_sequence_done(self) -> FanucState | None:
        return None

    def _handle_reset_from_pi(self):
        print("[ROBO_SIM] RESET_SIGNAL from Pi received. Resetting sequence.")
        self.io.set_part_sequence_done(False)
        self.io.set_ack(False)
        self.current_part_type = None
        self.current_view_idx = 0
        self.current_state = FanucState.AT_INITIAL_POSITION
        
RoboDKFanucPerformer = RoboDKFanuc()