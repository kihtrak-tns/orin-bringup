# orin-bringup

Sandbox ROS 2 workspace for the LAKSA Orin, built against `orin_bringup_plan.md`
(rev 2, 27 Sep 2026). This is **not** a copy of `Project-LAKSA/project_laksa`
(the firmware repo) -- it's the Orin-side sandbox that plan's A4 task calls
for: interfaces + provenance, bringup, no flash dumps or credentials.

**Built in a session with no link to the car or the Orin.** Nothing here has
run against real hardware yet. Treat every package as "compiles and matches
documented firmware evidence" only, until you've run it. `laksa_readonly_check`
in particular must report `ALL MATCH` on the real Orin before anything else
in this repo is trusted.

## What's here, mapped to the plan

| Package | Plan task | Status |
|---|---|---|
| `laksa_interfaces` | referenced throughout | msg/srv reconstructed from the real firmware repo (see Provenance below), not guessed |
| `laksa_bringup` | A1a, A1b, A3, A6 helper | `laksa_readonly_check`, `drive_command_loopback_test`, `laksa_health`, boot launch/systemd, bag recorder |
| `laksa_teleop_supervisor` | Phase E (prep) | manual-drive supervisor, **disabled by default**, not wired into any boot path |
| `laksa_replay` | Phase E (prep) | bag playback launch + `bag_stats` sanity check |

Owner column from the plan still applies: A1a's checker here is written and
ready, but *running* it on the car is yours; A1b's script is written, you run
it with the battery unplugged; A2 (LiDAR), A5 (ZED), A6 (recording the actual
bags) are not attempted here -- they need the physical sensors and Orin.

## Provenance (why these interfaces should be trusted)

`esp32_installed_firmware_findings.md` established that the flashed ESP32
build (`cba74e7-dirty`) mixes features from two branches of the public
`Project-LAKSA/project_laksa` repo. Rather than re-derive that from strings
a second time, this workspace's `laksa_interfaces` package was built by
cloning the actual branches and reading the actual `.msg`/`.srv` files:

- `DriveCommand`, `VescState`: `autonomy-handoff-2026-09-02` @ `4787d05`
  (has `brake` field, `brake_active`, `telemetry_sequence`, `telemetry_age_ms`)
- `Pca9685State`: `production/laksa-mainline` @ `1f0db4f`
  (only branch defining this message)
- `VehicleState`: identical on both branches, confirmed by diff

This matches `esp32_installed_firmware_findings.md` exactly (branch names,
commit hashes, and which fields came from which branch all line up). It does
**not** by itself prove the flashed binary's *wire layout* matches what's in
these files -- that's what `laksa_readonly_check`'s raw-byte cross-check is
for (see below). The public repo's own commits are strong evidence, not a
substitute for the on-car check.

## Safety posture (why it's safe to build/run pieces of this before Phase A/B/C are done)

- `laksa_interfaces`: data only, no behavior.
- `laksa_readonly_check`: subscribes only, never publishes. Cross-checks
  rclpy's typed deserialization against an independently-written raw CDR
  decode of the same bytes, because Humble does not check type hashes across
  the wire -- a wrong `laksa_interfaces` definition would otherwise
  deserialize "successfully" with silently wrong values.
- `drive_command_loopback_test`: the one script in this repo that publishes
  DriveCommand messages before Phase C. It refuses to run without
  `--confirm-battery-unplugged` and a typed confirmation phrase, and its
  docstring explains why battery-unplugged makes it safe (VESC/servo draw
  actuation power from the pack, not from USB).
- `laksa_health`: subscribes only, boot-safe by design; is the *only* thing
  meant to auto-start via systemd in this repo.
- `laksa_teleop_supervisor`: not referenced by any systemd unit or boot
  launch file here. Its own `enabled` parameter defaults to `false`, and even
  when enabled requires an active deadman signal every control cycle or it
  brakes. Its default speed limit (0.5 m/s) is a placeholder, not a validated
  vehicle limit -- see "Known gaps" below.

## Build

On the Orin (ROS 2 Humble, JetPack 6 family, Ubuntu 22.04 -- see
`docs/dependencies.md`):

```bash
cd orin-bringup
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

This has only been checked with `python3 -m py_compile` on every `.py` file
in a container with no ROS 2 install -- it has **not** been through `colcon
build` yet. Expect to fix at least minor build issues on first real build;
report them back so the interface/package files here can be corrected against
real evidence rather than left wrong.

## Known gaps / do not treat as done

- LiDAR (A2) and ZED (A5) drivers are not in this repo.
- No rosbags exist yet (A6); `laksa_replay` has nothing to replay until then.
- `laksa_teleop_supervisor`'s input format is `sensor_msgs/Joy` with
  parameterized axis/button indices -- no gamepad/joy driver has been chosen
  yet, wire one up separately.
- `max_abs_speed_mps` in the supervisor (0.5 m/s default) and any ERPM-based
  reasoning anywhere is a placeholder until the speed/odometry factor is
  measured (Phase C step 5, Decision #1).
- `udev/99-laksa.rules` reconstructs the ESP32 rule from confirmed live USB
  identifiers, but the LiDAR entry is a best guess (typical A2M12 CP210x
  IDs) -- the working rules are reportedly already installed on the Orin;
  don't overwrite them with this file without diffing first.
- systemd units assume `ROS_DOMAIN_ID=0`, `/opt/ros/humble`, a `laksa` user,
  and a workspace at `~/laksa_ws` -- adjust to the Orin's actual layout.

## Decisions still needed (carried from the plan, unchanged by this work)

1. Speed/odometry factor: Option 1 (fast) or Option 2 (clean rebuild) before
   the competition.
2. Approval for VESC configuration writes (Phase D).
3. Competition date(s); safety-review status and its wired-stop requirement.
4. GitHub access to the sandbox from the Orin.
5. Multimeter before untethered driving (Orin barrel polarity).
