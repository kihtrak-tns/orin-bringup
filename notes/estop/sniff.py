#!/usr/bin/env python3
# Read-only: capture printable boot text from the ESP32 USB serial across resets (12 s).
import os, time, re
buf = b""; end = time.time() + 12
while time.time() < end:
    try:
        fd = os.open("/dev/ttyACM0", os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY)
    except OSError:
        time.sleep(0.02); continue
    try:
        while time.time() < end:
            try:
                d = os.read(fd, 4096)
                if d: buf += d
                else: time.sleep(0.005)
            except BlockingIOError:
                time.sleep(0.005)
            except OSError:
                break
    finally:
        os.close(fd)
txt = re.sub(rb"[^\x20-\x7e\n]", b"", buf).decode()
lines = [l for l in txt.splitlines() if re.search(r"rst:|boot:|ESP-ROM|Brownout|brownout|panic|Guru|abort|assert|WDT|reset|Backtrace|E \(", l)]
print(f"captured {len(buf)} bytes"); print("\n".join(lines[-40:]))
