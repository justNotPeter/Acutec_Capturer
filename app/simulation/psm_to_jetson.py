"""
CLI tool to:
- trigger a single capture via PiStateMachine test mode
- send JPEG bytes + metadata to Jetson API

Usage:
python -m simulation.psm_to_jetson \
  --part-id SIM_001 \
  --part-type A_005_CAST_PLT \
  --view-index 0 \
"""

import argparse
import sys

from app.state_machine.pi_state_machine import PiOrchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PSM → Jetson test capture CLI")

    parser.add_argument("--part_id", required=True, help="Unique part ID")
    parser.add_argument("--part_type", required=True, help="Part type name")
    parser.add_argument("--view_index", type=int, default=0, help="View index to capture")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    runtime_config = {
        "part_id": args.part_id,
        "part_type": args.part_type,
        "view_index": args.view_index,
    }

    print("Begin testing from PSM to Jetson!")
    try:
        result = PiOrchestrator.run_test_mode(runtime_config)
        print(result)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()