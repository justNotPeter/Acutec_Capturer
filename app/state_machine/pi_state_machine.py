import time
import cv2

from datetime import datetime, timezone
import numpy as np
from enum import Enum, auto
from app.hardware.camera import camera
from app.handshake_interface.pi_io import PiCapturerIOInterface
from app.service.qr_code_reader import decode_qr_code
from app.service.quality_control import compute_qc_metrics, check_quality

def encode_to_jpeg(frame: np.ndarray, quality: int = 92) -> bytes:
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    success, encoded_image = cv2.imencode(".jpg", frame, encode_params)

    if not success:
        print("JPEG encoding failed!")
        raise RuntimeError("Failed to encode frame to JPEG!")

    jpeg_bytes = encoded_image.tobytes()
    
    return jpeg_bytes

class PiState(Enum):
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
    def __init__(self, test_mode: bool = False):
        self.camera = camera
        self.io = PiCapturerIOInterface
        self.current_state = PiState.WAITING_FOR_PART
        self.current_part = {
            "part_id": None,
            "part_type": None,
            "view_index": -1,
            "sharpness": 0,
            "brightness": 0,
            "contrast": 0,
            "captured_at": None
        }
        self.inspection_event = 0
        self.max_qr_tries = 3
        self.max_capture_tries = 5
        
        self._reset_sent = False
        
        self.function_handler = {
            PiState.WAITING_FOR_PART: self._handle_waiting_for_part,
            PiState.SCANNING_QR_CODE: self._handle_scanning_for_qr_code,
            PiState.SENDING_RECIPE: self._handle_sending_recipe,
            PiState.WAITING_FOR_RECIPE_CONFIRMATION: self._handle_waiting_for_recipe_confirmation,
            PiState.WAITING_FOR_ROBOT_POSE: self._handle_waiting_for_robot_pose,
            PiState.CAPTURING_OBJECT_VIEW: self._handle_capturing_object_view,
            PiState.WAITING_FOR_CAPTURE_ACK: self._handle_waiting_for_capture_ack, 
            PiState.DONE: self._handle_done,
            PiState.ERROR: self._handle_error,
        }
        
        self.test_mode = test_mode
        
    def init_pi_capturer_system(self):
        self.camera.init_camera()
        print(f"System started! Current state is {self.current_state}")
        
    def _start_new_inspection(self, part_id: str, part_type: str):
        self.inspection_event += 1
        
        self.current_part.update({
            "part_id": part_id,
            "part_type": part_type 
        })
        
        print(f"Started new inspection for part {self.current_part.get('part_id', 'N/A')}!")
        
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
            
    def run_test_mode(self, runtime_config: object) -> PiState:
        self.init_pi_capturer_system()
        self._reset_current_part()
         
        test_part_id = runtime_config["part_id"]
        test_part_type = runtime_config["part_type"]
        test_view_index = runtime_config["view_index"]
        
        self._start_new_inspection(test_part_id, test_part_type)
        
        self.current_part.update({"view_index": test_view_index})
        
        return self._handle_capturing_object_view()
          
    def automate_sequence(self):
        print("Automating PSM sequence...")
        
        if self.test_mode:
            return self.run_test_mode()
        
        while True:
            self.step_once()
                 
    def check_robot_health(self):
        if not self.io.report_connection_alive_status():
            print("❌ No heartbeat from Fanuc!")
            return PiState.ERROR
        return
    
    def _reset_current_part(self):
        self.current_part = {
            "part_id": None,
            "part_type": None,
            "view_index": 0,
            "sharpness": 0,
            "brightness": 0,
            "contrast": 0,
            "captured_at": None
        }
              
    def _handle_waiting_for_part(self):
        print("Waiting for new part to arrive")
        
        if self.io.is_fanuc_in_position_for_capture():
            print("Part detected - Fanuc is in position for scanning QR code!")
            return PiState.SCANNING_QR_CODE
        
        time.sleep(0.02)
        return 
    
    def _handle_scanning_for_qr_code(self):
        print("Sanning for QR code!")
        
        qr_retry_count = 0
        qr_code_data = None
        
        while not qr_code_data and qr_retry_count <= self.max_qr_tries:
            frame, capture_time = self.camera.capture_frame()
            # qr_code_data, bbox = decode_qr_code(frame, simulated_result={"part_id": "SIM_001","part_type": "A_001_PLATE"})
            qr_code_data, bbox = decode_qr_code(frame)
            
            if qr_code_data:
                print(f"QR Code Detected: {qr_code_data}")
                break
            
            qr_retry_count += 1
            print(f"❌ QR code not detected. Retry {qr_retry_count}/{self.max_qr_tries}...")
            time.sleep(0.1)
        
        if not qr_code_data:
            print(f"❌ Failed to read QR code after {self.max_qr_tries} times!")
            return PiState.ERROR
        
        part_id = qr_code_data["part_id"]
        part_type = qr_code_data["part_type"]
        
        self._start_new_inspection(part_id, part_type)
        
        return PiState.SENDING_RECIPE
    
    def _handle_sending_recipe(self):
        part_type = self.current_part["part_type"]
        
        print(f"Sending part type recipe for {part_type} to Fanuc!")
        
        success = self.io.send_required_recipe(part_type)
        
        if not success:
            print("❌ Could not send recipe to Fanuc!")
            return PiState.ERROR
        
        print("Waiting for robot to move to capture pose…")
        return PiState.WAITING_FOR_RECIPE_CONFIRMATION
    
    def _handle_waiting_for_recipe_confirmation(self):
        if self.io.is_robot_ack():
            print("Robot confirmed recipe!")
            return PiState.WAITING_FOR_ROBOT_POSE
        return None
    
    def _handle_waiting_for_robot_pose(self) -> PiState | None:
        print("Checking pose and sequence status...")

        if self.io.is_every_part_view_captured():
            print("✅ Part sequence done. All views captured!")
            time.sleep(0.1)
            return PiState.DONE

        if not self.io.is_fanuc_in_position_for_capture():
            time.sleep(0.05)
            return 

        print("Requesting capture view!")
        return PiState.CAPTURING_OBJECT_VIEW
    
    
    def _handle_capturing_object_view(self) -> PiState:
        print("Capturing image!")
        
        num_try = 0
        qc_pass = False

        while num_try < self.max_capture_tries and not qc_pass:
            frame, captured_time = self.camera.capture_frame()
            
            # frame_metrics = compute_qc_metrics(frame, simulated_result={"sharpness": 110, "brightness": 70, "contrast": 30})
            frame_metrics = compute_qc_metrics(frame)
            qc_pass = check_quality(frame_metrics)
            
            if qc_pass:
                print(f"View #{self.current_part.get('view_index', 'N/A')} passed QC!")
                break
            
            num_try += 1
            print(f"❌ Image did not pass at qc check. Retry {num_try}/{self.max_capture_tries}...")
            time.sleep(0.05)
            
        if not qc_pass:
            print("Max retries reached for this view. Going to ERROR!")
            self.io.send_error_signal()
            return PiState.ERROR
        
        current_view_index = self.current_part["view_index"]
                
        self.current_part.update({
            "view_index": current_view_index + 1, 
            "qc_sharpness": frame_metrics["sharpness"],
            "qc_brightness": frame_metrics["brightness"],
            "qc_contrast": frame_metrics["contrast"],
            "captured_at": captured_time 
        })
        
        jpeg_frame = encode_to_jpeg(frame)
        
        # dispatch_to_jetson(jpeg_frame, self.current_part)
        
        if self.test_mode:
            return PiState.DONE

        self.io.set_capture_done(True)
        return PiState.WAITING_FOR_CAPTURE_ACK
    
    
    def _handle_done(self) -> PiState:
        print(f"Part {self.current_part.get('id')} fully processed!")
        
        self._reset_current_part()

        self.io.set_capture_done(False)
        
        self.io.send_reset_signal()
        # self._reset_sent = True
        
        return PiState.WAITING_FOR_PART
    
    def _handle_waiting_for_capture_ack(self) -> PiState | None:
        if self.io.is_robot_ack():
            print("Robot acknowledged CAPTURE_DONE, waiting for next pose…")
            
            self.io.set_capture_done(False)
            return PiState.WAITING_FOR_ROBOT_POSE
        return None
    
    def _handle_error(self) -> None | PiState:
        print("ERROR: Staying in error for now!")
        
        self.io.send_error_signal()
        time.sleep(0.5)
        exit(1)
    
    def handle_reset_state(self):
        return PiState.WAITING_FOR_PART
    
PiOrchestrator = PiStateMachine()