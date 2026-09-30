# ESTOP — supervisor follows transmitter (bridge as a systemd service)

Run at: 20260930T235347Z (23:47–23:54 UTC). Battery unplugged. ESP32 assumed working (per operator); not verified here.
Bridge: laksa-estop-bridge.service (enabled, active since 23:43:02 UTC, 0 restarts, sole publisher on /laksa/estop_hw).
Monitor: notes/estop/sup_monitor.py. Y injected with notes/estop/press_y.py (no controller connected).

## Output
```
23:47:26.670  SUP latched      True
23:47:26.671  SUP reason       'hardware e-stop link lost'
23:47:26.678  Rx estop_hw      True
23:51:42.128  Rx estop_hw      False
23:52:33.962  SUP latched      False
23:52:33.968  SUP reason       ''
23:52:50.328  Rx estop_hw      True
23:52:50.333  SUP latched      True
23:52:50.334  SUP reason       'hardware emergency stop'
23:53:23.678  Rx estop_hw      False
23:53:34.213  SUP latched      False
23:53:34.215  SUP reason       ''
```
Y presses: 23:52:33.959 and 23:53:34.206 (rising edge).

## Results
| # | Action | Result | Evidence |
|---|---|---|---|
| 1 | Tx → RUN | PASS | Rx false 23:51:42.128; supervisor stayed latched |
| 2 | Y | PASS | unlatched 23:52:33.962 (+3 ms), reason '' |
| 3 | Tx → STOP | PASS | Rx true 23:52:50.328 → latched 'hardware emergency stop' 23:52:50.333 (+5 ms) |
| 4 | Tx → RUN | PASS | Rx false 23:53:23.678; supervisor stayed latched (by design) |
| 5 | Y | PASS | unlatched 23:53:34.213 (+7 ms), reason '' |

## Verdict
PASS 5/5. "Brake always on" was the bridge not running after a reboot, plus a latch that needs Y by design. Both are confirmed.
The supervisor now follows the transmitter. Wheels-lift still depends on the ESP32 hardware issue and the B4 polarity flip.
