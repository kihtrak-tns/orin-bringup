#!/usr/bin/env python3
"""Read-only VESC probe over the VESC's own USB port.

Sends only COMM_FW_VERSION (0) and COMM_GET_VALUES (4). No configuration
commands are ever sent. Skips the ESP32's port (/dev/laksa_microros).
Usage: vesc_probe.py [/dev/ttyACMx] [--count N]
"""
import glob, os, struct, sys, time
import serial

COMM_FW_VERSION, COMM_GET_VALUES = 0, 4
FAULTS = {0: "NONE", 1: "OVER_VOLTAGE", 2: "UNDER_VOLTAGE", 3: "DRV", 4: "ABS_OVER_CURRENT",
          5: "OVER_TEMP_FET", 6: "OVER_TEMP_MOTOR"}


def crc16(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def frame(payload):
    return bytes([2, len(payload)]) + payload + struct.pack(">H", crc16(payload)) + b"\x03"


def request(port, cmd, timeout=1.0):
    port.reset_input_buffer()
    port.write(frame(bytes([cmd])))
    buf, end = b"", time.time() + timeout
    while time.time() < end:
        buf += port.read(512)
        i = buf.find(b"\x02")
        if i >= 0 and len(buf) >= i + 2:
            n = buf[i + 1]
            if len(buf) >= i + 2 + n + 3:
                payload = buf[i + 2:i + 2 + n]
                if struct.unpack(">H", buf[i + 2 + n:i + 4 + n])[0] != crc16(payload):
                    return None, "CRC mismatch"
                if payload and payload[0] == cmd:
                    return payload[1:], None
                buf = buf[i + 2 + n + 3:]
    return None, f"no reply in {timeout:.1f} s ({len(buf)} bytes seen)"


def find_port():
    esp = os.path.realpath("/dev/laksa_microros") if os.path.exists("/dev/laksa_microros") else None
    for p in sorted(glob.glob("/dev/ttyACM*")):
        if os.path.realpath(p) != esp:
            return p
    return None


def main():
    args = sys.argv[1:]
    count = 3
    if "--count" in args:
        count = int(args[args.index("--count") + 1])
    dev = next((a for a in args if a.startswith("/dev/")), None) or find_port()
    if not dev:
        print("No VESC USB port found (only the ESP32's port is present).")
        sys.exit(2)
    for link in glob.glob("/dev/serial/by-id/*"):
        if os.path.realpath(link) == os.path.realpath(dev):
            print("device:", dev, "->", os.path.basename(link))
    port = serial.Serial(dev, 115200, timeout=0.05)
    time.sleep(0.2)
    p, err = request(port, COMM_FW_VERSION)
    if err:
        print("FW_VERSION:", err)
    else:
        name = p[2:].split(b"\x00")[0].decode(errors="replace")
        print(f"FW_VERSION: {p[0]}.{p[1]:02d}  hw='{name}'")
    for _ in range(count):
        p, err = request(port, COMM_GET_VALUES)
        if err:
            print("GET_VALUES:", err)
        else:
            t_fet, t_mot = struct.unpack(">hh", p[0:4])
            i_mot, i_in = struct.unpack(">ii", p[4:12])
            duty = struct.unpack(">h", p[20:22])[0]
            rpm = struct.unpack(">i", p[22:26])[0]
            v_in = struct.unpack(">h", p[26:28])[0]
            fault = p[52] if len(p) > 52 else -1
            print(f"GET_VALUES: v_in={v_in / 10:.1f} V  t_fet={t_fet / 10:.1f} C  t_motor={t_mot / 10:.1f} C  "
                  f"i_motor={i_mot / 100:.2f} A  i_in={i_in / 100:.2f} A  duty={duty / 1000:.3f}  erpm={rpm}  "
                  f"fault={fault} ({FAULTS.get(fault, '?')})")
        time.sleep(0.3)
    port.close()


if __name__ == "__main__":
    main()
