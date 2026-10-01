# ESTOP — wheel ramp attempt at RUN (wheels lifted, battery connected)

Run at: 20261001T035626Z (03:56:01–03:56:13 UTC). The user asked for a low-to-higher-speed spin at RUN.
Command: wlift.py --ramp 900,1300,1500 --step-sec 3 (injected /joy throttle 0.5, presets via /laksa/manual_speed_erpm)

## Result
- E-stop NOT latched the whole run (emergency_stop=False, reason '', estop_hw=False). The second Y press at 03:52:14 rearmed it;
  the first press (03:51:47), sent right after the reboot, was not acted on.
- /laksa/command stayed speed=0.000 brake=True the whole time. measured_erpm 0. VESC input_voltage 0.0 V, telemetry_sequence 0.
- The supervisor brakes because the VESC telemetry is stale, not because of the e-stop. imu_available=false as well.
  The ESP32 runs the operator-reflashed firmware (303a:4001, 0 USB disconnects since the 03:42 boot) but hears nothing from the VESC or the IMU.

## Verdict
The motion test could not be done. The blocker is the ESP32 not talking to the VESC/IMU, not the e-stop. The e-brake stop test is still pending.
