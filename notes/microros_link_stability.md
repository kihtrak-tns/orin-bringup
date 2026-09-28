# ESP32 micro-ROS link — stability investigation (2026-09-27/28)

Status: **one bug fixed, one instability still open (narrowed 2026-09-28, see §4).** The open instability
must be understood before any live command-publisher work in Phase C.

Setup: `micro_ros_agent serial --dev /dev/laksa_microros -b 115200` (Humble,
agent built in `~/uros_ws` on the Orin, run by the operator in a
`screen -S microros` session). `/dev/laksa_microros -> ttyACM0`.

## 1. Not a USB/hardware-level reset (confirmed)

The kernel log for the current boot (only one boot in the journal, booted
2026-09-27 13:44 CDT) has exactly one `cdc_acm`/`ttyACM0` enumeration: at boot.
There are no USB disconnects or re-enumerations since. Checked by the operator
with `dmesg` (full log, boot to now) and re-checked by Claude Code with
`journalctl -k -b 0 | grep -iE 'cdc_acm|ttyACM|usb 1-2.*disconnect'` (3 lines,
all from the boot-time driver registration).

(The `/dev/ttyACM0` ctime of 00:13:44Z seen earlier is therefore udev touching
the node, not a re-enumeration.)

## 2. Fixed: agent had no typesupport for laksa_interfaces

Symptom: standard-type topics (`/laksa/imu/data`, `/laksa/imu/mag`,
`sensor_msgs`) delivered data, but the three custom-message topics
(`/laksa/state`, `/laksa/vesc/state`, `/laksa/pca9685/state`) never delivered a
single sample, even though `ros2 topic info` showed a publisher with matching
BEST_EFFORT QoS. A1a timed out on exactly those three (exit 2, 00:39:15Z).

Cause: the agent's own workspace `~/uros_ws` did not contain
`laksa_interfaces`. With no typesupport, the agent can create the DDS
entities (they show up in the graph) but cannot deliver data for those types,
however stable the serial session is.

Fix (on the Orin, outside this git repo, since `uros_ws` is a separate,
pre-existing workspace): copied `laksa_interfaces` into `~/uros_ws/src/` and
rebuilt that workspace, then restarted the agent. Evidence:
`~/uros_ws/src/laksa_interfaces` (01:31Z) and
`~/uros_ws/install/laksa_interfaces` (01:36Z) exist. After the fix, A1a
received all three topics and passed
(`results/A1a_20260928T022525Z.md`).

**Keep in sync:** `~/uros_ws/src/laksa_interfaces` is now a *copy* of
`src/laksa_interfaces` from this repo. If the message definitions here ever
change, that copy must be updated and `uros_ws` rebuilt too, or the agent
will be out of step with the Orin-side nodes.

## 3. Still open: the XRCE session itself is intermittently unstable

Observed by the operator from the agent log:
- The micro-ROS **session** intermittently tears down and is re-created
  (entities deleted, then `create_participant`/`create_topic`/... again) at
  irregular intervals, from ~21 s to ~63 min apart.
- Separately, the link once went **fully silent** with no session teardown
  logged at all. Claude Code saw this independently at ~00:42Z: 0 samples on
  all 5 topics over 30 s (including the IMU topics that had delivered minutes
  earlier), and the agent process used 0 CPU ticks over 5 s, so it was getting
  no serial traffic. The last session creation was at 00:08:23Z.

Ruled out so far: USB re-enumeration (§1). No evidence of an ESP32 reboot has
been found either (no USB event, nothing in the agent log that looks like a
fresh boot). Root cause not yet found.

Candidates worth checking (not yet tested):
- ESP32 firmware-side: ping/timeout logic (`rmw_uros_ping_agent` + reconnect
  state machine) giving up and re-creating the session, or a task stalling
  (watchdog, blocking I2C/UART read to the unpowered VESC) that starves the
  micro-ROS executor. The "silent, no teardown" mode fits a stalled
  executor/transport better than a reconnect.
- ESP32 serial console / reset reason (`esp_reset_reason()`) to settle the
  "did it reboot?" question directly.
- Agent run with `-v6` to log per-message traffic and the timing of the
  teardown relative to the last data seen.
- 115200 baud headroom versus the aggregate publish rate of 5 topics.

## 4. Load experiment (2026-09-28): narrows it, doesn't settle it

Full data: `results/churn_experiment_20260928T132216Z.md`. Three 15-min
windows plus 3.4 h of extra idle observation, counting agent `delete_client`
teardowns:

| condition | resets / 15 min | CPU % |
|---|---|---|
| idle (14 windows) | 2–9, mean ~5.7 (~23/h) | ~2 |
| 100% CPU busy-loop | 3 | 100 |
| LiDAR + ZED running | 11 | 38 (GPU 11) |

What this settles or narrows:
- **The churn is present at rest, at ~23 resets/h** with only agent + health
  running. Load is not the root cause. (The earlier "~21 s to ~63 min apart"
  observation now reads as that idle baseline.)
- **CPU starvation is ruled out as the mechanism:** 100% CPU on all cores
  gave no increase.
- **LiDAR+ZED is associated with ~2× churn** (above all 14 idle windows), at
  lower CPU than the CPU test. n = 1, so suggestive, not proven. Not yet
  separated: shared-hub USB traffic vs USB bus power vs DDS/GPU activity.
- **USB topology:** one xHCI controller; the ESP32, LiDAR and ZED HID sit on
  the same external USB 2.0 hub (the ZED video is on that hub chip's USB 3
  half). The hub is **multi-TT**, so full-speed bandwidth starvation of the
  ESP32 is less likely than shared power/upstream effects.
- **Every data stall in 45 min coincided with a session reset** (1–2.5 s of
  lost data each); the "silent, no teardown" mode was not reproduced.
- Each reset re-arms the firmware's `/laksa/brake` latch (see the A1b
  addendum in `docs/esp32_installed_firmware_findings.md`). At ~23/h idle and
  ~44/h with sensors running, any command publisher **must** re-release it
  continuously.

Next discriminating tests (not run): LiDAR-only vs ZED-only windows; the
ESP32 moved off the shared hub to its own port; a powered hub for the ZED;
agent `-v6` and ESP32-side ping/timeout logging for the idle churn.

## 5. USB autosuspend: ruled out (2026-09-28, read-only)

Full data: `results/autosuspend_check_20260928T141630Z.md`. The ESP32 device
(`power/control=on`), its USB2 hub, the USB2 root and the xHCI controller
each show **0 ms runtime-suspended in 5.77 h since boot**
(`active_duration == connected_duration`), and 119 session resets happened
in that time. Autosuspend can't be the mechanism, so no change was made
(the system is still at boot defaults). The USB3 half (ZED video + its hub)
does autosuspend, but it sits steadily suspended at idle while idle churn
continues, so it can't drive the idle rate. CPU DVFS is also largely covered
already: in the load experiment's CPU condition all cores were pinned at max
frequency for 15 min, with no change in churn. EMC/GPU DVFS (MAXN +
`jetson_clocks`) remains an optional, low-expected-value test.

With host-side power management largely set aside, the **ESP32/firmware and
transport side is now the leading area** for the idle churn: micro-ROS
ping/timeout and reconnect logic, executor stalls, serial framing. Agent
`-v6` around a teardown is the next cheap look.

## 6. Mechanism (2026-09-28, agent -v6): the ESP32 misses a reply the host sent on time

Full data: `results/churn_mechanism_20260928T154208Z.md`. The firmware tears
the session down after one failed ping (100 ms timeout, every 500 ms, no
retries; `micro_ros_bridge.c:33-39, 585-593`). With the agent at `-v6`, all
4 captured teardowns follow the same pattern: the ESP32's last ping reached
the agent, and **the agent replied in 0.36–0.42 ms**, yet **~107 ms later**
the ESP32 started reconnecting. Over 646 pings, agent reply latency was
median 0.38 ms, p99 0.72 ms. The reply is lost or late on the host→ESP32
leg, or not read by the ESP32 within 100 ms. The host/kernel/agent side is
not the late party. No kernel USB events on the ESP32 path across 123 resets;
usbmon is unavailable (`CONFIG_USB_MON` not set).

Secondary: each teardown costs ~1 s of data because the agent deletes the
~20 old DDS entities at ~100 ms each before re-establishing.

Leading fix direction (firmware): tolerate N consecutive ping failures and/or
a longer timeout before tearing down; instrument the ESP32 transport (RX
overflow and framing/CRC error counters, ping RTT) to find where the reply
is lost.

## 7. Device isolation (2026-09-28, Part 2): ZED is the dominant load factor; same mechanism everywhere

Bookended 5 × 15 min (`results/churn_mechanism_20260928T154208Z.md`, Part 2):
ESP32 only **6** → +LiDAR **8** → ZED only **12** → LiDAR+ZED **14** → ESP32
only **7**. **47/47 resets** show the Part 1 pattern (agent replied to the
fatal ping in 0.13–0.46 ms; the ESP32 gave up 101–103 ms later). The bookends
agree (no drift). The LiDAR is within idle variation; the ZED doubles the rate.
Fix direction unchanged: firmware ping tolerance + ESP32 RX-path
instrumentation. Open cheap test: move the ESP32 off the shared hub and repeat
ESP32-only vs ZED-only.

## Risk assessment

- **A1a:** unaffected. A read-only snapshot that passed on a live session.
- **A1b (loopback):** tolerable. It's read-only-adjacent with the battery
  unplugged, and a dropped session shows up as a missed echo that can be
  retried, not as motion.
- **Phase C (live command publisher):** **do not proceed** until the session
  drops and the silent stalls are understood. A session that can go silent
  with no teardown means the ESP32 may stop receiving `/laksa/command` and
  `/laksa/brake` without the Orin side seeing any error. The firmware's
  command-freshness timeout (`vesc.command_fresh`) has to be verified to stop
  the car in exactly that situation.
