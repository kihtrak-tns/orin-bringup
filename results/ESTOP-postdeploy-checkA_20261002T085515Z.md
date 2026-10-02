# Post-deploy Check A on release laksa-car-20261002T0839-bb44146 (EBrake-Rework). PASS

Run at: 2026-10-02 08:52–08:57 UTC, after reboot. Car on blocks, battery unplugged (VESC 0.0 V).
Release built from Project_LAKSA `EBrake-Rework` bb44146 and installed by laksa-deploy at boot
(build OK, tests 67+8+2 OK). The supervisor (pid 5166, auto mode: actuation_enabled=true, autonomy on, cruise 2485)
runs `releases/laksa-car-20261002T0839-bb44146/.../drive_supervisor_node.py` with the edge-reset fix;
`hardware_estop_enabled=true`. 1 publisher on /laksa/command.

## Attempt 1 (08:52:35): REARM did not reach the car. Cause: tooling, not the car
Tx presses latched (08:52:48.923 → 08:52:48.925, 2 ms); the second press landed while still latched (no change).
No /joy messages at all: the WSL `ssh -L 8095` tunnel to the console died with the reboot. The console was still
running on the Orin (127.0.0.1:8095). The tunnel was reopened and the browser reloaded.
```
08:52:35.076 watching for 240s
08:52:35.078 /laksa/estop_hw -> False
08:52:35.079 /laksa/command speed=0.000 steer=+0.000 brake=True
08:52:48.923 /laksa/estop_hw -> True
08:52:48.925 /laksa/emergency_stop -> True
08:52:48.927 /laksa/emergency_stop_reason -> 'hardware emergency stop'
08:52:50.670 /laksa/estop_hw -> False
08:53:02.870 /laksa/estop_hw -> True
08:53:05.120 /laksa/estop_hw -> False
08:55:07.576 /joy buttons -> Y
08:55:07.582 /laksa/emergency_stop -> False
08:55:07.583 /laksa/emergency_stop_reason -> ''
08:55:15.621 /laksa/estop_hw -> True
08:55:15.623 /laksa/emergency_stop -> True
08:55:15.625 /laksa/emergency_stop_reason -> 'hardware emergency stop'
08:55:17.020 /laksa/estop_hw -> False
08:55:19.448 /laksa/emergency_stop -> False
08:55:19.449 /laksa/emergency_stop_reason -> ''
08:55:23.420 /laksa/estop_hw -> True
08:55:23.432 /laksa/emergency_stop -> True
08:55:23.433 /laksa/emergency_stop_reason -> 'hardware emergency stop'
08:55:25.170 /laksa/estop_hw -> False
08:55:29.629 /laksa/emergency_stop -> False
08:55:29.631 /laksa/emergency_stop_reason -> ''
```

## Attempt 2 (08:53:51)
```
08:53:51.295 watching for 240s
08:53:51.298 /laksa/estop_hw -> False
08:53:51.298 /laksa/command speed=0.000 steer=+0.000 brake=True
08:55:07.575 /joy buttons -> Y
08:55:07.581 /laksa/emergency_stop -> False
08:55:07.583 /laksa/emergency_stop_reason -> ''
08:55:15.620 /laksa/estop_hw -> True
08:55:15.623 /laksa/emergency_stop -> True
08:55:15.625 /laksa/emergency_stop_reason -> 'hardware emergency stop'
08:55:17.020 /laksa/estop_hw -> False
08:55:19.448 /laksa/emergency_stop -> False
08:55:19.449 /laksa/emergency_stop_reason -> ''
08:55:23.420 /laksa/estop_hw -> True
08:55:23.432 /laksa/emergency_stop -> True
08:55:23.433 /laksa/emergency_stop_reason -> 'hardware emergency stop'
08:55:25.170 /laksa/estop_hw -> False
08:55:29.629 /laksa/emergency_stop -> False
08:55:29.631 /laksa/emergency_stop_reason -> ''
```

## Verdict: PASS
| Step | Result |
|---|---|
| REARM (attempt-1 latch) | cleared 6 ms after Y |
| Tx → latch #1 | 3 ms, 'hardware emergency stop' |
| REARM #1 | first click |
| Tx → latch #2 | 12 ms |
| REARM #2 | first click, no HOLD tap |

The deployed package keeps both fixes across reboots.

## Notes
- After any Orin reboot, reopen the console tunnel (`ssh -N -L 8095:127.0.0.1:8095 dev-orin`) and reload the page.
- nvargus-daemon: 1 SEGV already this boot (8 last boot). ZED cloud healthy now (5.0 Hz, 1411 pts, 0 errors).
- Auto mode starts with actuation ON at 2485 eRPM. Decide on this default before ground runs.

## State left
Supervisor not latched, actuation_enabled=true (auto mode), battery unplugged, car on blocks.
