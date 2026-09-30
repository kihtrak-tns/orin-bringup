#!/usr/bin/env python3
# Read-only: timestamp every change of /laksa/estop_hw, /laksa/emergency_stop and its reason.
import time, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import Bool, String
L = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
rclpy.init(); n = Node("estop_supervisor_monitor"); st = {}
def ts():
    t = time.time(); return time.strftime("%H:%M:%S", time.gmtime(t)) + ".%03d" % int(t % 1 * 1000)
def mk(label):
    def cb(m):
        if st.get(label) != m.data:
            print(f"{ts()}  {label:<16} {m.data!r}", flush=True)
        st[label] = m.data
    return cb
n.create_subscription(Bool, "/laksa/estop_hw", mk("Rx estop_hw"), 10)
n.create_subscription(Bool, "/laksa/emergency_stop", mk("SUP latched"), L)
n.create_subscription(String, "/laksa/emergency_stop_reason", mk("SUP reason"), L)
rclpy.spin(n)
