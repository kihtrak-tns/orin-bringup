# Check B: wheel-lift actuation kill via hardware e-stop. Telemetry PASS 3/3 (operator confirmation pending)

Run at: 2026-10-02 08:31:33–08:36:33 UTC. Car on blocks, wheels off the ground, main battery connected (15.0 V).
Deployed release `laksa-car-20261002T0336-21af14f` with `hardware_estop_enabled: true` and the edge-reset fix
([edge fix](ESTOP-edge-reset-fix_20261002T075220Z.md)). The same changes are committed on Project_LAKSA branch `EBrake-Rework`
(bb44146, local, not pushed).

## Setup
- Supervisor restarted by the operator (as samyak) with `actuation_enabled:=true exploration_max_erpm:=900.0`
  (other args unchanged), PID 85216 / pgid 85208. 1 publisher on /laksa/command.
- No Xbox: the console HOLD TO RUN supplied A (1 s hold → FORWARD-PRIORITY LIDAR CRUISE); the learned_driver drove.
- The operator stood behind the car (out of the ZED view), Tx in hand.

## Blockers hit first (same session)
1. 08:13:44 attempt: `Autonomous request rejected: OBSTACLE_SOURCE_STALE: ZED obstacle cloud`. The ZED had logged
   `Point cloud retrieve error: FAILURE` ~14/s since 04:59 UTC (165k lines). Clouds were 3 points at ~1.6 Hz,
   gaps up to 2.5 s (> zed_cloud_timeout_sec 1.5). The car was facing a wall ~1–1.5 ft away (≈ min_depth 0.3 m),
   with voxel_point_cloud on. The ZED was restarted twice: during the first stop `nvargus-daemon` segfaulted
   (8 SEGVs this boot, restart counter 7+). After restart #2, facing open space: 0 retrieve errors, cloud
   4.96 Hz, 567 points (1–5 KB), max gap 0.275 s.
2. 08:29:21 attempt: cruise engaged, but learned_driver logged `Person close ahead; holding` (operator in front
   of the ZED); the command stayed at speed 0. Correct behavior.

## Output (subscribe-only monitor; per-sample /laksa/state lines omitted)
```
08:31:33.948 watching for 300s
08:31:33.950 /laksa/estop_hw -> False
08:31:33.950 /laksa/command speed=0.000 steer=+0.000 brake=True
08:31:55.962 /joy buttons -> A
08:31:55.969 /laksa/command speed=0.000 steer=+0.000 brake=False
08:31:57.018 /laksa/emergency_stop -> False
08:31:57.018 /laksa/emergency_stop_reason -> ''
08:31:57.024 /laksa/command speed=0.000 steer=+0.000 brake=True
08:31:57.166 /laksa/command speed=0.217 steer=+0.016 brake=False
08:31:57.463 /joy buttons -> none
08:32:07.365 /laksa/command speed=0.000 steer=+0.000 brake=False
08:32:07.416 /laksa/command speed=0.217 steer=+0.013 brake=False
08:32:09.275 /laksa/estop_hw -> True
08:32:09.282 /laksa/emergency_stop -> True
08:32:09.284 /laksa/emergency_stop_reason -> 'hardware emergency stop'
08:32:09.326 /laksa/command speed=0.000 steer=+0.000 brake=True
08:32:12.422 /laksa/estop_hw -> False
08:32:19.062 /joy buttons -> Y
08:32:19.064 /laksa/emergency_stop -> False
08:32:19.064 /laksa/emergency_stop_reason -> ''
08:32:19.070 /laksa/command speed=0.000 steer=+0.000 brake=False
08:32:20.120 /laksa/command speed=0.000 steer=+0.000 brake=True
08:32:30.972 /joy buttons -> A
08:32:31.020 /laksa/command speed=0.000 steer=+0.000 brake=False
08:32:32.031 /laksa/command speed=0.000 steer=+0.000 brake=True
08:32:32.118 /laksa/command speed=0.217 steer=+0.016 brake=False
08:32:32.466 /joy buttons -> none
08:32:35.129 /laksa/command speed=0.000 steer=+0.000 brake=False
08:32:35.216 /laksa/command speed=0.217 steer=+0.229 brake=False
08:32:35.716 /laksa/command speed=0.000 steer=+0.000 brake=False
08:32:35.816 /laksa/command speed=0.217 steer=+0.233 brake=False
08:32:36.922 /laksa/estop_hw -> True
08:32:36.923 /laksa/emergency_stop -> True
08:32:36.923 /laksa/emergency_stop_reason -> 'hardware emergency stop'
08:32:36.969 /laksa/command speed=0.000 steer=+0.000 brake=True
08:32:39.524 /laksa/estop_hw -> False
08:32:44.762 /joy buttons -> Y
08:32:44.764 /laksa/emergency_stop -> False
08:32:44.764 /laksa/emergency_stop_reason -> ''
08:32:44.771 /laksa/command speed=0.000 steer=+0.000 brake=False
08:32:45.829 /laksa/command speed=0.000 steer=+0.000 brake=True
08:32:49.063 /joy buttons -> A
08:32:49.121 /laksa/command speed=0.000 steer=+0.000 brake=False
08:32:50.171 /laksa/command speed=0.000 steer=+0.000 brake=True
08:32:50.217 /laksa/command speed=0.000 steer=+0.000 brake=False
08:32:50.575 /joy buttons -> none
08:32:52.168 /laksa/command speed=0.217 steer=-0.061 brake=False
08:32:55.572 /laksa/estop_hw -> True
08:32:55.573 /laksa/emergency_stop -> True
08:32:55.573 /laksa/emergency_stop_reason -> 'hardware emergency stop'
08:32:55.621 /laksa/command speed=0.000 steer=+0.000 brake=True
08:33:01.273 /laksa/estop_hw -> False
08:33:04.281 /joy buttons -> Y
08:33:04.285 /laksa/emergency_stop -> False
08:33:04.288 /laksa/emergency_stop_reason -> ''
08:33:04.318 /laksa/command speed=0.000 steer=+0.000 brake=False
08:33:05.368 /laksa/command speed=0.000 steer=+0.000 brake=True
```

## Timings (from the log; /laksa/state ~10 Hz, so "wheels stopped" is ±100 ms)
| Trial | Tx press (UTC) | eRPM at press | Tx → latch | Tx → cmd speed 0 / brake | Tx → wheels <30 eRPM | Held stopped until REARM |
|---|---|---|---|---|---|---|
| 1 | 08:32:09.275 | 918 | 7 ms | 51 ms | **342 ms** | 9.4 s, brake_active true, no sample ≥30 eRPM |
| 2 | 08:32:36.922 | 951 | 1 ms | 47 ms | **323 ms** | 7.5 s |
| 3 | 08:32:55.572 | 1037 | 1 ms | 49 ms | **521 ms** | 8.2 s (−43 eRPM rebound at +420 ms, then still) |

Each REARM (console, first click) cleared the latch in 2–4 ms. The operator held HOLD through each latch.
The monitor logs every /laksa/state sample with |eRPM| ≥ 30 and every brake_active change; none were logged
between each stop and its REARM.

## Verdict
Telemetry: **PASS 3/3.** Wheels stopped 323–521 ms after the Tx press (limit 1 s). `/laksa/command` was
`speed_mps=0.0 brake=True` within 47–51 ms, and the latch held under HOLD until REARM.

Observation: requested 900 eRPM (0.217 m/s), measured peak 1273 eRPM (+41%) unloaded on blocks.
Check speed overshoot before ground runs.

## Human confirmation needed
Operator: confirm that you saw the wheels stop within ~1 s on all three trials and stay stopped until REARM.

## State left
**actuation_enabled=true**, cruise cap 900, battery connected, supervisor rearmed (not latched).
Recommend restarting with actuation_enabled:=false when the bench session ends.

## Follow-ups
- nvargus-daemon segfaults (8 this boot): investigate before relying on the ZED; a reboot may be needed.
- ZED point cloud fails with a wall inside ~min_depth: consider whether the driver/supervisor should treat a
  persistently near-empty cloud differently, or park facing open space.
- Push `EBrake-Rework` and build a package from it (both fixes are lost on redeploy until then).
