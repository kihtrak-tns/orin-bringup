# Wheel spin on blocks — no motion; ESP32 ignores drive commands while the PCA9685 is absent

Run at: 20261001T071117Z (07:08–07:12 UTC). Battery in, Tx at RUN, the user approved a careful spin. ESP32 has only USB + VESC UART connected.
Y pressed 07:08:14 → supervisor unlatched. Runs: wlift.py --ramp 900,1300 --step-sec 4, then --ramp 900 --step-sec 3 (extra logging).

## Observed
- Supervisor: /laksa/command speed 0.217 → 0.314 m/s, brake=False (it also publishes /laksa/brake = command.brake at 20 Hz).
- ESP32 /laksa/state throughout: command_fresh=True, requested_erpm=0, active_erpm=0, brake_active=True, I_mot -0.01 A, duty 0.
  measured_erpm within ±8 (noise). VESC 15.6 V, fault 0, telemetry fresh.
- /laksa/pca9685/state: initialized=false, responsive=false, consecutive_i2c_errors=2268, last_i2c_error_code=264,
  automatic_recovery_enabled=false, reinitialization_count=0.
- Reference P3 (29 Sep, original firmware, PCA connected): requested 911, active 911, measured ~850, brake_active False.

## Interpretation (not source-confirmed)
The ESP32 receives commands but never requests eRPM. The only known difference from P3 is the unplugged PCA9685 (steering),
so the flashed (handoff-like) firmware most likely refuses or zeros drive when steering cannot be applied. Its exact
source is unknown (cba74e7-dirty has no matching commit); Samyak's branch source differs (no /laksa/brake, different VescState).

## Verdict
No motion. Not an e-stop or supervisor issue. Next: reconnect the PCA9685 (+ servo), reset the ESP32, confirm
pca9685 initialized=true, then re-run the 900 eRPM spin.
