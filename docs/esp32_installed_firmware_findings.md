# LAKSA ESP32 + VESC – installed firmware and configuration findings (26 Sep 2026)

Evidence: verified 16 MB flash backup of the car's ESP32-S3 (ROM download mode, `verify_flash` OK), its app descriptor and strings; VESC firmware query and motor/app configuration XML read with VESC Tool 7.00 CLI (read-only); first live micro-ROS contact from the new Orin; all compared against the public repo Project-LAKSA/project_laksa (all branches). Strings show what is compiled in, not proven runtime behaviour.

## ESP32: identity of the flashed build
- ESP-IDF v6.0.1, CMake project `sample_project`, single `factory` app (no OTA), built **5 Sep 2026 16:30:57**.
- App version `cba74e7-dirty`: built on commit `cba74e7` (branch `add_micro_ros_support`, 10 Aug) **with uncommitted changes**. ELF SHA-256 `fb31999e69da97f8f99459eee75291f84b673eb0df58d0282d5b41805030a17d`.
- **No commit in the repo matches it.** It mixes features found only on `autonomy-handoff-2026-09-02` (DriveCommand `brake`, `/laksa/brake`, `brake_active`, "Drive command timeout; braking and centering steering") and only on `production/laksa-mainline` (`Pca9685State`, `/laksa/pca9685/state`, `automatic_recovery_enabled`). The flash backup is the only exact copy.
- **No web dashboard in the flashed build**: `/api/motor`, `/api/steering`, `/api/state`, `httpd` and the Wi-Fi SSID are all absent from the strings.

## ESP32: interface (confirmed live from the Orin, 26 Sep, battery unplugged)
- micro-ROS over TinyUSB CDC "LAKSA micro-ROS CDC" (USB 303a:4001, serial LAKSA-ESP32S3-001) → `/dev/laksa_microros` via udev rule; agent `micro_ros_agent serial --dev /dev/laksa_microros -b 115200` establishes a session.
- Node `/laksa_esp32`. Topics: `/laksa/brake` [std_msgs/Bool], `/laksa/command` [laksa_interfaces/DriveCommand, ESP32 subscribes, RELIABLE, KEEP_LAST 1], `/laksa/imu/data` [sensor_msgs/Imu, ~41 Hz, frame `imu_link`], `/laksa/imu/mag` [sensor_msgs/MagneticField], `/laksa/pca9685/state` [Pca9685State], `/laksa/state` [VehicleState], `/laksa/vesc/state` [VescState]. Services: `/laksa/get_state` [GetVehicleState], `/laksa/set_drive_command` [SetDriveCommand].
- Field names in firmware strings: DriveCommand = speed_mps, steering_angle_rad, brake (handoff); VescState = handoff layout (brake_active, telemetry_sequence, telemetry_age_ms); Pca9685State = production layout (`initialized` field to be confirmed at runtime); VehicleState and services identical on both branches.
- Orin package `laksa_interfaces` assembled accordingly (handoff 4787d05 for DriveCommand/VescState, production 1f0db4f for the rest), with a listen-only checker (`laksa_readonly_check.py`) that decodes raw bytes and confirms the layout using known values (I2C 0x40, 50 Hz, channel 7, IMU orientation). Humble does not check type hashes, so a mismatch would silently mis-decode: no command publisher until the checker reports ALL MATCH.

## Actuation architecture
- Traction: ESP32 → VESC over **UART** (SolidGeek VescUart, RPM commands). Repo values: UART2, TX GPIO17, RX GPIO18, 115200 baud, max |ERPM| 900, command timeout 500 ms.
- Steering: ESP32 → PCA9685 over I2C (SDA GPIO8, SCL GPIO9, addr 0x40, 50 Hz) → **channel 7** → Traxxas 2056. Center 100°, limits 63°/139°.
- IMU: BNO08x over **SPI** (SCK 5, MOSI 6, MISO 7, CS 4, INT 15, RST 16). Working on USB power alone.
- Compiled-in safety: drive-command timeout (500 ms) → brake + center steering; micro-ROS agent disconnect → stop actuators.

## VESC (Flipsky Mini FSESC6.7 Pro)
- Firmware **6.06 `no_hw_limits`**, hardware "60". Configured limits are the only protection.
- **App: UART only** (`app_to_use = 3`), 115200 baud (matches firmware). PPM input unused, so the PCA9685→VESC receiver lead has no throttle function (its 5 V pin remains a power-rail question).
- `kill_sw_mode = 0`: the wired stop does not act through the VESC.
- **UART timeout 1000 ms, timeout brake current 0**: ESP32 silence → motor coasts after 1 s.
- Motor: FOC sensorless, detected (R 16.5 mΩ, L 8.83 µH, λ 0.779 mWb); `si_motor_poles = 4` (**2 pole pairs**), wheel 0.105 m, gear 1.
- Limits: motor +45/−20 A, battery +99/−60 A, abs 150 A, **ERPM ±100 000**, duty 0.95, cutoff 13.6→12.8 V (fits 4S), temps 85–100 °C. `si_battery_cells = 6` is display-only.

## Issues to resolve (none changed yet)
1. **Pole-pair mismatch**: firmware uses 7 pole pairs, VESC says 2 → commanded motor speed ~3.5× intended; reported speed ~3.5× low. Gear/wheel values need real drivetrain numbers.
2. **No ERPM limit** with a 2S-class motor on 4S and `no_hw_limits`: set `l_max_erpm` once the motor rating is known; firmware 900 ERPM cap is the only limit meanwhile.
3. **Loss-of-ESP32**: consider VESC UART timeout ~300 ms with a small brake current.
4. **Low-speed sensorless control** at ≤900 ERPM may be rough (unproven).
5. Public repo `esp32_config.h` contains a Wi-Fi SSID/password: rotate and remove.
6. Keep `CONFIG_LAKSA_WEB_DASHBOARD` disabled in future builds.

## Open items
- Run `laksa_readonly_check.py` (Pca9685State `initialized`, VescState/VehicleState layout). **Done** (A1a, 26-27 Sep 2026, 97/97 and 90/90 raw==typed — see repo `results/A1a_20260928T022525Z.md`).
- Barrel-plug voltages/polarity (Jetson, LiDAR) – needs a multimeter; Orin stays on its wall adapter until measured.
- Motor cannot currently be unplugged; traction isolation = battery unplugged, or stand + no command publisher.
- ~~Unpowered continuity of GPIO17/18 ↔ VESC COMM, GPIO8/9 ↔ PCA SDA/SCL, PCA ch7 ↔ servo signal.~~ **PCA ch7 ↔ servo signal: resolved 27 Sep 2026** — see addendum below. The PCA9685 itself answers I2C and updates its output register on logic power alone, but the servo does not physically move: confirmed with a large (0.3 rad, ~half-range) sustained command and the brake latch released, operator watching the linkage directly, no movement observed. GPIO17/18 ↔ VESC COMM and GPIO8/9 ↔ PCA SDA/SCL continuity remain open (no reason to suspect an issue, just not separately verified).
- How the RJ45 wired stop actually interrupts propulsion.

## Addendum (27 Sep 2026): root cause of A1b's brake/steering failure — boot-default brake latch, never released

**Context.** A1b (`drive_command_loopback_test`) failed twice: `steering_target_rad` never echoed a commanded nonzero angle, `pca9685.steering_command_deg` never left the 100° center, and `vesc.brake_active` stayed `true` even under an explicit `brake=False` command. `vesc.command_fresh` correctly tracked publish/stop, ruling out a dead transport.

**Source-level finding.** Cloned the public `Project-LAKSA/project_laksa` repo and read `firmware/esp32-s3/src/micro_ros_bridge.c` and `vesc_uart.cpp` on branch `autonomy-handoff-2026-09-02` (commit `4787d05`, the same commit the doc above already cites as the source for the flashed `DriveCommand`/`VescState` layout). This branch's `micro_ros_bridge.c` contains the exact log string "Drive command timeout; braking and centering steering" that the flash-image string dump shows in the running build, which is strong (not certain — the flash is `cba74e7-dirty`, i.e. this code plus uncommitted local edits) evidence this is the real donor source.

Mechanism, as written in that source:
- `bridge.brake_requested` starts `true` at boot (`micro_ros_bridge_start()`), and is reset to `true` again on **every** micro-ROS agent disconnect/reconnect (`destroy_entities()`, which also calls `apply_actuator_failsafe()`).
- The only way `brake_requested` ever becomes `false` is a message on `/laksa/brake` (`std_msgs/Bool`) with `data=false` (`brake_callback`). Nothing in this bring-up has ever published to that topic.
- `command_callback` computes the effective brake as `bridge.brake_requested || command->brake` before calling `apply_drive_command` — so the persistent latch overrides whatever `DriveCommand.brake` says.
- `apply_drive_command` forces steering to `0.0f` (center) whenever the effective brake is true, independent of the commanded `steering_angle_rad`.
- Independently, `vesc_uart.cpp`'s control loop computes `brake_active = !command_fresh || vesc->brake_requested || (has_telemetry && fault_code != 0)` — so `brake_active` is also forced true by the same latch, regardless of `DriveCommand.brake`, and is unaffected by VESC power/telemetry state (that term only matters when telemetry is actually being received).

**This explains every observed symptom** and rules out a DriveCommand transport/layout bug (hypothesis b: the decode is fine) and a VESC-power-tied failsafe (hypothesis a: nothing here depends on VESC telemetry being present). It also means **the still-open micro-ROS session-churn instability re-arms this latch on every drop** — a one-time unlatch will not hold across a session reset; whatever resolves this needs to either republish on reconnect or fix the firmware's persistence.

**Live confirmation (27 Sep 2026, A1b re-run 3, PASS 6/6).** Held `/laksa/brake=false` continuously alongside `/laksa/command` during A1b's command-publishing steps. Result: `steering_target_rad` 0.1 → 0.0981, PCA9685 servo command 100°→94° (1611→1544 µs), `brake_active` produced a real False→True transition on `brake=True`. Confirms the latch is the root cause, not (a) or (b). See `results/A1b_20260928T041406Z.md` in the repo.

**Physical-motion follow-up (27 Sep 2026, resolved).** With A1b closed, the open question of whether the servo has power independent of the main battery was checked directly: with the battery still unplugged, the brake latch released, and the operator watching the steering linkage (not just listening), a sustained large command (`steering_angle_rad=0.3`, ~half the mechanical range) produced **no physical movement**. The PCA9685 register did update (confirmed via `/laksa/pca9685/state` in A1b's own run), but the servo itself never moved. **Conclusion: the servo's actuation power is genuinely tied to the main battery, independent of USB/ESP32 logic power.** This confirms — empirically, not just by design intent — that Phase A's battery-unplugged testing has been inert on the steering actuator the whole time, and that Phase B's "power-up steering" remains the correct place to first test steering under real actuation power, on a stand with wheels clear, as originally planned.

## Addendum (28 Sep 2026): source-level mechanism for the session-churn — a 100 ms/500 ms/1-attempt liveness check with no slack

**Context.** The churn investigation (`results/churn_experiment_20260928T132216Z.md`) established that the session churn is present at rest (~23 resets/hour), is not caused by CPU load (100% on all 6 cores made no measurable difference), and roughly doubles when the LiDAR and ZED are running — but hadn't yet identified what specifically triggers any *one* reset. Re-read `micro_ros_bridge.c` (same donor commit, `4787d05`, already cited above) with exactly that question.

**Source-level finding.** The firmware's agent-liveness check (`micro_ros_bridge.c:33-39`, task loop at `:549-617`):
```
#define MICRO_ROS_AGENT_PING_PERIOD_MS   500   // ping the agent every 500 ms
#define MICRO_ROS_AGENT_PING_TIMEOUT_MS  100   // give it 100 ms to answer
#define MICRO_ROS_AGENT_PING_ATTEMPTS      1   // exactly one try, no retry
```
While `BRIDGE_AGENT_CONNECTED`, a single failed ping (`rmw_uros_ping_agent()` not OK inside 100 ms) transitions straight to `BRIDGE_AGENT_DISCONNECTED`, which calls `destroy_entities()` — the exact same call that re-arms the boot-default brake latch (see the 27 Sep addendum above) — and returns to `BRIDGE_WAITING_FOR_AGENT` to rebuild the session from nothing.

**There is zero slack in this design.** Any single USB-serial round trip (agent ↔ ESP32, roughly a hundred bytes) that happens to take longer than 100 ms, for any reason, tears down and rebuilds the entire session. At the time this was found, the leading environmental hypothesis was USB autosuspend — since superseded by direct measurement, see the addendum immediately below.

**On whether a churn event is a real MCU reboot (a caution raised independently during review, worth recording exactly as flagged): do not infer a reboot from the session/`client_key` changing.** Checked directly: there is no `esp_restart()` or equivalent anywhere in the `BRIDGE_AGENT_DISCONNECTED` → `destroy_entities()` → `BRIDGE_WAITING_FOR_AGENT` path — by source-level design, a churn event is a software session-layer teardown/rebuild, not a hardware reset. However, this is the code's *intent*, not yet an independent runtime confirmation: grepped the whole `firmware/esp32-s3` tree for `reset_reason`/`boot_count`/`uptime`/`reboot` and found nothing — the current telemetry stream has no field that could catch an unrelated brownout/watchdog reset if one occurred for a different reason. The only way to check directly would be capturing the ESP32's own serial console log (its `ESP_LOGW`/`ESP_LOGE` output, e.g. "Agent disconnected; stopping actuators") during a live churn event, which is not currently being captured. Not yet done.

## Addendum (28 Sep 2026, later): churn mechanism measured directly — the host side is not the problem

**Context.** Followed up the ping-timeout finding above with direct measurement: kernel-log correlation of every reset since boot plus a live capture window, and `-v6` (verbose XRCE-DDS) logging on the micro-ROS agent to see the actual ping/reply timing around real reset events. Full data: `results/churn_mechanism_20260928T154208Z.md` in the repo.

**Kernel correlation.** Across all 123 resets recorded since boot, plus a 17-minute live `dmesg -wT`/`journalctl -k -f` capture running in parallel with the agent log (which happened to catch a quiet spell with no resets), the kernel logged **nothing** on the ESP32's USB path at any reset. No autosuspend/resume messages, no URB errors, nothing.

**Autosuspend ruled out by observation, not intervention.** Checked `/sys/bus/usb/devices/*/power/control` for the ESP32's device: it is set to `on` and has never suspended. So the autosuspend hypothesis from the addendum above is ruled out directly — not because disabling it changed anything, but because it was already off the whole time.

**The decisive measurement (`-v6` agent logging, 4 captured reset events).** Every reset has the same shape: the ESP32's ping reaches the agent, the agent replies in 0.36–0.42 ms, and about **107 ms** later — matching the 100 ms timeout constant exactly — the ESP32 gives up and starts reconnecting. Aggregate stats across 646 pings: median reply latency 0.38 ms, p99 0.72 ms. The agent, the kernel, USB power management, and CPU load are now all ruled out as the source of the delay — **the host side is consistently fast.**

**What's left.** The reply is either lost or delayed on the final leg to the ESP32, or it arrives but the ESP32 doesn't process it in time — a receive-buffer overflow while it's busy streaming its own sensor data, a framing error that causes a silent discard, or an internal scheduling issue in the firmware's own USB CDC handling. Telling these apart needs instrumentation inside the ESP32 firmware itself; not yet done.

**Cost per event.** After a teardown, the agent deletes the old session's ~20 DDS entities at roughly 100 ms each before a new session can start — so each churn event costs on the order of 1-2+ seconds of dead time, not just the 107 ms detection window. Relevant to any future command-publisher design: the brake-latch re-arm (27 Sep addendum) needs to survive this whole window, not just the initial timeout.

**Candidate fix (firmware, not yet done).** Since the host reply is reliably back within ~1 ms, the firmware's liveness check has essentially no reason to be this strict. Loosening `MICRO_ROS_AGENT_PING_TIMEOUT_MS` and/or `MICRO_ROS_AGENT_PING_ATTEMPTS` (e.g. requiring several consecutive failures, or a longer per-attempt window) should eliminate most resets without hiding a genuine disconnect — and the actuator-level safety (the independent 500 ms drive-command timeout → brake + center) is unaffected either way, since it doesn't depend on this ping. This is a firmware rebuild-and-reflash change, though, which is a bigger and more deliberate step than anything done so far (see Phase D's firmware-rebuild discussion in the bring-up plan) — not pursued yet, pending the device-isolation follow-up (Part 2, in progress) and a deliberate plan for a safe reflash/rollback.
