#!/usr/bin/env python3
"""Phase E prep: manual-drive supervisor. DISABLED BY DEFAULT.

This is the only node in this workspace meant to eventually be a long-lived
DriveCommand publisher for manual driving. It is written now, in parallel
with Phase A/B/C hardware work, per the plan's Phase E note ("Now (Claude):
... supervisor for manual drive ... disabled by default").

Layered defenses so this cannot accidentally start commanding the vehicle:
  1. The `enabled` ROS parameter defaults to False. While False, the node
     subscribes to nothing that could look like "armed" and its timer loop
     only logs that it is disabled -- it never touches the DriveCommand
     publisher. Must be explicitly overridden (enabled:=true) at launch.
  2. Even when enabled, actual output requires a currently-active deadman
     signal (a button held on the input device, see `deadman_button_index`).
     Any Joy message where the deadman button is not pressed is treated
     identically to no input at all: brake.
  3. Stale-input brake: if no Joy message has arrived within
     `input_timeout_s`, or the deadman was released, the node publishes
     brake=True, speed_mps=0.0, steering_angle_rad=0.0 -- not just "stop
     publishing" (stopping relies on the ESP32's own 500 ms timeout as a
     second layer, not the first).
  4. Rate limiting: both speed_mps and steering_angle_rad are slew-rate
     limited (max change per second) before being sent, and hard-clamped to
     `max_abs_speed_mps` / `max_abs_steer_rad`.

Known placeholder needing a real number before this is used for real driving:
`max_abs_speed_mps` defaults very conservatively (0.5 m/s) because the
speed/ERPM scale factor is still unmeasured (Phase C step 5 / Decision #1 in
orin_bringup_plan.md). Do not raise it until that factor is measured -- this
default is a safety placeholder, not a validated vehicle limit.

Input format: sensor_msgs/Joy, from whatever `joy_node` (or equivalent) the
teammate's gamepad uses. Axis/button indices are parameters, not hardcoded,
since the actual gamepad hasn't been decided in the plan yet.
"""
from __future__ import annotations

import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import Joy

from laksa_interfaces.msg import DriveCommand

QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.RELIABLE,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
    durability=QoSDurabilityPolicy.VOLATILE,
)

CONTROL_RATE_HZ = 20.0


class SupervisorNode(Node):
    def __init__(self):
        super().__init__("laksa_teleop_supervisor")

        self.declare_parameter("enabled", False)
        self.declare_parameter("input_timeout_s", 0.2)
        self.declare_parameter("deadman_button_index", 4)
        self.declare_parameter("brake_button_index", 5)
        self.declare_parameter("speed_axis_index", 1)
        self.declare_parameter("steer_axis_index", 0)
        self.declare_parameter("max_abs_speed_mps", 0.5)  # SAFETY PLACEHOLDER, see docstring
        self.declare_parameter("max_abs_steer_rad", 0.6458)  # ~+-37 deg, servo limit from findings
        self.declare_parameter("max_speed_slew_mps2", 1.0)
        self.declare_parameter("max_steer_slew_rad_s", 3.0)

        self._last_joy = None
        self._last_joy_rx_time = None
        self._current_speed_mps = 0.0
        self._current_steer_rad = 0.0
        self._last_loop_time = time.monotonic()

        self.command_pub = self.create_publisher(DriveCommand, "/laksa/command", QOS)
        self.create_subscription(Joy, "/joy", self._on_joy, QOS)
        self.create_timer(1.0 / CONTROL_RATE_HZ, self._control_loop)

        if not self.get_parameter("enabled").value:
            self.get_logger().warn(
                "laksa_teleop_supervisor is DISABLED (enabled:=false). "
                "No DriveCommand will be published. Pass enabled:=true to arm."
            )

    def _on_joy(self, msg: Joy) -> None:
        self._last_joy = msg
        self._last_joy_rx_time = time.monotonic()

    def _slew_limit(self, current: float, target: float, max_rate: float, dt: float) -> float:
        max_step = max_rate * dt
        delta = target - current
        if delta > max_step:
            delta = max_step
        elif delta < -max_step:
            delta = -max_step
        return current + delta

    def _control_loop(self) -> None:
        now = time.monotonic()
        dt = now - self._last_loop_time
        self._last_loop_time = now

        enabled = bool(self.get_parameter("enabled").value)
        if not enabled:
            return  # armed defense #1: not even a brake command is sent; node is inert

        timeout_s = float(self.get_parameter("input_timeout_s").value)
        deadman_idx = int(self.get_parameter("deadman_button_index").value)
        brake_idx = int(self.get_parameter("brake_button_index").value)
        speed_axis = int(self.get_parameter("speed_axis_index").value)
        steer_axis = int(self.get_parameter("steer_axis_index").value)
        max_speed = abs(float(self.get_parameter("max_abs_speed_mps").value))
        max_steer = abs(float(self.get_parameter("max_abs_steer_rad").value))
        max_speed_slew = float(self.get_parameter("max_speed_slew_mps2").value)
        max_steer_slew = float(self.get_parameter("max_steer_slew_rad_s").value)

        joy = self._last_joy
        stale = (
            joy is None
            or self._last_joy_rx_time is None
            or (now - self._last_joy_rx_time) > timeout_s
        )
        deadman_held = (
            not stale and len(joy.buttons) > deadman_idx and joy.buttons[deadman_idx] == 1
        )
        brake_requested = (
            not stale and len(joy.buttons) > brake_idx and joy.buttons[brake_idx] == 1
        )

        cmd = DriveCommand()

        if stale or not deadman_held or brake_requested:
            # Defenses #2 and #3: brake, and reset the slew-limited state so
            # there's no discontinuity/lurch if driving resumes later.
            self._current_speed_mps = 0.0
            self._current_steer_rad = 0.0
            cmd.speed_mps = 0.0
            cmd.steering_angle_rad = 0.0
            cmd.brake = True
            self.command_pub.publish(cmd)
            return

        target_speed = 0.0
        target_steer = 0.0
        if len(joy.axes) > speed_axis:
            target_speed = max(-1.0, min(1.0, joy.axes[speed_axis])) * max_speed
        if len(joy.axes) > steer_axis:
            target_steer = max(-1.0, min(1.0, joy.axes[steer_axis])) * max_steer

        self._current_speed_mps = self._slew_limit(
            self._current_speed_mps, target_speed, max_speed_slew, dt
        )
        self._current_steer_rad = self._slew_limit(
            self._current_steer_rad, target_steer, max_steer_slew, dt
        )

        cmd.speed_mps = max(-max_speed, min(max_speed, self._current_speed_mps))
        cmd.steering_angle_rad = max(-max_steer, min(max_steer, self._current_steer_rad))
        cmd.brake = False
        self.command_pub.publish(cmd)


def main(argv=None):
    rclpy.init(args=argv)
    node = SupervisorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
