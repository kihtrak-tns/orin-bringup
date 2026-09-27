#!/usr/bin/env python3
"""A3: laksa_health -- listen-only health check, safe to run at every boot.

Publishes diagnostic_msgs/DiagnosticArray on /diagnostics at 1 Hz summarizing:
  - whether /laksa/state, /laksa/vesc/state, /laksa/pca9685/state are being
    received at all, and how stale the freshest sample is
  - vesc.telemetry_fresh and vesc.fault_code (WARN if fault_code != 0)
  - pca9685.responsive and pca9685.automatic_recovery_enabled (WARN if a
    reinitialization_count increase is observed between samples)
  - vehicle.imu_available

This node makes no publishers other than /diagnostics: it cannot become a
DriveCommand publisher and never will, by design, since it is the thing
allowed to run unattended at boot (see A3's "Done when": reboot -> health
green with no manual steps, with any command publisher disabled by default).
"""
from __future__ import annotations

import time

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy

from laksa_interfaces.msg import Pca9685State, VehicleState, VescState

QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.RELIABLE,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
    durability=QoSDurabilityPolicy.VOLATILE,
)

STALE_AFTER_S = 1.0


class LaksaHealth(Node):
    def __init__(self):
        super().__init__("laksa_health")
        self._last_vehicle = None
        self._last_vehicle_rx_time = None
        self._last_vesc = None
        self._last_vesc_rx_time = None
        self._last_pca = None
        self._last_pca_rx_time = None
        self._last_reinit_count = None

        self.create_subscription(VehicleState, "/laksa/state", self._on_vehicle, QOS)
        self.create_subscription(VescState, "/laksa/vesc/state", self._on_vesc, QOS)
        self.create_subscription(Pca9685State, "/laksa/pca9685/state", self._on_pca, QOS)

        self.diag_pub = self.create_publisher(DiagnosticArray, "/diagnostics", 10)
        self.create_timer(1.0, self._publish_diagnostics)

    def _on_vehicle(self, msg):
        self._last_vehicle = msg
        self._last_vehicle_rx_time = time.monotonic()

    def _on_vesc(self, msg):
        self._last_vesc = msg
        self._last_vesc_rx_time = time.monotonic()

    def _on_pca(self, msg):
        self._last_pca = msg
        self._last_pca_rx_time = time.monotonic()

    def _status(self, name: str, level: int, message: str, kvs: dict) -> DiagnosticStatus:
        st = DiagnosticStatus()
        st.name = name
        st.level = level
        st.message = message
        st.hardware_id = "laksa_esp32"
        st.values = [KeyValue(key=k, value=str(v)) for k, v in kvs.items()]
        return st

    def _publish_diagnostics(self):
        now = time.monotonic()
        arr = DiagnosticArray()
        arr.header.stamp = self.get_clock().now().to_msg()

        # --- link / freshness ---
        def age(rx_time):
            return None if rx_time is None else now - rx_time

        vehicle_age = age(self._last_vehicle_rx_time)
        vesc_age = age(self._last_vesc_rx_time)
        pca_age = age(self._last_pca_rx_time)

        link_ok = all(
            a is not None and a <= STALE_AFTER_S for a in (vehicle_age, vesc_age, pca_age)
        )
        arr.status.append(
            self._status(
                "laksa: micro-ROS link",
                DiagnosticStatus.OK if link_ok else DiagnosticStatus.ERROR,
                "receiving all three state topics" if link_ok else "one or more topics stale/missing",
                {
                    "vehicle_state_age_s": vehicle_age,
                    "vesc_state_age_s": vesc_age,
                    "pca9685_state_age_s": pca_age,
                },
            )
        )

        # --- VESC ---
        if self._last_vesc is not None:
            v = self._last_vesc
            fault_ok = v.fault_code == 0
            arr.status.append(
                self._status(
                    "laksa: VESC",
                    DiagnosticStatus.OK if (fault_ok and v.telemetry_fresh) else DiagnosticStatus.WARN,
                    "nominal" if fault_ok else f"fault_code={v.fault_code}",
                    {
                        "telemetry_fresh": v.telemetry_fresh,
                        "fault_code": v.fault_code,
                        "input_voltage_v": round(v.input_voltage_v, 2),
                        "requested_erpm": v.requested_erpm,
                        "command_fresh": v.command_fresh,
                        "brake_active": v.brake_active,
                    },
                )
            )
        else:
            arr.status.append(
                self._status("laksa: VESC", DiagnosticStatus.ERROR, "no data received yet", {})
            )

        # --- PCA9685 / steering ---
        if self._last_pca is not None:
            p = self._last_pca
            reinit_warn = (
                self._last_reinit_count is not None
                and p.reinitialization_count > self._last_reinit_count
            )
            self._last_reinit_count = p.reinitialization_count
            ok = p.initialized and p.responsive and not reinit_warn
            arr.status.append(
                self._status(
                    "laksa: PCA9685/steering",
                    DiagnosticStatus.OK if ok else DiagnosticStatus.WARN,
                    "nominal" if ok else "reinitialized since last check or not responsive",
                    {
                        "initialized": p.initialized,
                        "responsive": p.responsive,
                        "automatic_recovery_enabled": p.automatic_recovery_enabled,
                        "reinitialization_count": p.reinitialization_count,
                        "total_i2c_errors": p.total_i2c_errors,
                    },
                )
            )
        else:
            arr.status.append(
                self._status(
                    "laksa: PCA9685/steering", DiagnosticStatus.ERROR, "no data received yet", {}
                )
            )

        # --- IMU presence ---
        if self._last_vehicle is not None:
            imu_ok = bool(self._last_vehicle.imu_available)
            arr.status.append(
                self._status(
                    "laksa: IMU",
                    DiagnosticStatus.OK if imu_ok else DiagnosticStatus.WARN,
                    "available" if imu_ok else "imu_available=false",
                    {},
                )
            )

        self.diag_pub.publish(arr)

        overall = max((s.level for s in arr.status), default=DiagnosticStatus.OK)
        overall_str = {0: "OK", 1: "WARN", 2: "ERROR", 3: "STALE"}.get(overall, "?")
        self.get_logger().info(f"laksa_health: {overall_str}")


def main(argv=None):
    rclpy.init(args=argv)
    node = LaksaHealth()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
