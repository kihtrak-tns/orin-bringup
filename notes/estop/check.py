#!/usr/bin/env python3
# Pre-run health check: VESC voltage/fault, supervisor e-stop state, estop_hw.
import time, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, qos_profile_sensor_data
from std_msgs.msg import Bool, String
from laksa_interfaces.msg import VehicleState
L = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
rclpy.init(); n = Node("wlift_precheck"); st = {"n_state": 0}
def s(m): st.update(n_state=st["n_state"]+1, v=round(m.vesc.input_voltage_v, 2), fault=m.vesc.fault_code, erpm=m.vesc.measured_erpm, tele_fresh=m.vesc.telemetry_fresh, tele_age_ms=m.vesc.telemetry_age_ms)
n.create_subscription(VehicleState, "/laksa/state", s, qos_profile_sensor_data)
n.create_subscription(Bool, "/laksa/emergency_stop", lambda m: st.update(estop=m.data), L)
n.create_subscription(String, "/laksa/emergency_stop_reason", lambda m: st.update(reason=m.data), L)
n.create_subscription(Bool, "/laksa/estop_hw", lambda m: st.update(hw=m.data), 10)
e = time.time() + 3
while time.time() < e: rclpy.spin_once(n, timeout_sec=0.01)
print(st)
