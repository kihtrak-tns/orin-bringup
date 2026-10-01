# Wheel spin on blocks — 900 eRPM, 3 s — PASS (wheels turn)

Run at: 20261001T071958Z (07:19:38–07:19:44 UTC). Battery in, Tx RUN, PCA9685 reconnected (initialized/responsive, 0 I2C errors,
steering 100 deg / 1611 us), ESP32 restarted 07:18:42, IMU still unplugged. Command: wlift.py --ramp 900 --step-sec 3.

## Telemetry (/laksa/state, ~3 Hz sampling)
07:19:40.518 /laksa/command speed=0.217 brake=False
40.825 req 900 act 900 meas 6     I_mot 2.92 A
41.132                 meas 25    I_mot 8.62 A
41.433                 meas 468   I_mot 10.23 A
41.746                 meas 1125  I_mot 4.21 A   (overshoot)
42.06–43.32            meas 709–990  I_mot 6.7–7.3 A  duty 0.024–0.028
43.490 throttle released → 43.518 command speed 0, brake False → 44.362 meas 0 (≤0.87 s)
VESC 15.6 V, fault 0 throughout.

## Verdict
PASS: the full chain Orin supervisor → ESP32 → VESC → motor works. The PCA9685 being absent was what blocked drive.
Notes: the settled motor current of ~7 A at ~800 eRPM on blocks is higher than P3 (~2–3 A at ~850); worth checking for drag.
The 1125 eRPM overshoot at spin-up resembles P3's start behaviour. The e-brake stop test is next.
