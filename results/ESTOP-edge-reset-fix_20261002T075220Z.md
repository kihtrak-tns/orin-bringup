# Supervisor button edge-reset fix: console REARM works on the first click, repeatable. PASS

Run at: 2026-10-02 07:50:41–07:55:41 UTC. Battery unplugged, actuation_enabled=false, no Xbox, console as stand-in.
Fixes the root cause found in [console REARM diag](ESTOP-console-rearm-diag_20261002T074108Z.md).

## Change (operator, as samyak, after review)
File: `~/laksa/current/src/firmware/esp32-s3/jetson/laksa_bringup/scripts/drive_supervisor_node.py`
(same inode as the install symlink target; release `laksa-car-20261002T0336-21af14f`).
Pre-edit md5 `1824ad8e349503c8b98bb89d4566a496` (matches the tested copy). Backup: `drive_supervisor_node.py.bak-20261002-edge`.
```diff
615a616,622
>             # Forget button states so the next press registers as a fresh
>             # rising edge.  Without this, a console REARM/STOP that sends
>             # a burst of presses and then goes silent leaves the last-seen
>             # state stuck at "pressed", and the next press is ignored.
>             self._previous_b = False
>             self._previous_y = False
>             self._previous_x = False
```
Inside the `/joy` gap block of `_joy_callback` (gap > joy_timeout_sec 0.5 s), which runs before edge evaluation.

## Pre-deploy simulation (patched callback fed 12×50 ms console bursts, on the Orin from /tmp copies)
```
DEPLOYED: rearm#1=True rearm#2=False rearm#3=False stop#1=True stop#2=False
PATCHED:  rearm#1=True rearm#2=True  rearm#3=True  stop#1=True stop#2=True
```
This also confirms that a second console STOP was ignored before the fix.

## Restart
Supervisor only, from `~/laksa/current/ws`, same args, actuation_enabled:=false. PID 75277 / pgid 75276.
Verified: hardware_estop_enabled=True, actuation_enabled=False, 1 publisher on /laksa/command, fix present in running file.

## Output (subscribe-only monitor)
```
07:50:41.083 /laksa/estop_hw -> False
07:52:20.622 /laksa/estop_hw -> True
07:52:20.625 /laksa/emergency_stop -> True
07:52:20.626 /laksa/emergency_stop_reason -> 'hardware emergency stop'
07:52:22.672 /laksa/estop_hw -> False
07:52:26.866 /joy buttons -> Y
07:52:26.867 /laksa/emergency_stop -> False
07:52:26.867 /laksa/emergency_stop_reason -> ''
07:52:38.672 /laksa/estop_hw -> True
07:52:38.674 /laksa/emergency_stop -> True
07:52:38.675 /laksa/emergency_stop_reason -> 'hardware emergency stop'
07:52:40.622 /laksa/estop_hw -> False
07:52:43.068 /laksa/emergency_stop -> False
07:52:43.068 /laksa/emergency_stop_reason -> ''
```
The second REARM has no `/joy buttons` line because the monitor prints only on a button-set *change*, and the
last /joy seen was REARM 1's Y. Only a Y press can clear the latch.

## Verdict: PASS
| Step | Result |
|---|---|
| Tx → latch #1 | 3 ms, reason 'hardware emergency stop' |
| REARM #1 (first click) | cleared 1 ms after Y |
| Tx → latch #2 | 2 ms |
| REARM #2 (first click, no HOLD tap) | cleared, previously always ignored |

The HOLD-tap workaround is no longer needed. Wait >0.5 s between console clicks (the reset fires on a /joy gap > joy_timeout_sec).

## Not yet done
- Console STOP (B) repeat not exercised on hardware (covered by the simulation only).
- The fix lives only in the deployed release folder, so a redeploy reverts it, along with `hardware_estop_enabled: true`.
  Both need to go into the source repo.
- Check B (wheel-lift actuation kill) still pending: battery, operator, and OK for actuation_enabled:=true + ~900 eRPM cap.

## State left
Supervisor rearmed, actuation_enabled=false, battery unplugged.
