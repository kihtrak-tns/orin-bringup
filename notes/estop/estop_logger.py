#!/usr/bin/env python3
# Logs every value change and any gap >120 ms on /laksa/estop_hw (read-only).
import time, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool
rclpy.init(); n = Node("estop_bench_logger")
st = {"last": None, "t": None, "count": 0}
def cb(m):
    now = time.time(); st["count"] += 1
    if st["t"] is not None and now - st["t"] > 0.12:
        print(f"{time.strftime('%H:%M:%S', time.gmtime(now))}.{int(now%1*1000):03d} GAP {now-st['t']:.3f}s", flush=True)
    if m.data != st["last"]:
        print(f"{time.strftime('%H:%M:%S', time.gmtime(now))}.{int(now%1*1000):03d} data={m.data} (msg #{st['count']})", flush=True)
        st["last"] = m.data
    st["t"] = now
n.create_subscription(Bool, "/laksa/estop_hw", cb, QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE))
def silent():
    if st["t"] and time.time() - st["t"] > 1.0 and st.get("silent_reported") != st["t"]:
        print(f"{time.strftime('%H:%M:%S', time.gmtime())} SILENT (last msg {time.time()-st['t']:.1f}s ago, last data={st['last']})", flush=True)
        st["silent_reported"] = st["t"]
n.create_timer(0.5, silent)
rclpy.spin(n)
