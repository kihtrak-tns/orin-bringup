#!/usr/bin/env python3
"""A1b: DriveCommand loopback test -- run with the main battery UNPLUGGED.

Purpose (orin_bringup_plan.md, Phase A, task A1b): prove the DriveCommand
format is compatible end-to-end, by publishing a small known command and
confirming the ESP32 echoes the same values back in VehicleState, *before*
anything is allowed to command the real vehicle.

Why battery-unplugged is safe for this test: the VESC and the steering servo
motor both draw their actuation power from the main pack, not from USB/ESP32
logic power (see Phase B of the plan, which treats "power-up steering" as a
separate actuator event to test only once powered, on a stand, wheels clear).
With the battery unplugged, the ESP32 still runs off USB, still parses
DriveCommand messages and still updates its internal state/echo fields --
but the VESC and servo cannot physically move. That is exactly what this
test needs and nothing more.

This script will REFUSE to run unless you pass --confirm-battery-unplugged
AND type the exact confirmation phrase when prompted (skippable only with
--yes-i-am-sure, for non-interactive/scripted use -- use that flag
deliberately, not as a way to bypass reading this).

What it does:
  1. Publishes DriveCommand(speed_mps=0.0, steering_angle_rad=TEST_STEER_RAD,
     brake=False) continuously at 10 Hz for a bounded duration (the ESP32's
     500 ms drive-command timeout means an unwanted brake+center happens
     automatically if we ever stop -- that's a feature, not a risk here).
     speed_mps=0.0 sidesteps the unmeasured speed/ERPM scale factor entirely:
     0 in should be 0 out regardless of that factor, so an exact match here
     really does prove the format, not just the zero case.
  2. Confirms /laksa/state (VehicleState) echoes steering_target_rad within
     tolerance and vesc.requested_erpm == 0, vesc.command_fresh == True,
     vesc.brake_active == False.
  3. Publishes DriveCommand(speed_mps=0.0, steering_angle_rad=0.0, brake=True)
     for a bounded duration and confirms vesc.brake_active == True.
  4. Stops publishing and confirms the ESP32's own 500 ms timeout brake
     engages on its own (vesc.command_fresh goes False, brake_active stays/
     becomes True) -- a first, cheap look at Phase C's stop-behaviour test.

Exit status: 0 only if every step passes. This script is the ONLY command
publisher it starts; it does not launch or rely on any other node that could
also be publishing to /laksa/command.
"""
from __future__ import annotations

import argparse
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy

from laksa_interfaces.msg import DriveCommand, VehicleState

COMMAND_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.RELIABLE,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
    durability=QoSDurabilityPolicy.VOLATILE,
)
STATE_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
    durability=QoSDurabilityPolicy.VOLATILE,
)

TEST_STEER_RAD = 0.10  # ~5.7 deg; well inside the 63-139 deg (~+-37 deg) limit
STEER_TOLERANCE_RAD = 0.02
PUBLISH_RATE_HZ = 10.0
HOLD_DURATION_S = 2.0
CONFIRM_PHRASE = "battery is unplugged"


def gate_or_exit(args) -> None:
    if not args.confirm_battery_unplugged:
        print(
            "Refusing to run: pass --confirm-battery-unplugged to acknowledge "
            "this test must only be run with the main battery physically "
            "disconnected (see docstring).",
            file=sys.stderr,
        )
        sys.exit(2)

    if args.yes_i_am_sure:
        return

    print(
        "Safety gate: this test publishes DriveCommand messages. It must "
        "only run with the main battery unplugged (VESC and servo unpowered).\n"
        f'Type exactly "{CONFIRM_PHRASE}" to continue, anything else aborts.'
    )
    try:
        typed = input("> ").strip()
    except EOFError:
        typed = ""
    if typed != CONFIRM_PHRASE:
        print("Confirmation not received -- aborting.", file=sys.stderr)
        sys.exit(2)


class LoopbackTestNode(Node):
    def __init__(self):
        super().__init__("laksa_drive_command_loopback_test")
        self.pub = self.create_publisher(DriveCommand, "/laksa/command", COMMAND_QOS)
        self.latest_state: VehicleState | None = None
        self.create_subscription(VehicleState, "/laksa/state", self._on_state, STATE_QOS)

    def _on_state(self, msg: VehicleState) -> None:
        self.latest_state = msg

    def publish_for(self, cmd: DriveCommand, duration_s: float) -> None:
        period = 1.0 / PUBLISH_RATE_HZ
        deadline = time.monotonic() + duration_s
        while rclpy.ok() and time.monotonic() < deadline:
            self.pub.publish(cmd)
            rclpy.spin_once(self, timeout_sec=period)

    def stop_publishing_and_wait(self, wait_s: float) -> None:
        deadline = time.monotonic() + wait_s
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)


def check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    line = f"[{mark}] {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    return ok


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-battery-unplugged", action="store_true")
    parser.add_argument(
        "--yes-i-am-sure",
        action="store_true",
        help="skip the interactive typed confirmation (non-interactive use only)",
    )
    args = parser.parse_args(argv)
    gate_or_exit(args)

    rclpy.init()
    node = LoopbackTestNode()
    all_ok = True
    try:
        print(f"Publishing steering test command for {HOLD_DURATION_S}s "
              f"(speed_mps=0.0, steering_angle_rad={TEST_STEER_RAD}, brake=False)...")
        cmd = DriveCommand()
        cmd.speed_mps = 0.0
        cmd.steering_angle_rad = TEST_STEER_RAD
        cmd.brake = False
        node.publish_for(cmd, HOLD_DURATION_S)

        state = node.latest_state
        if state is None:
            print("No /laksa/state received -- is the ESP32 connected and the "
                  "agent running?", file=sys.stderr)
            return 2

        all_ok &= check(
            "steering_target_rad echoed",
            abs(state.steering_target_rad - TEST_STEER_RAD) <= STEER_TOLERANCE_RAD,
            f"got {state.steering_target_rad:.4f}, expected {TEST_STEER_RAD:.4f} "
            f"+/- {STEER_TOLERANCE_RAD}",
        )
        all_ok &= check(
            "vesc.requested_erpm == 0 (speed_mps=0.0 sidesteps the unmeasured scale factor)",
            state.vesc.requested_erpm == 0,
            f"got {state.vesc.requested_erpm}",
        )
        all_ok &= check("vesc.command_fresh == True", bool(state.vesc.command_fresh))
        all_ok &= check("vesc.brake_active == False", not state.vesc.brake_active)

        print(f"\nPublishing brake command for {HOLD_DURATION_S}s "
              f"(speed_mps=0.0, steering_angle_rad=0.0, brake=True)...")
        brake_cmd = DriveCommand()
        brake_cmd.speed_mps = 0.0
        brake_cmd.steering_angle_rad = 0.0
        brake_cmd.brake = True
        node.publish_for(brake_cmd, HOLD_DURATION_S)

        state = node.latest_state
        all_ok &= check("vesc.brake_active == True", bool(state.vesc.brake_active))

        print("\nStopping publishing; watching for the ESP32's own 500 ms "
              "drive-command timeout to engage on its own...")
        node.stop_publishing_and_wait(1.0)
        state = node.latest_state
        all_ok &= check(
            "vesc.command_fresh == False after silence (firmware timeout observed)",
            not bool(state.vesc.command_fresh) if state is not None else False,
        )

    finally:
        node.destroy_node()
        rclpy.shutdown()

    print()
    if all_ok:
        print("Values echoed exactly -> DriveCommand format proven end-to-end.")
        return 0
    print("One or more checks FAILED. Do not proceed to Phase B/C. Compare "
          "against esp32_installed_firmware_findings.md.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
