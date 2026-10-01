# Why the car won't move — hypothesis A/B/C/D investigation (read-only)

Run at: 20261001T040201Z (04:01 UTC). Nothing restarted, no wiring touched, no sudo, the serial port was not read (the agent holds it).

## Evidence
1. Supervisor: /laksa/emergency_stop = false, reason = '' (rearmed by Y at 03:52:14; earlier 5/5 Tx-follow test at 23:51–23:54).
   /laksa/mode does not exist. No laksa-drive-supervisor unit; the supervisor runs under laksa-car.service (as samyak).
2. Bridge: laksa-estop-bridge.service active (PID 988). /laksa/estop_hw at 19.99 Hz (48–52 ms), data:false (RUN).
4. /laksa/state at 7.94 Hz: imu_available=false; vesc.command_fresh=true; brake_active=true; telemetry_fresh=false;
   telemetry_sequence=0; telemetry_age_ms=4294967295; input_voltage_v=0.0; fault_code=0. /laksa/vesc/state shows the same (1 publisher).
5. ESP32 = 303a:4001 "LAKSA micro-ROS CDC" on usb 1-2.3 (behind the on-board hub), 0 USB disconnects this boot. Agent active.
   /dev/ttyUSB0 is the LiDAR's CP210x.
6. No vesc_tool on the Orin. VESC LEDs on, per operator (earlier).

## Conclusion: D
The ESP32 is alive and talking to the Orin (state at 8 Hz, command_fresh=true) but has NEVER received a VESC reply
(telemetry_sequence=0, 0.0 V). The IMU is also absent. A is ruled out (bridge 20 Hz; mirroring verified 23:51–23:54).
B is ruled out (fault_code 0, not latched). C is ruled out (ESP32 boots, 0 disconnects).
Chain: supervisor not latched → its "VESC telemetry stale" gate commands brake=True → ESP32 reports brake_active=true
(probably what shows as "brake" on the console) → no motion.
Physical action needed (operator/Samyak): the ESP32↔VESC UART path (TX17/RX18, common GND, VESC UART app/baud) and the
IMU SPI/power; 5VIN measured 0.5–1.0 V earlier. Also check that the reflashed firmware is the build that matches this wiring.
Orin-side software fixes cannot make it move: bypassing the telemetry gate would be loosening a safety check.
Note: the ESP32 is back behind the on-board USB hub (1-2.3), which caused session churn on 28 Sep.
