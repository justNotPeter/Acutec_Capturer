# Pi <-> Robot GPIO Handoff

## Scope

This document explains the Raspberry Pi <-> Fanuc robot GPIO communication used in `Acutec_Capturer`.

Primary references:
- `app/config/digital_io.py`
- `app/config/gpio_setup.py`
- `app/handshake_interface/pi_io.py`
- `app/handshake_interface/fanuc_io.py`
- `app/state_machine/pi_state_machine.py`
- `app/state_machine/robodk_fanuc_state_machine.py`

## GPIO Mapping

### Pi inputs from robot

| Signal | BCM Pin | Direction at Pi | Purpose |
| --- | ---: | --- | --- |
| `HEARTBEAT` | 11 | Input | Robot alive / health signal |
| `ROBOT_IN_POSITION_FOR_CAPTURE` | 12 | Input | Robot is at QR or image capture pose |
| `PART_SEQUENCE_DONE` | 13 | Input | Robot says all views for current part are complete |
| `ACKNOWLEDGEMENT` | 14 | Input | Robot acknowledges recipe receipt or capture completion |

### Pi outputs to robot

| Signal | BCM Pin | Direction at Pi | Purpose |
| --- | ---: | --- | --- |
| `CAPTURE_DONE` | 22 | Output | Pi says image capture for current view is complete |
| `ERROR_SIGNAL` | 23 | Output | Pi pulses error to robot |
| `RESET_SIGNAL` | 24 | Output | Pi requests robot to reset sequence |
| `RECIPE_BIT_2` | 25 | Output | Recipe code bit 2 |
| `RECIPE_BIT_1` | 26 | Output | Recipe code bit 1 |
| `RECIPE_BIT_0` | 27 | Output | Recipe code bit 0 |

### Conveyor input used by robot side

| Signal | BCM Pin | Direction at Robot Logic | Purpose |
| --- | ---: | --- | --- |
| `PD_CONVEYOR_STOPPED` | 10 | Input | Conveyor stopped with part present |

## GPIO Initialization

GPIO setup happens in `app/config/gpio_setup.py`.

- GPIO mode is `BCM`.
- All robot-to-Pi lines are configured as inputs with `GPIO.PUD_DOWN`.
- All Pi-to-robot lines are configured as outputs.

Configured Pi inputs:
- `HEARTBEAT`
- `ROBOT_IN_POSITION_FOR_CAPTURE`
- `ACKNOWLEDGEMENT`
- `PART_SEQUENCE_DONE`

Configured Pi outputs:
- `RESET_SIGNAL`
- `CAPTURE_DONE`
- `ERROR_SIGNAL`
- `RECIPE_BIT_2`
- `RECIPE_BIT_1`
- `RECIPE_BIT_0`

## Files That Touch GPIO

### Configuration

- `app/config/digital_io.py`
  Defines logical signal names and BCM pin numbers.

- `app/config/gpio_setup.py`
  Initializes GPIO direction and pull-down configuration.

### Pi-side GPIO logic

- `app/handshake_interface/pi_io.py`
  Pi writes `CAPTURE_DONE`, `RESET_SIGNAL`, `ERROR_SIGNAL`, and recipe bits.
  Pi reads `HEARTBEAT`, `ACKNOWLEDGEMENT`, `ROBOT_IN_POSITION_FOR_CAPTURE`, and `PART_SEQUENCE_DONE`.

### Robot-side GPIO logic

- `app/handshake_interface/fanuc_io.py`
  Robot writes `ROBOT_IN_POSITION_FOR_CAPTURE`, `PART_SEQUENCE_DONE`, and `ACKNOWLEDGEMENT`.
  Robot reads `CAPTURE_DONE`, `RESET_SIGNAL`, and recipe bits.

- `app/state_machine/robodk_fanuc_state_machine.py`
  Sets `HEARTBEAT` high on startup and uses the GPIO handshake during robot motion flow.

### Simulation support

- `app/external/dummy_gpio.py`
  Simulation GPIO backend.

- `app/simulation/fanuc_to_psm_v2.py`
  Full-cell simulation entrypoint with both Pi and robot state machines.

- `app/simulation/manual_fanuc_to_psm.py`
  Manual signal-toggling test harness. This file appears stale and does not match current interface names exactly.

## Signal Direction Summary

### Outputs (Pi -> Robot)

- `CAPTURE_DONE`
- `ERROR_SIGNAL`
- `RESET_SIGNAL`
- `RECIPE_BIT_2`
- `RECIPE_BIT_1`
- `RECIPE_BIT_0`

### Inputs (Robot -> Pi)

- `HEARTBEAT`
- `ROBOT_IN_POSITION_FOR_CAPTURE`
- `PART_SEQUENCE_DONE`
- `ACKNOWLEDGEMENT`

## Protocol Overview

The protocol is a level-based GPIO handshake between the Pi state machine and the robot state machine.

### High-level sequence

1. Robot boots and drives `HEARTBEAT=HIGH`.
2. Robot waits for part presence from `PD_CONVEYOR_STOPPED`.
3. Robot sets `ROBOT_IN_POSITION_FOR_CAPTURE=HIGH` to indicate QR/initial pose readiness.
4. Pi detects `ROBOT_IN_POSITION_FOR_CAPTURE`, captures a QR frame, and decodes part type.
5. Pi sends the recipe as a 3-bit code on `RECIPE_BIT_2:0`.
6. Robot reads the recipe bits and sets `ACKNOWLEDGEMENT=HIGH`.
7. Robot moves to a capture view, then sets `ROBOT_IN_POSITION_FOR_CAPTURE=HIGH`.
8. Pi detects the in-position signal and captures the image.
9. Pi runs QC and dispatches the image to Jetson.
10. Pi sets `CAPTURE_DONE=HIGH`.
11. Robot reads `CAPTURE_DONE`, clears `ROBOT_IN_POSITION_FOR_CAPTURE`, and sets `ACKNOWLEDGEMENT=HIGH`.
12. Robot either moves to the next view or sets `PART_SEQUENCE_DONE=HIGH`.
13. Pi sees `PART_SEQUENCE_DONE`, clears `CAPTURE_DONE`, and sends `RESET_SIGNAL=HIGH`.
14. Robot reads `RESET_SIGNAL` and resets its sequence state.

## Step-by-Step Execution Flow

### 1. Process start

The clearest runnable system entrypoint is `app/simulation/fanuc_to_psm_v2.py`.

It:
- forces simulation mode with `PI_SIM=1`
- initializes GPIO via `init_gpio_pins()`
- initializes the Pi camera system
- creates the robot simulator
- steps both state machines together

### 2. Pi startup behavior

Pi-side startup is in `PiStateMachine.init_pi_capturer_system()`.

It:
- opens the camera
- prints current state

Pi runtime loop is:
- `PiStateMachine.step_once()` for one cycle
- `PiStateMachine.automate_sequence()` for continuous operation

### 3. Robot startup behavior

Robot-side startup is in `RoboDKFanuc.__init__()`.

It:
- connects to RoboDK
- sets `HEARTBEAT` high immediately
- clears `ROBOT_IN_POSITION_FOR_CAPTURE`
- clears `PART_SEQUENCE_DONE`
- clears `ACKNOWLEDGEMENT`

### 4. When signals are sent to the robot

Pi sends signals in `app/handshake_interface/pi_io.py`.

- `send_required_recipe(part_type)`
  Sends recipe on pins `25`, `26`, `27`.

- `set_capture_done(high)`
  Sends capture completion on pin `22`.

- `send_reset_signal()`
  Sends reset on pin `24`.

- `send_error_signal()`
  Pulses error on pin `23`.

### 5. When signals are read from the robot

Pi reads robot signals in `app/handshake_interface/pi_io.py`.

- `report_connection_alive_status()`
  Reads `HEARTBEAT`.

- `is_robot_ack()`
  Reads `ACKNOWLEDGEMENT`.

- `is_fanuc_in_position_for_capture()`
  Reads `ROBOT_IN_POSITION_FOR_CAPTURE`.

- `is_every_part_view_captured()`
  Reads `PART_SEQUENCE_DONE`.

### 6. When signals are sent from robot to Pi

Robot sends signals in `app/handshake_interface/fanuc_io.py`.

- `set_in_position_for_capture(high)`
- `set_part_sequence_done(high)`
- `set_ack(high)`

Additionally, `HEARTBEAT` is driven directly in `RoboDKFanuc.__init__()`.

### 7. When signals are read from Pi by robot

Robot reads Pi signals in `app/handshake_interface/fanuc_io.py`.

- `read_capture_done()`
- `read_reset_signal()`
- `read_recipe_code()`

## Capture Trigger

Image capture is triggered in `PiStateMachine._handle_capturing_object_view()`.

Capture can only happen after the Pi sees:
- `ROBOT_IN_POSITION_FOR_CAPTURE == HIGH`
- `PART_SEQUENCE_DONE == LOW`

That gating logic is in `PiStateMachine._handle_waiting_for_robot_pose()`.

### Trigger type

Production flow:
- Triggered by robot signal.

Not used in the production state-machine flow:
- internal timer trigger

Available test path:
- manual/test trigger through `app/simulation/psm_to_jetson.py`

## Loops Based On Signal State

### Pi loops

- `automate_sequence()`
  Infinite control loop.

- `_handle_waiting_for_part()`
  Polls until robot reports in-position.

- `_handle_waiting_for_recipe_confirmation()`
  Polls until `ACKNOWLEDGEMENT` goes high.

- `_handle_waiting_for_robot_pose()`
  Polls until either `PART_SEQUENCE_DONE` or `ROBOT_IN_POSITION_FOR_CAPTURE`.

- `_handle_waiting_for_capture_ack()`
  Polls until `ACKNOWLEDGEMENT` goes high after capture.

- `_handle_scanning_for_qr_code()`
  Retries QR capture up to `max_qr_tries`.

- `_handle_capturing_object_view()`
  Retries capture/QC up to `max_capture_tries`.

### Robot loops

- `RoboDKFanuc.step_once()`
  Repeatedly checks reset and advances robot state.

- `_handle_waiting_for_part()`
  Polls until `PD_CONVEYOR_STOPPED` indicates part present.

- `_handle_waiting_for_recipe()`
  Polls recipe bits until they decode to a known part type.

- `_handle_in_capturing_pose()`
  Polls `CAPTURE_DONE` until Pi says capture completed.

## Logging And Print Statements

### Waiting for robot

- `Waiting for robot to move to capture pose…`
- `Checking pose and sequence status...`
- `[ROBO_SIM] Waiting for conveyor/sensor to signal PART_PRESENT`

### Robot ready

- `Robot confirmed recipe!`
- `[ROBO_SIM] Reached capture pose for view #...`
- `[ROBO_SIM] Part detected & conveyor stopped. Setting in_position=HIGH.`

### Sending signal

- `SEND CAPTURE_DONE: HIGH`
- `SEND CAPTURE_DONE: LOW`
- `Sent recipe code ...`
- `RESET signal sent!`
- `ERROR signal sent!`

### Capture triggered

- `Requesting capture view!`
- `Capturing image!`
- `View #... passed QC!`

### Process complete

- `✅ Part sequence done. All views captured!`
- `[ROBO_SIM] All views captured. PART_SEQUENCE_DONE=HIGH (latched).`
- `Part ... fully processed!`

## Error Handling

### Present

- Heartbeat missing:
  `PiStateMachine.check_robot_health()` sends Pi to `ERROR` when `HEARTBEAT` is low.

- QR read failure:
  bounded retry count, then `ERROR`.

- QC failure:
  bounded retry count, then `ERROR_SIGNAL` pulse and `ERROR`.

- GPIO read/write exceptions:
  most interfaces log the exception and return a safe default.

- Camera open/capture failure:
  raises `RuntimeError`.

### Not present

No explicit timeout handling was found for:
- waiting for recipe acknowledgement
- waiting for capture acknowledgement
- waiting for robot in-position
- waiting for part-sequence-done

No explicit validation was found for:
- impossible or contradictory GPIO combinations
- stale acknowledgements
- pulse width / edge timing requirements

The current behavior in these cases is mostly indefinite polling.

## Known Code Gaps

These are worth fixing before depending on the flow as-is:

1. `PiStateMachine._handle_waiting_for_robot_pose()` calls `is_every_part_view_capured()`, but the interface defines `is_every_part_view_captured()`.

2. `PiStateMachine._handle_capturing_object_view()` calls `dispatch_to_jetson(...)`, but `dispatch_to_jetson` is not imported in that file.

3. `app/simulation/manual_fanuc_to_psm.py` appears out of sync with current module names and method names.

4. `app/main.py` is not the actual orchestrator; it only moves the RoboDK robot once.

## Onboarding Summary

Think of the system as two cooperating state machines:

- The Pi owns inspection.
  It reads QR, decides the recipe, captures images, checks image quality, forwards images to Jetson, and tells the robot when each capture is done.

- The robot owns motion.
  It reports health, exposes when it is at a valid pose, acknowledges commands from the Pi, advances through capture views, and declares when the full sequence is done.

The handshake is simple:

- Robot says: "I am alive."
- Robot says: "I have a part / I am in position."
- Pi says: "Use this recipe."
- Robot says: "Recipe received."
- Robot says: "I am at capture pose."
- Pi says: "Capture done."
- Robot says: "Ack, moving to next view."
- Robot eventually says: "Sequence done."
- Pi says: "Reset for next part."

That is the core Pi <-> Robot communication contract in this repo.
