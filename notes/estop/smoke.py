#!/usr/bin/env python3
# Freshness-patch smoke test, steps 1-4 (loop CLOSED throughout). Usage: smoke.py
import os, signal, subprocess, sys, time
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from sensor_msgs.msg import Joy
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
LATCHED = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
PIDF = os.path.expanduser("~/estop_bridge/bridge.pid")
rclpy.init(); n = Node("estop_smoke_test")
st = {"estop": None, "reason": None, "hw": None, "events": []}
def ts(t): return time.strftime("%H:%M:%S", time.gmtime(t)) + ".%03d" % int(t % 1 * 1000)
def mk(key):
    def cb(m):
        if st[key] != m.data:
            st["events"].append((time.time(), key, m.data)); print(f"  {ts(time.time())} {key} = {m.data!r}", flush=True)
        st[key] = m.data
    return cb
n.create_subscription(Bool, "/laksa/emergency_stop", mk("estop"), LATCHED)
n.create_subscription(String, "/laksa/emergency_stop_reason", mk("reason"), LATCHED)
n.create_subscription(Bool, "/laksa/estop_hw", mk("hw"), 10)
joy = n.create_publisher(Joy, "/joy", 10)
def spin(sec):
    end = time.time() + sec
    while time.time() < end: rclpy.spin_once(n, timeout_sec=0.005)
def press_y():
    for b in (0, 1, 0):
        m = Joy(); m.header.frame_id = "joy"; m.header.stamp = n.get_clock().now().to_msg()
        m.axes = [0.0] * 8; m.buttons = [0] * 11; m.buttons[3] = b
        joy.publish(m); print(f"  {ts(time.time())} /joy Y={b}", flush=True); spin(0.2)
def start_bridge():
    print(subprocess.run(["bash", os.path.expanduser("~/estop_bridge/start_bridge.sh")], capture_output=True, text=True).stdout.strip())
def check(name, ok, detail):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)
    if not ok: sys.exit(1)
spin(2.0)  # discovery + current state
check("step1 supervisor latched, bridge not running", st["estop"] is True and st["reason"] == "hardware e-stop link lost",
      f"estop={st['estop']} reason={st['reason']!r} hw={st['hw']}")
print("== step2: start bridge, wait for RUN + 1 s, press Y"); start_bridge()
t0 = time.time()
while st["hw"] is not False and time.time() - t0 < 5: spin(0.05)
spin(1.0); press_y(); spin(1.0)
check("step2 rearm with bridge alive", st["estop"] is False and st["reason"] == "", f"estop={st['estop']} reason={st['reason']!r} hw={st['hw']}")
print("== step3: kill -9 bridge"); spin(1.0)
pid = int(open(PIDF).read()); st["events"].clear(); tk = time.time(); os.kill(pid, signal.SIGKILL)
print(f"  {ts(tk)} SIGKILL {pid}")
while st["estop"] is not True and time.time() - tk < 3: spin(0.005)
lat = next((t - tk for t, k, v in st["events"] if k == "estop" and v is True), None)
spin(0.3)
check("step3 latch on link loss", lat is not None and lat <= 0.7 and st["reason"] == "hardware e-stop link lost",
      f"latency={lat if lat is None else round(lat*1000)} ms after SIGKILL; reason={st['reason']!r}")
print("== step4: restart bridge, wait RUN + 1 s, press Y"); start_bridge()
t0 = time.time()
while st["hw"] is not False and time.time() - t0 < 5: spin(0.05)
spin(1.0); press_y(); spin(1.0)
check("step4 recovery", st["estop"] is False and st["reason"] == "", f"estop={st['estop']} reason={st['reason']!r} hw={st['hw']}")
