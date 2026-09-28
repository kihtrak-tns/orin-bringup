# Status

Orin SSH target: `dev-orin` (SSH config alias on the WSL machine, in `~/.ssh/config`)

Multi-agent note: `Agent` names who produced the result and may therefore set
`Status` for that row (see CLAUDE.md's "Multi-agent coordination" section).
A row set by anyone else is a proposal, not a status — leave `Status`
unchanged and note the disagreement in the result file instead.

| Task | Status | Timestamp (UTC) | Agent | Result |
|---|---|---|---|---|
| A1a laksa_readonly_check | done — 97/97 ALL MATCH; VESC controller_id/telemetry_fresh deferred to B3 (unpowered) | 2026-09-28T02:25:25Z | local Claude Code | [results/A1a_20260928T022525Z.md](results/A1a_20260928T022525Z.md) |
| A1b drive_command_loopback_test | done — PASS 6/6 on re-run 3 with /laksa/brake=false held during command steps; confirms the boot-default brake latch root cause ([findings addendum](docs/esp32_installed_firmware_findings.md)). Resolved 27 Sep: servo does not move without the main battery, even under a large (0.3 rad) sustained command with the brake latch released (operator confirmed visually) -- servo actuation power is genuinely tied to the main pack, not USB/logic power. See docs/esp32_installed_firmware_findings.md addendum. Still open (blocks Phase C): latch re-arms on session reset, so every command publisher must hold /laksa/brake=false | 2026-09-28T04:14:06Z | human operator ran it; recorded by local Claude Code | [re-run 3](results/A1b_20260928T041406Z.md), [re-run 2](results/A1b_20260928T033612Z.md), [run 1](results/A1b_20260928T031343Z.md) |
| A2 LiDAR (sllidar_ros2) | done — health OK, /scan at a stable 12.8 Hz (device default motor speed, not the nominal 10 Hz the plan mentions; operator accepted 2026-09-28), sane full-360 data, motor confirmed stopped after shutdown (operator checked at the car). Follow-up: configurable scan rate, deferred (see result file) | 2026-09-28T06:58:25Z | local Claude Code | [results/A2_20260928T065825Z.md](results/A2_20260928T065825Z.md) |
| A3 laksa_bringup boot services | done — reboot → agent + health active (NRestarts=0), /diagnostics fresh, link/PCA/IMU OK, VESC WARN (unpowered); 0 publishers on /laksa/command and /laksa/brake. Units fixed first (uros_ws sourcing, ros2 run exec, User=karsha, ordering cycle); udev diffed only | 2026-09-28T04:56:45Z | local Claude Code (operator ran the sudo install + reboot) | [results/A3_20260928T045645Z.md](results/A3_20260928T045645Z.md) |
| A4 sandbox repo | done (this repo) | 2026-09-27 | cloud Claude | — |
| A5 ZED 2i | blocked at step 6 — SDK 5.5.0 (L4T 36.5) installed, ZED_Diagnostic OK (camera + USB bandwidth OK); first still is a real image but badly underexposed (dark room) and depth untrustworthy; operator to re-capture with lights on and inspect. ROS wrapper not started | 2026-09-28T07:49:19Z | local Claude Code (operator ran sudo install) | [checkpoint 2](results/A5_20260928T074919Z.md), [checkpoint 1](results/A5_20260928T073453Z.md) |
| A6 rosbag recording | not started | | | |
