# ESP32 micro-ROS link — stability investigation (2026-09-27/28)

Status: **one bug fixed, one instability still open.** The open instability
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
