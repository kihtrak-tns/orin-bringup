#!/usr/bin/env python3
# Print current /laksa/emergency_stop, reason and /laksa/estop_hw; optional "y" arg presses Y.
import sys, time, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import Bool, String
from sensor_msgs.msg import Joy
L = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
rclpy.init(); n = Node("estop_state_probe"); st = {}
def ts(): t=time.time(); return time.strftime("%H:%M:%S", time.gmtime(t)) + ".%03d" % int(t % 1 * 1000)
def mk(k):
    def cb(m):
        if st.get(k) != m.data: print(f"  {ts()} {k} = {m.data!r}", flush=True)
        st[k] = m.data
    return cb
n.create_subscription(Bool, "/laksa/emergency_stop", mk("estop"), L)
n.create_subscription(String, "/laksa/emergency_stop_reason", mk("reason"), L)
n.create_subscription(Bool, "/laksa/estop_hw", mk("hw"), 10)
def spin(s):
    e = time.time() + s
    while time.time() < e: rclpy.spin_once(n, timeout_sec=0.01)
spin(1.5)
if "y" in sys.argv[1:]:
    p = n.create_publisher(Joy, "/joy", 10); spin(0.5)
    for b in (0, 1, 0):
        m = Joy(); m.header.frame_id = "joy"; m.header.stamp = n.get_clock().now().to_msg()
        m.axes = [0.0]*8; m.buttons = [0]*11; m.buttons[3] = b; p.publish(m); print(f"  {ts()} /joy Y={b}", flush=True); spin(0.2)
    spin(1.0)
print("STATE", st)
