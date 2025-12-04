from enum import Enum, auto
from app.hardware.camera import camera
from app.communication_interface.pi_io import PiIOInterface
from app.service.qr_code_reader import decode_qr_code
from app.service.quality_control import compute_qc_metrics, check_quality
import time

class State(Enum):
    WAITING_FOR_PART = auto()
    SCANNING_QR_CODE = auto()
    SENDING_RECIPE = auto()
    WAITING_FOR_RECIPE_CONFIRMATION = auto()
    WAITING_FOR_ROBOT_POSE = auto()
    CAPTURING_OBJECT_VIEW = auto()
    WAITING_FOR_CAPTURE_ACK = auto() 
    DONE = auto()
    ERROR = auto()
    
class PiStateMachine:
    def __init__(self):
        self.camera = camera
        self.robot_interface = PiIOInterface
        
        self.current_state = State.WAITING_FOR_PART
        self.current_part = {}
        self.max_qr_tries = 3
        self.max_capture_tries = 5
        self.image_view_index = 0
        
        self.function_handler = {
            State.WAITING_FOR_PART: self._handle_waiting_for_part,
            State.SCANNING_QR_CODE: self._handle_scanning_for_qr_code,
            State.SENDING_RECIPE: self._handle_sending_recipe,
            State.WAITING_FOR_RECIPE_CONFIRMATION: self._handle_waiting_for_recipe_confirmation,
            State.WAITING_FOR_ROBOT_POSE: self._handle_waiting_for_robot_pose,
            State.CAPTURING_OBJECT_VIEW: self._handle_capturing_object_view,
            State.WAITING_FOR_CAPTURE_ACK: self._handle_waiting_for_capture_ack, 
            State.DONE: self._handle_done,
            State.ERROR: self._handle_error,
        }
        
    def init_pi_capturer_system(self):
        self.camera.init_camera()
        self.robot_interface.init_GPIO()
        print(f"System started! Current state is {self.current_state}")
        
    def step_once(self):
        health_state = self.check_robot_health()
        
        if health_state is not None:
            if self.current_state != health_state:
                print(f"Please check Fanuc for connection, system is in ERROR state!")
                
            self.current_state = health_state
            return

        handler = self.function_handler[self.current_state]
        next_state = handler()

        if next_state is not None and next_state != self.current_state:
            print(f"Transition from {self.current_state} -> {next_state}")
            self.current_state = next_state
        
    def automate_sequence(self):
        print("Automating PSM sequence...")
        
        while True:
            self.step_once()
            
                 
    def check_robot_health(self):
        if not self.robot_interface.report_connection_alive_status():
            print("❌ No heartbeat from Fanuc!")
            return State.ERROR
        return
    
              
    def _handle_waiting_for_part(self):
        print("Waiting for new part to arrive")
        
        if self.robot_interface.is_fanuc_in_position_for_capture():
            print("Part detected - Fanuc is in position for scanning QR code!")
            return State.SCANNING_QR_CODE
        
        time.sleep(0.02)
        return 
    
    
    def _handle_scanning_for_qr_code(self):
        print("Sanning for QR code!")
        
        qr_retry_count = 0
        qr_code_data = None
        
        while not qr_code_data and qr_retry_count <= self.max_qr_tries:
            frame = self.camera.capture_frame()
            qr_code_data, bbox = decode_qr_code(frame, simulated_result={"part_id": "SIM_001","part_type": "A_001_PLATE"})
            
            if qr_code_data:
                print(f"QR Code Detected: {qr_code_data}")
                break
            
            qr_retry_count += 1
            print(f"❌ QR code not detected. Retry {qr_retry_count}/{self.max_qr_tries}...")
            time.sleep(0.1)
        
        if not qr_code_data:
            print(f"❌ Failed to read QR code after {self.max_qr_tries} times!")
            return State.ERROR
            
        self.current_part = {
            "id": qr_code_data["part_id"],
            "type": qr_code_data["part_type"]
        }
        
        return State.SENDING_RECIPE
    
    
    def _handle_sending_recipe(self):
        part_type = self.current_part["type"]
        
        print(f"Sending part type recipe for {part_type} to Fanuc!")
        
        success = self.robot_interface.send_required_recipe(part_type)
        
        if not success:
            print("❌ Could not send recipe to Fanuc!")
            return State.ERROR
        
        print("Waiting for robot to move to capture pose…")
        return State.WAITING_FOR_RECIPE_CONFIRMATION
    
    def _handle_waiting_for_recipe_confirmation(self):
        # if self.robot_interface.is_recipe_confirmed():
        if self.robot_interface.is_robot_ack():
            print("Robot confirmed recipe!")
            return State.WAITING_FOR_ROBOT_POSE
        return None
    
        
    def _handle_waiting_for_robot_pose(self):
        print("Checking pose and sequence status...")

        if self.robot_interface.is_every_part_view_capured():
            print("✅ Part sequence done. All views captured!")
            time.sleep(0.1)
            return State.DONE

        if not self.robot_interface.is_fanuc_in_position_for_capture():
            time.sleep(0.05)
            return 

        print("Requesting capture view!")
        return State.CAPTURING_OBJECT_VIEW
    
    
    def _handle_capturing_object_view(self):
        print("Capturing image!")
        
        num_try = 0
        qc_pass = False
        frame = None

        while num_try < self.max_capture_tries and not qc_pass:
            frame = self.camera.capture_frame()
            
            frame_metrics = compute_qc_metrics(frame, simulated_result={"sharpness": 110, "brightness": 70, "contrast": 30})
            qc_pass = check_quality(frame_metrics)
            
            if qc_pass:
                print(f"View #{self.image_view_index} passed QC!")
                break
            
            num_try += 1
            print(f"❌ Image did not pass at qc check. Retry {num_try}/{self.max_capture_tries}...")
            time.sleep(0.05)
            
        if not qc_pass:
            print("[PI] ❌ Max retries reached for this view. Going to ERROR.")
            self.robot_interface.send_error_signal()
            return State.ERROR
            
        self.image_view_index += 1
                
        self.current_part["view_index"] = self.image_view_index
        
        # send_to_jetson(frame: nparray, current_part: dict)

        self.robot_interface.set_capture_done(True)
        return State.WAITING_FOR_CAPTURE_ACK
    
    
    def _handle_done(self):
        print(f"Part {self.current_part.get('id')} fully processed!")
        self.current_part = {}
        self.image_view_index = 0
        
        self.robot_interface.set_capture_done(False)
        
        self.robot_interface.send_reset_signal()
        return State.WAITING_FOR_PART
    
    
    
    def _handle_waiting_for_capture_ack(self):
        if self.robot_interface.is_robot_ack():
            print("Robot acknowledged CAPTURE_DONE, waiting for next pose…")
            
            self.robot_interface.set_capture_done(False)
            return State.WAITING_FOR_ROBOT_POSE
        return None
    
    
    def _handle_error(self):
        print("ERROR: Staying in error for now!")
        
        self.robot_interface.send_error_signal()
        time.sleep(0.5)
        return
    
    
    def handle_reset_state(self):
        return State.WAITING_FOR_PART
    
PiOrchestrator = PiStateMachine()