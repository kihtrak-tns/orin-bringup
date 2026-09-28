#!/usr/bin/env python3
"""A1a: listen-only layout check for Pca9685State, VescState, VehicleState.

Purpose (see orin_bringup_plan.md, Phase A, task A1a): prove that the
laksa_interfaces message definitions in this workspace exactly match the
layout the flashed ESP32 firmware (build cba74e7-dirty) actually publishes,
*before* any command publisher is allowed to exist on this system. This node
never publishes to the vehicle -- it only subscribes.

It checks two independent things and requires BOTH to pass:

1. Sanity check on decoded values: fields that should hold known constants
   right now (I2C address 0x40, PWM frequency 50 Hz, steering channel 7,
   fault_code 0) actually do, using rclpy's normal typed deserialization.

   VESC controller_id == 83 and telemetry_fresh can only hold once the VESC
   is powered from the main battery and has answered the ESP32 over UART.
   Phase A runs with the battery unplugged, so by default those two are
   reported as [INFO] and do not affect the exit status; pass --vesc-powered
   (Phase B, task B3) to make them hard checks again.

2. Raw-byte cross-check: for the same topics, an independent CDR decoder
   (_cdr.py), built from the message field order without going through
   rclpy's deserializer, is run against the raw wire bytes of all three
   topics (VehicleState including its nested VescState). Its output is
   compared field-by-field against what rclpy decoded. rclpy will "succeed"
   even if laksa_interfaces doesn't match the firmware's real layout --
   Humble does not check type hashes across the wire -- so a raw decode that
   agrees with rclpy is real evidence the layout is right, not an assumption.

Exit status: 0 only if every non-[INFO] check across both methods passes
("ALL MATCH"). The raw==typed checks are never informational.
Any mismatch must be resolved by comparing against firmware evidence
(esp32_installed_firmware_findings.md) -- never by patching this script's
expected values until it goes green.

Usage:
    ros2 run laksa_bringup laksa_readonly_check
    ros2 run laksa_bringup laksa_readonly_check --timeout 15
    ros2 run laksa_bringup laksa_readonly_check --vesc-powered   # B3 only
"""
from __future__ import annotations

import argparse
import functools
import sys
import threading
import time
from dataclasses import dataclass, field

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy

from laksa_interfaces.msg import Pca9685State, VehicleState, VescState

from ._cdr import CDRReader

QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
    durability=QoSDurabilityPolicy.VOLATILE,
)

# Known-good constants from esp32_installed_firmware_findings.md (26 Sep 2026).
EXPECTED_I2C_ADDRESS = 0x40
EXPECTED_PWM_FREQUENCY_HZ = 50
EXPECTED_STEERING_CHANNEL = 7
EXPECTED_VESC_CONTROLLER_ID = 83
EXPECTED_VESC_FAULT_CODE = 0


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    # Reported but not counted toward the exit status (e.g. VESC-powered-only
    # checks while the main battery is unplugged).
    informational: bool = False


@dataclass
class TopicState:
    """Tracks the most recent typed message and matching raw payload."""

    typed_msg: object = None
    raw_bytes: bytes = None
    lock: threading.Lock = field(default_factory=threading.Lock)


def decode_vesc_state_raw(data: bytes) -> dict:
    return _read_vesc_state(CDRReader(data))


def _read_vesc_state(r: CDRReader) -> dict:
    out = {}
    out["stamp"] = r.read_time()
    out["command_fresh"] = r.read_bool()
    out["direction_change_pending"] = r.read_bool()
    out["brake_active"] = r.read_bool()
    out["telemetry_fresh"] = r.read_bool()
    out["telemetry_sequence"] = r.read_u32()
    out["telemetry_age_ms"] = r.read_u32()
    out["requested_erpm"] = r.read_i32()
    out["active_erpm"] = r.read_i32()
    out["measured_erpm"] = r.read_f32()
    out["motor_current_a"] = r.read_f32()
    out["input_current_a"] = r.read_f32()
    out["duty_cycle"] = r.read_f32()
    out["input_voltage_v"] = r.read_f32()
    out["amp_hours"] = r.read_f32()
    out["amp_hours_charged"] = r.read_f32()
    out["watt_hours"] = r.read_f32()
    out["watt_hours_charged"] = r.read_f32()
    out["temp_mosfet_c"] = r.read_f32()
    out["temp_motor_c"] = r.read_f32()
    out["pid_position"] = r.read_f32()
    out["tachometer"] = r.read_i32()
    out["tachometer_abs"] = r.read_i32()
    out["controller_id"] = r.read_u8()
    out["fault_code"] = r.read_u8()
    out["motor_angular_velocity_rad_s"] = r.read_f32()
    out["wheel_angular_velocity_rad_s"] = r.read_f32()
    out["vehicle_linear_velocity_mps"] = r.read_f32()
    return out


def decode_pca9685_state_raw(data: bytes) -> dict:
    r = CDRReader(data)
    out = {}
    out["stamp"] = r.read_time()
    out["initialized"] = r.read_bool()
    out["responsive"] = r.read_bool()
    out["configuration_matches"] = r.read_bool()
    out["i2c_address"] = r.read_u8()
    out["configured_pwm_frequency_hz"] = r.read_u16()
    out["mode1"] = r.read_u8()
    out["prescale"] = r.read_u8()
    out["last_successful_write_age_sec"] = r.read_f32()
    out["last_successful_read_age_sec"] = r.read_f32()
    out["consecutive_i2c_errors"] = r.read_u32()
    out["total_i2c_errors"] = r.read_u32()
    out["last_i2c_error_code"] = r.read_i32()
    out["reinitialization_count"] = r.read_u32()
    out["automatic_recovery_enabled"] = r.read_bool()
    out["steering_pwm_channel"] = r.read_u8()
    out["steering_command_deg"] = r.read_u8()
    out["steering_pulse_us"] = r.read_u16()
    out["steering_off_tick"] = r.read_u16()
    return out


def _read_vector3(r: CDRReader) -> dict:
    return {"x": r.read_f64(), "y": r.read_f64(), "z": r.read_f64()}


def decode_vehicle_state_raw(data: bytes) -> dict:
    """Flattened to dotted keys (e.g. "orientation.w", "vesc.controller_id")."""
    r = CDRReader(data)
    out = {}
    out["stamp"] = r.read_time()
    out["imu_available"] = r.read_bool()
    for k in ("x", "y", "z", "w"):
        out[f"orientation.{k}"] = r.read_f64()
    out["orientation_accuracy_rad"] = r.read_f32()
    for vec in ("angular_velocity_rad_s", "linear_acceleration_m_s2", "magnetic_field_t"):
        for k, v in _read_vector3(r).items():
            out[f"{vec}.{k}"] = v
    for k, v in _read_vesc_state(r).items():
        if k != "stamp":
            out[f"vesc.{k}"] = v
    out["steering_target_rad"] = r.read_f32()
    out["steering_current_rad"] = r.read_f32()
    out["steering_endpoint_relief_active"] = r.read_bool()
    return out


def _getattr_path(obj, dotted: str):
    return functools.reduce(getattr, dotted.split("."), obj)


def compare(name: str, raw: dict, typed_getter, tolerance: float = 1e-4) -> list[CheckResult]:
    results = []
    for key, raw_val in raw.items():
        if key == "stamp":
            continue  # stamps are compared implicitly via message pairing
        typed_val = typed_getter(key)
        if isinstance(raw_val, float):
            ok = abs(raw_val - typed_val) <= tolerance
        else:
            ok = raw_val == typed_val
        results.append(
            CheckResult(
                name=f"{name}.{key} raw==typed",
                passed=ok,
                detail=f"raw={raw_val!r} typed={typed_val!r}",
            )
        )
    return results


class ReadonlyCheckNode(Node):
    def __init__(self, timeout_s: float, vesc_powered: bool = False):
        super().__init__("laksa_readonly_check")
        self.timeout_s = timeout_s
        self.vesc_powered = vesc_powered
        self.pca_state = TopicState()
        self.vesc_state = TopicState()
        self.vehicle_state = TopicState()

        # Typed subscriptions (normal rclpy deserialization).
        self.create_subscription(
            Pca9685State, "/laksa/pca9685/state", self._on_pca_typed, QOS
        )
        self.create_subscription(VescState, "/laksa/vesc/state", self._on_vesc_typed, QOS)
        self.create_subscription(
            VehicleState, "/laksa/state", self._on_vehicle_typed, QOS
        )

        # Raw subscriptions (independent CDR decode). rclpy supports raw=True
        # since Foxy; it hands back the exact bytes off the wire.
        self.create_subscription(
            Pca9685State, "/laksa/pca9685/state", self._on_pca_raw, QOS, raw=True
        )
        self.create_subscription(
            VescState, "/laksa/vesc/state", self._on_vesc_raw, QOS, raw=True
        )
        self.create_subscription(
            VehicleState, "/laksa/state", self._on_vehicle_raw, QOS, raw=True
        )

    def _on_pca_typed(self, msg):
        with self.pca_state.lock:
            self.pca_state.typed_msg = msg

    def _on_pca_raw(self, data: bytes):
        with self.pca_state.lock:
            self.pca_state.raw_bytes = data

    def _on_vesc_typed(self, msg):
        with self.vesc_state.lock:
            self.vesc_state.typed_msg = msg

    def _on_vesc_raw(self, data: bytes):
        with self.vesc_state.lock:
            self.vesc_state.raw_bytes = data

    def _on_vehicle_typed(self, msg):
        with self.vehicle_state.lock:
            self.vehicle_state.typed_msg = msg

    def _on_vehicle_raw(self, data: bytes):
        with self.vehicle_state.lock:
            self.vehicle_state.raw_bytes = data

    def have_all_topics(self) -> bool:
        return (
            self.pca_state.typed_msg is not None
            and self.pca_state.raw_bytes is not None
            and self.vesc_state.typed_msg is not None
            and self.vesc_state.raw_bytes is not None
            and self.vehicle_state.typed_msg is not None
            and self.vehicle_state.raw_bytes is not None
        )

    def run_checks(self) -> list[CheckResult]:
        results: list[CheckResult] = []

        # --- Sanity checks against known-good constants ---
        pca = self.pca_state.typed_msg
        vesc = self.vesc_state.typed_msg
        veh = self.vehicle_state.typed_msg

        results.append(CheckResult("pca9685.initialized", bool(pca.initialized)))
        results.append(CheckResult("pca9685.responsive", bool(pca.responsive)))
        results.append(
            CheckResult(
                "pca9685.i2c_address == 0x40",
                pca.i2c_address == EXPECTED_I2C_ADDRESS,
                f"got 0x{pca.i2c_address:02x}",
            )
        )
        results.append(
            CheckResult(
                "pca9685.configured_pwm_frequency_hz == 50",
                pca.configured_pwm_frequency_hz == EXPECTED_PWM_FREQUENCY_HZ,
                f"got {pca.configured_pwm_frequency_hz}",
            )
        )
        results.append(
            CheckResult(
                "pca9685.steering_pwm_channel == 7",
                pca.steering_pwm_channel == EXPECTED_STEERING_CHANNEL,
                f"got {pca.steering_pwm_channel}",
            )
        )
        unpowered_note = (
            "" if self.vesc_powered
            else "; expected while VESC is unpowered (battery unplugged) -- re-verify in B3"
        )
        results.append(
            CheckResult(
                "vesc.controller_id == 83",
                vesc.controller_id == EXPECTED_VESC_CONTROLLER_ID,
                f"got {vesc.controller_id}{unpowered_note}",
                informational=not self.vesc_powered,
            )
        )
        results.append(
            CheckResult(
                "vesc.fault_code == 0",
                vesc.fault_code == EXPECTED_VESC_FAULT_CODE,
                f"got {vesc.fault_code}",
            )
        )
        results.append(
            CheckResult(
                "vesc.telemetry_fresh",
                bool(vesc.telemetry_fresh),
                f"telemetry_sequence={vesc.telemetry_sequence} "
                f"telemetry_age_ms={vesc.telemetry_age_ms}{unpowered_note}",
                informational=not self.vesc_powered,
            )
        )
        results.append(CheckResult("vehicle.imu_available", bool(veh.imu_available)))

        # --- Raw-byte cross-check ---
        pca_raw = decode_pca9685_state_raw(self.pca_state.raw_bytes)
        results += compare("pca9685", pca_raw, lambda k: getattr(pca, k))

        vesc_raw = decode_vesc_state_raw(self.vesc_state.raw_bytes)
        results += compare("vesc", vesc_raw, lambda k: getattr(vesc, k))

        # Same bytes, so float fields must match exactly (no tolerance) --
        # magnetic_field_t is ~1e-5 T, below compare()'s default tolerance.
        veh_raw = decode_vehicle_state_raw(self.vehicle_state.raw_bytes)
        results += compare(
            "vehicle", veh_raw, lambda k: _getattr_path(veh, k), tolerance=0.0
        )

        return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="seconds to wait for one sample of each topic"
    )
    parser.add_argument(
        "--vesc-powered",
        action="store_true",
        help="VESC is powered (Phase B3+): make controller_id/telemetry_fresh hard checks",
    )
    args = parser.parse_args(argv)

    rclpy.init()
    node = ReadonlyCheckNode(timeout_s=args.timeout, vesc_powered=args.vesc_powered)
    try:
        deadline = time.monotonic() + args.timeout
        while rclpy.ok() and time.monotonic() < deadline and not node.have_all_topics():
            rclpy.spin_once(node, timeout_sec=0.2)

        if not node.have_all_topics():
            missing = [
                name
                for name, st in (
                    ("/laksa/pca9685/state", node.pca_state),
                    ("/laksa/vesc/state", node.vesc_state),
                    ("/laksa/state", node.vehicle_state),
                )
                if st.typed_msg is None or st.raw_bytes is None
            ]
            print(
                f"TIMEOUT waiting for: {missing}. Is the micro-ROS agent running "
                f"and connected to /dev/laksa_microros?",
                file=sys.stderr,
            )
            return 2

        results = node.run_checks()
    finally:
        node.destroy_node()
        rclpy.shutdown()

    counted = [r for r in results if not r.informational]
    failed = [r for r in counted if not r.passed]
    info = [r for r in results if r.informational]
    for r in results:
        if r.informational:
            mark = "INFO" if not r.passed else "PASS"
        else:
            mark = "PASS" if r.passed else "FAIL"
        line = f"[{mark}] {r.name}"
        if r.detail:
            line += f"  ({r.detail})"
        print(line)

    print()
    if info:
        print(f"{len(info)} informational check(s) not counted (VESC unpowered; "
              f"re-run with --vesc-powered in B3).")
    if failed:
        print(f"{len(failed)}/{len(counted)} checks FAILED -- do NOT enable any command "
              f"publisher. Resolve against esp32_installed_firmware_findings.md first.")
        return 1

    print(f"ALL MATCH ({len(counted)}/{len(counted)} checks passed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
