import curses
import io
import time
from collections import deque
from contextlib import redirect_stdout

from app.config.digital_io import (
    DIGITAL_OUTPUTS_FROM_FANUC_TO_PI,
    DIGITAL_OUTPUTS_FROM_PI_TO_FANUC,
)
from app.config.gpio_setup import GPIO, cleanup_gpio, init_gpio_pins
from app.state_machine.pi_state_machine import PiOrchestrator


STEP_INTERVAL_SECONDS = 0.05
LOG_BUFFER_SIZE = 16


def pin_level(pin: int) -> str:
    try:
        return "HIGH" if GPIO.input(pin) == GPIO.HIGH else "LOW"
    except Exception as exc:
        return f"ERR ({exc})"


def collect_step_logs(log_buffer: deque[str]) -> None:
    capture = io.StringIO()

    with redirect_stdout(capture):
        PiOrchestrator.step_once()

    for line in capture.getvalue().splitlines():
        if line.strip():
            log_buffer.append(line.rstrip())


def draw_section(stdscr, start_row: int, title: str, items: list[str]) -> int:
    stdscr.addstr(start_row, 0, title, curses.A_BOLD)

    row = start_row + 1
    for item in items:
        stdscr.addstr(row, 2, item)
        row += 1

    return row + 1


def draw_screen(stdscr, log_buffer: deque[str]) -> None:
    stdscr.erase()

    header = "Acutec Pi State Machine!"
    stdscr.addstr(0, 0, header, curses.A_REVERSE)

    state = getattr(PiOrchestrator.current_state, "name", str(PiOrchestrator.current_state))
    current_part = PiOrchestrator.current_part

    row = 2
    row = draw_section(
        stdscr,
        row,
        "State",
        [
            f"Current State : {state}",
            f"Part ID       : {current_part.get('part_id')}",
            f"Part Type     : {current_part.get('part_type')}",
            f"View Index    : {current_part.get('view_index')}",
            f"Captured UTC  : {current_part.get('captured_time_utc')}",
        ],
    )

    fanuc_inputs = [
        f"{name:<30} BCM {pin:<2}  {pin_level(pin)}"
        for name, pin in DIGITAL_OUTPUTS_FROM_FANUC_TO_PI.items()
    ]
    row = draw_section(stdscr, row, "Robot -> Pi Inputs", fanuc_inputs)

    pi_outputs = [
        f"{name:<30} BCM {pin:<2}  {pin_level(pin)}"
        for name, pin in DIGITAL_OUTPUTS_FROM_PI_TO_FANUC.items()
    ]
    row = draw_section(stdscr, row, "Pi -> Robot Outputs", pi_outputs)

    stdscr.addstr(row, 0, "Recent Logs", curses.A_BOLD)
    row += 1

    max_y, max_x = stdscr.getmaxyx()
    available_rows = max_y - row - 1
    visible_logs = list(log_buffer)[-max(available_rows, 0):]

    for line in visible_logs:
        stdscr.addstr(row, 2, line[: max_x - 4])
        row += 1
        if row >= max_y - 1:
            break

    stdscr.refresh()


def main(stdscr) -> int:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(1)

    log_buffer: deque[str] = deque(maxlen=LOG_BUFFER_SIZE)

    init_gpio_pins()
    log_buffer.append("GPIO initialized.")

    PiOrchestrator.init_pi_capturer_system()
    log_buffer.append("Pi capturer system initialized.")

    try:
        while True:
            char = stdscr.getch()
            if char == ord("q"):
                break

            collect_step_logs(log_buffer)
            draw_screen(stdscr, log_buffer)
            time.sleep(STEP_INTERVAL_SECONDS)

    finally:
        try:
            PiOrchestrator.camera.release()
        except Exception:
            pass
        cleanup_gpio()

    return 0


if __name__ == "__main__":
    raise SystemExit(curses.wrapper(main))
