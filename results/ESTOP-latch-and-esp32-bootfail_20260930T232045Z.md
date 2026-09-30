# ESTOP "brake always on" + ESP32 boot failure — 30 Sep evening

Run at: 20260930T232045Z (23:16–23:21 UTC). The Orin booted 23:09 UTC.

## 1. Brake always on (e-stop side)
- Root cause: the bridge is not a service. After every Orin reboot nothing publishes /laksa/estop_hw, so the patched
  supervisor stays latched "hardware e-stop link lost" whatever pin 15 does (verified: 0 publishers at 23:16).
- Also by design: a latch never clears on RUN. Only an Xbox Y rising edge clears it, and no controller is present (/dev/input/js* absent).
- Fix prepared: notes/estop/laksa-estop-bridge.service (User=karsha, Group=gpio, Restart=always, SIGTERM → final STOP),
  staged at dev-orin:~/estop_bridge/. systemd-analyze verify: clean. Installing it needs sudo. The bridge was started manually for now (pid 6687).

## 2. ESP32 not booting (blocks VESC/IMU/actuation)
- USB 303a:1001 (ROM), resets every ~3 s since boot (138 disconnects by 23:16).
- Boot log, every cycle: `E (31) boot_comm: mismatch chip ID, expected 9, found 65535`, then `rst:0x3 (RTC_SW_SYS_RST)`.
  The 2nd-stage bootloader reads 0xFFFF from flash once it switches to its own flash config (DIO 80 MHz per the header at 0x0).
- Read-only esptool/espefuse checks:
  - The flash answers (mfr 0x68, dev 0x4018, 16 MB). Header at 0x0 is valid (chip id 9). Partition table: nvs, phy_init, factory@0x10000.
    App header at 0x10000 is valid (chip id 9, "cba74e7-dirty", the same installed build). Flash content is intact.
  - eFuse VDD_SPI_FORCE=1, VDD_SPI_TIEH=1 → flash supply is locked to VDD3P3_RTC_IO (3.3 V). GPIO45 strapping is not the cause.
  - Firmware pins (src/esp32_config.h): I2C 8/9, SPI 5/6/7, BNO CS 4, INT 15, RST 16, VESC UART TX 17/RX 18. No flash/PSRAM (26–37) or strap pins.
- Conclusion: flash reads fail at boot speed although the content is fine → electrical (module 3V3 sag/short, or an external load
  on the flash/PSRAM lines through a miswire). Not caused by e-stop software, which does not run on the ESP32. Needs hands-on checks.

## Verdict
E-stop: root cause found; the fix (systemd unit) awaits sudo install. ESP32: BLOCKED on a hardware check. No firmware writes made.
