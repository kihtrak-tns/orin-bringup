# Check A: hardware e-stop → supervisor latch (deployed build, flag re-enabled). 4/5: latch PASS, console REARM FAIL

Run at: 2026-10-02 07:15:37–07:18:37 UTC (Tx press 07:15:45.472)
Follows [ESTOP-hw-live-stack](ESTOP-hw-live-stack_20261002T055244Z.md) (FAIL: supervisor ignored estop_hw).

## Root cause of the 05:52 FAIL
Deployed release `laksa-car-20261002T0336-21af14f`, `drive_supervisor.yaml:33` had
`hardware_estop_enabled: false`, marked "TEMPORARY (owner's request, 2026-10-01)", because the bridge "reported
'stop' continuously and latched the emergency stop at every start". With it false, `_hardware_estop_callback`
returns immediately. The Oct 1 PASSes probably ran a different build: `restart_supervisor.sh` sources
`~/laksa_ws`, which resolves to `~samyak/src/Project_LAKSA` (has the e-stop always on, no flag).

Probable cause of "stop continuously": a failing Tx battery. At 06:33 the Tx was in a ~3.9 s reboot loop
(estop_hw STOP 3.75 s / RUN 0.15 s, repeating). On USB power it was stable (30 s, 601 msgs, all RUN).

## Changes (operator, as samyak)
1. `drive_supervisor.yaml:33` → `hardware_estop_enabled: true` (backup `drive_supervisor.yaml.bak-20261002`).
2. Restarted only drive_supervisor from `~/laksa/current/ws` (NOT `restart_supervisor.sh`, which would load
   `~/laksa_ws` = a different build): same args, `actuation_enabled:=false`. PIDs 43829/43830.
   Verified: hardware_estop_enabled=True, actuation_enabled=False, caps 2485/1000, autonomy on,
   /laksa/command 1 publisher (drive_supervisor), no "IGNORED" warning in the log.
3. No Xbox (unavailable): the web console (`laksa_console`, which publishes /joy) is used as the stand-in:
   REARM = Y pulse, STOP = B pulse, HOLD = operator heartbeat. `require_operator` is unchanged (True).

## Output (subscribe-only monitor)
```
07:15:37.181 watching for 180s
07:15:37.222 /laksa/estop_hw -> False
07:15:45.472 /laksa/estop_hw -> True
07:15:45.473 /laksa/emergency_stop -> True
07:15:45.474 /laksa/emergency_stop_reason -> 'hardware emergency stop'
07:15:47.722 /laksa/estop_hw -> False
```
At 07:16:29: `/laksa/emergency_stop: true`, reason `hardware emergency stop` (still latched).
supervisor.log (times converted to UTC):
```
184: 06:56:01.775 EMERGENCY STOP LATCHED: hardware emergency stop   <- before the 06:59 attempt's window
186: 06:59:51.215 Emergency stop REARMED by Xbox Y; MANUAL mode     <- console REARM, worked
247: 07:15:45.475 EMERGENCY STOP LATCHED: hardware emergency stop   <- this run; no REARMED/rejected after
```
The console log has no rearm, ignoring or heartbeat lines at all, including for the 06:59 rearm that worked.

## Verdict
| # | Check | Result |
|---|---|---|
| 1 | estop_hw → True | PASS 07:15:45.472 |
| 2 | emergency_stop → True within 50 ms | **PASS: 1 ms** |
| 3 | reason "hardware emergency stop" | PASS: +2 ms |
| 4 | stays latched after release | PASS: released 07:15:47.722, still latched at 07:16:29 (>40 s) |
| 5 | REARM clears | **FAIL**: operator clicked console REARM; the supervisor never received a Y edge (no REARMED or rejected line). VESC fault_code 0. Not retried, per the plan. |

The regression is fixed: hardware e-stop → latch is 1 ms, and the latch holds. Console REARM is unreliable:
1 of 2 attempts worked (06:59:51), and the console logs nothing that shows why one was lost.
Earlier attempt (06:59) did not measure the latch: the supervisor was already latched since 06:56:01.

## State left
Supervisor LATCHED (car braked), actuation_enabled=false.

## Blockers for Check B
- VESC unpowered: `/laksa/state` telemetry_sequence 0, input_voltage_v 0.0 (console "Battery 0.0 V").
  Expected, not a fault: the operator confirmed the main battery was unplugged throughout Check A.
  Check B needs the battery connected.
- No manual throttle without the Xbox. Check B would need HOLD TO RUN (autonomy) with a lowered cap.
- A rearm path that works reliably.

## Follow-ups (not done)
- `setup/tonight/restart_supervisor.sh` sources `~/laksa_ws`; it should source `~/laksa/current/ws`.
- The deployed build has no `/laksa/estop_hw` link-loss timeout (the repo version has 0.5 s). If the bridge dies,
  nothing latches.
- The YAML fix sits in a release folder; a redeploy will revert it. Fix it in the source repo and tell the owner who asked for the disable.
