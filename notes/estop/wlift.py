#!/usr/bin/env python3
"""Wheels-lift e-stop test driver (car on blocks, operator watching, hand on XT60).

Publishes /joy at 20 Hz: neutral (releases the supervisor's neutral interlock),
optional Y press to rearm, then a small forward stick for --duration seconds,
then neutral. Throttle beyond the deadzone maps to the 900 eRPM manual preset.
If this process dies, /joy goes stale and the supervisor brakes within 0.5 s.

Measures, from the trigger (first /laksa/estop_hw true, or the bridge kill this
script sends), the time to supervisor latch, to /laksa/command brake/zero speed,
and to wheels stopped (|vesc.measured_erpm| < STOP_ERPM on /laksa/state).

Abort: touch ~/estop_bridge/ABORT  -> neutral immediately and exit.
"""
import argparse, os, signal, sys, time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, qos_profile_sensor_data
from std_msgs.msg import Bool, String, Int32
from sensor_msgs.msg import Joy
from laksa_interfaces.msg import DriveCommand, VehicleState

STOP_ERPM = 50.0
MAX_DURATION = 45.0
THROTTLE = 0.5
ABORT = os.path.expanduser("~/estop_bridge/ABORT")
PIDF = os.path.expanduser("~/estop_bridge/bridge.pid")
LATCHED = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)

ap = argparse.ArgumentParser()
ap.add_argument("--duration", type=float, default=20.0)
ap.add_argument("--rearm", action="store_true", help="press Y before driving")
ap.add_argument("--kill-bridge-at", type=float, default=None,
                help="seconds into the throttle phase to signal the bridge")
ap.add_argument("--ramp", default=None, help="comma list of eRPM presets, e.g. 900,1300,1500")
ap.add_argument("--step-sec", type=float, default=3.0)
ap.add_argument("--signal", choices=["TERM", "KILL"], default="TERM")
a = ap.parse_args()
a.duration = min(a.duration, MAX_DURATION)

rclpy.init()
n = Node("wheels_lift_test")
st = {"estop": None, "reason": None, "hw": None, "erpm": None, "cmd": None}
ev = {"trigger": None, "latch": None, "cmd_stop": None, "wheels_stop": None,
      "peak_erpm": 0.0}


def ts(t=None):
    t = time.time() if t is None else t
    return time.strftime("%H:%M:%S", time.gmtime(t)) + ".%03d" % int(t % 1 * 1000)


def log(msg):
    print(f"  {ts()} {msg}", flush=True)


def on_hw(m):
    if st["hw"] != m.data:
        log(f"estop_hw = {m.data}")
        if m.data and phase == "drive" and ev["trigger"] is None:
            ev["trigger"] = time.time()
    st["hw"] = m.data


def on_estop(m):
    if st["estop"] != m.data:
        log(f"emergency_stop = {m.data}")
        if m.data and ev["trigger"] is not None and ev["latch"] is None:
            ev["latch"] = time.time()
    st["estop"] = m.data


def on_reason(m):
    if st["reason"] != m.data:
        log(f"reason = {m.data!r}")
    st["reason"] = m.data


def on_cmd(m):
    key = (round(m.speed_mps, 3), m.brake)
    if st["cmd"] != key:
        log(f"/laksa/command speed={m.speed_mps:.3f} brake={m.brake}")
        if (ev["trigger"] is not None and ev["cmd_stop"] is None
                and (m.brake or abs(m.speed_mps) < 1e-3)):
            ev["cmd_stop"] = time.time()
    st["cmd"] = key


last_erpm_print = [0.0]


def on_state(m):
    e = float(m.vesc.measured_erpm)
    st["erpm"] = e
    ev["peak_erpm"] = max(ev["peak_erpm"], abs(e)) if phase == "drive" else ev["peak_erpm"]
    now = time.time()
    if now - last_erpm_print[0] >= (0.25 if phase == "drive" else 1.0):
        v = m.vesc
        log(f"measured_erpm = {e:.0f}  req={v.requested_erpm} act={v.active_erpm} cmd_fresh={v.command_fresh} "
            f"brake={v.brake_active} dir_pend={v.direction_change_pending} I_mot={v.motor_current_a:.2f} A "
            f"I_in={v.input_current_a:.2f} A duty={v.duty_cycle:.3f} (fault {v.fault_code}, {v.input_voltage_v:.1f} V)")
        last_erpm_print[0] = now
    if ev["trigger"] is not None and ev["wheels_stop"] is None and abs(e) < STOP_ERPM:
        ev["wheels_stop"] = now
        log(f"WHEELS STOPPED (measured_erpm {e:.0f})")


phase = "setup"
n.create_subscription(Bool, "/laksa/estop_hw", on_hw, 10)
n.create_subscription(Bool, "/laksa/emergency_stop", on_estop, LATCHED)
n.create_subscription(String, "/laksa/emergency_stop_reason", on_reason, LATCHED)
n.create_subscription(DriveCommand, "/laksa/command", on_cmd, 10)
n.create_subscription(VehicleState, "/laksa/state", on_state, qos_profile_sensor_data)
joy = n.create_publisher(Joy, "/joy", 10)
preset = n.create_publisher(Int32, "/laksa/manual_speed_erpm", LATCHED)
RAMP = [int(x) for x in a.ramp.split(",")] if a.ramp else []
if RAMP:
    a.duration = min(MAX_DURATION, a.step_sec * len(RAMP))


def set_preset(v):
    preset.publish(Int32(data=v)); log(f"manual_speed_erpm preset -> {v}")


def send(throttle=0.0, y=0):
    m = Joy()
    m.header.frame_id = "joy"
    m.header.stamp = n.get_clock().now().to_msg()
    m.axes = [0.0] * 8
    m.axes[1] = throttle
    m.buttons = [0] * 11
    m.buttons[3] = y
    joy.publish(m)


def run(seconds, throttle=0.0, y=0):
    end = time.time() + seconds
    nxt = time.time()
    while time.time() < end:
        if os.path.exists(ABORT):
            raise KeyboardInterrupt("ABORT file")
        if time.time() >= nxt:
            send(throttle, y)
            nxt += 0.05
        rclpy.spin_once(n, timeout_sec=0.005)


def neutral_exit(code):
    try:
        run(1.0, 0.0)
        if RAMP:
            set_preset(900); run(0.3, 0.0)
    finally:
        print("RESULT", {k: (ts(v) if isinstance(v, float) and v > 1e9 else v) for k, v in ev.items()}, flush=True)
        if ev["trigger"]:
            for k in ("latch", "cmd_stop", "wheels_stop"):
                d = ev[k]
                print(f"  {k:12s}: " + (f"{(d - ev['trigger']) * 1000:.0f} ms after trigger" if d else "NOT SEEN"), flush=True)
        n.destroy_node()
        rclpy.shutdown()
        sys.exit(code)


signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt("SIGTERM")))
try:
    run(1.5, 0.0)  # discovery + neutral (releases interlock)
    print(f"START estop={st['estop']} reason={st['reason']!r} hw={st['hw']} erpm={st['erpm']}", flush=True)
    if a.rearm:
        run(0.3, 0.0, 1)
        run(0.6, 0.0, 0)
        log(f"after Y: estop={st['estop']} reason={st['reason']!r}")
    if st["estop"]:
        print("Supervisor still latched; not driving.", flush=True)
        neutral_exit(2)
    phase = "drive"
    log(f"THROTTLE {THROTTLE} for {a.duration:.0f} s")
    t0 = time.time()
    killed = False
    step = -1
    while time.time() - t0 < a.duration:
        if RAMP:
            k = min(int((time.time() - t0) // a.step_sec), len(RAMP) - 1)
            if k != step:
                step = k; set_preset(RAMP[k])
        run(0.05, THROTTLE)
        if a.kill_bridge_at is not None and not killed and time.time() - t0 >= a.kill_bridge_at:
            pid = int(open(PIDF).read())
            ev["trigger"] = time.time()
            os.kill(pid, signal.SIGTERM if a.signal == "TERM" else signal.SIGKILL)
            log(f"SIG{a.signal} bridge pid {pid}")
            killed = True
    phase = "done"
    log("THROTTLE released")
    neutral_exit(0)
except KeyboardInterrupt as exc:
    log(f"interrupted ({exc}); neutral")
    phase = "done"
    neutral_exit(3)
