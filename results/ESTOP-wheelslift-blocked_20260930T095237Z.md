# ESTOP wheels-lift — BLOCKED (ESP32 peripheral fault), no W-step run

Run at: 20260930T095237Z (session 09:31–09:53 UTC)
Setup: user chose W1–W5, W7, W8, K9 now (W6 skipped pending Rx polarity flip), with /joy injected by the agent.
Test tooling: notes/estop/wlift.py (20 Hz /joy, 900 eRPM preset, timing from /laksa/state measured_erpm), check.py, sniff.py.

## Timeline (UTC)
- 09:31 wlift.py dry run, battery out: supervisor held brake ("VESC telemetry stale"/"ESP32 state timeout"), as expected.
- 09:32:40 battery connected → the ESP32 USB drops and re-enumerates every 2–17 s (25× in 2.5 min). VESC 0.0 V, telemetry never received.
- ~09:36 battery unplugged. ESP32 gone from USB 09:36:44. Replugged at 09:38 → still resetting every ~3 s on USB power alone.
- Serial boot log (read-only): every cycle "rst:0x7 (TG0WDT_SYS_RST) Saved PC:0x40049abe" → 2nd-stage bootloader prints
  "efuse block revision: v1.4", then hangs until the watchdog fires. The app is never reached (USB ID 303a:1001 = ROM JTAG serial).
- 09:43:07 operator rebooted the Orin, all ESP32 peripherals reconnected → ESP32 boots the app (303a:4001), stable.
  laksa-car.service restarted the stock supervisor (patched file on disk), which came up latched "hardware e-stop link lost".
  The freshness check behaved correctly on a real restart. The bridge was restarted manually (pid 3875).
- 09:48 battery connected again: no ESP32 resets (0 in >3 min), but vesc.telemetry_sequence=0 (never a reply), input_voltage_v=0.0,
  and imu_available=false. VESC LEDs are on and the UART reseated per operator. A USB replug of the ESP32 made no change.
  Earlier sessions: IMU available (A1a), VESC reported 7.1–15 V.

## Verdict
BLOCKED — W1–W8 not run. The ESP32 cannot talk to the VESC or the IMU, and it had a bootloader watchdog loop that began at battery connect.
A shared ESP32-side peripheral/power/wiring fault is suspected; not diagnosed. Not related to the e-stop bridge or the supervisor patch
(neither runs on the ESP32). Needs hands-on inspection (Samyak) before any wheels-lift.
