# E-brake test on blocks — W2 (stop) + W3 (stays latched) — PASS

Run at: 20261001T073753Z (07:24:14–07:25:02 UTC). Battery in, wheels lifted, PCA9685 connected, IMU unplugged.
Bridge: laksa-estop-bridge.service (debounce 5, run_is_high=True). Supervisor: Samyak's stack (patched, require_operator default).
Y pressed 07:24:01.647 → unlatched. Command: wlift.py --ramp 900 --step-sec 45 (900 eRPM, throttle held through the latch).
Operator set the transmitter to STOP ~5 s after seeing the wheels spin. (The first attempt at 07:20 was invalid: STOP arrived 13 s after the throttle ended.)

## Log excerpt (ebrake_run2.log)
```
  07:24:14.884 estop_hw = False
  07:24:14.885 emergency_stop = False
  07:24:14.886 reason = ''
  07:24:14.886 /laksa/command speed=0.000 brake=True
  07:24:14.909 measured_erpm = 0  req=0 act=0 cmd_fresh=True brake=True dir_pend=False I_mot=-0.02 A I_in=0.00 A duty=0.000 (fault 0, 15.6 V)
  07:24:14.929 /laksa/command speed=0.000 brake=False
  07:24:15.973 measured_erpm = 0  req=0 act=0 cmd_fresh=True brake=False dir_pend=False I_mot=-0.02 A I_in=0.00 A duty=0.000 (fault 0, 15.6 V)
START estop=False reason='' hw=False erpm=0.0
  07:24:16.385 THROTTLE 0.5 for 45 s
  07:24:16.385 manual_speed_erpm preset -> 900
  07:24:16.420 /laksa/command speed=0.217 brake=False
  07:24:16.480 measured_erpm = 0  req=900 act=900 cmd_fresh=True brake=False dir_pend=False I_mot=-0.01 A I_in=0.00 A duty=0.000 (fault 0, 15.6 V)
  07:24:21.200 measured_erpm = 834  req=900 act=900 cmd_fresh=True brake=False dir_pend=False I_mot=3.36 A I_in=0.04 A duty=0.021 (fault 0, 15.6 V)
  07:24:21.515 measured_erpm = 943  req=900 act=900 cmd_fresh=True brake=False dir_pend=False I_mot=3.12 A I_in=0.04 A duty=0.018 (fault 0, 15.6 V)
  07:24:21.578 estop_hw = True
  07:24:21.582 emergency_stop = True
  07:24:21.583 reason = 'hardware emergency stop'
  07:24:21.623 /laksa/command speed=0.000 brake=True
  07:24:21.838 measured_erpm = -23  req=0 act=0 cmd_fresh=True brake=True dir_pend=False I_mot=1.05 A I_in=0.01 A duty=0.000 (fault 0, 15.6 V)
  07:24:21.838 WHEELS STOPPED (measured_erpm -23)
  07:24:22.143 measured_erpm = 0  req=0 act=0 cmd_fresh=True brake=True dir_pend=False I_mot=-0.01 A I_in=0.00 A duty=0.000 (fault 0, 15.6 V)
  07:24:22.464 measured_erpm = 0  req=0 act=0 cmd_fresh=True brake=True dir_pend=False I_mot=-0.01 A I_in=0.00 A duty=0.000 (fault 0, 15.6 V)
  07:24:22.776 measured_erpm = 0  req=0 act=0 cmd_fresh=True brake=True dir_pend=False I_mot=-0.01 A I_in=0.00 A duty=0.000 (fault 0, 15.6 V)
  07:24:23.075 measured_erpm = 0  req=0 act=0 cmd_fresh=True brake=True dir_pend=False I_mot=-0.01 A I_in=0.00 A duty=0.000 (fault 0, 15.6 V)
  07:24:23.380 measured_erpm = 0  req=0 act=0 cmd_fresh=True brake=True dir_pend=False I_mot=-0.01 A I_in=0.00 A duty=0.000 (fault 0, 15.6 V)
  07:24:23.697 measured_erpm = 0  req=0 act=0 cmd_fresh=True brake=True dir_pend=False I_mot=-0.01 A I_in=0.00 A duty=0.000 (fault 0, 15.6 V)
  07:25:02.471 measured_erpm = 0  req=0 act=0 cmd_fresh=True brake=True dir_pend=False I_mot=-0.01 A I_in=0.00 A duty=0.000 (fault 0, 15.6 V)
RESULT {'trigger': '07:24:21.578', 'latch': '07:24:21.582', 'cmd_stop': '07:24:21.623', 'wheels_stop': '07:24:21.838', 'peak_erpm': 1061.0}
  latch       : 4 ms after trigger
  cmd_stop    : 45 ms after trigger
  wheels_stop : 260 ms after trigger
```

## Results
| Check | Result | Measured |
|---|---|---|
| Spinning before STOP | yes | 834–943 eRPM at 07:24:20.9–21.5, I_mot ~3.2 A |
| Rx STOP → supervisor latched | PASS | 4 ms (07:24:21.578 → .582), reason 'hardware emergency stop' |
| → /laksa/command brake | PASS | 45 ms (speed 0.000, brake=True) |
| → wheels stopped (<50 eRPM) | **PASS** | **260 ms** (−23 at .838; 0 from 07:24:22.143) — limit 1 s |
| W3: refuses throttle while latched | PASS | 126 samples 07:24:22.1–07:25:01.4: max abs(eRPM) 1, requested 0, brake_active true throughout, while /joy held throttle 0.5 |

## Notes
- The stop time is measured from the bridge's /laksa/estop_hw true. The transmitter→receiver LoRa delay and the 5-read debounce are not
  included (the debounce applies only to RUN; STOP is immediate). Measure the end-to-end time on video if needed.
- Not tested: W6 (signal wire pulled; B4 polarity flip still pending), W7 (receiver power loss), W8/kill -9 under motion.
- The Orin was unreachable after the test and came back freshly rebooted (uptime 54 s; its clock was not yet synced). Cause not established: ask the operator whether it was power-cycled.
