"""Minimal CDR (Common Data Representation) reader for cross-checking rclpy's
typed deserialization against the raw bytes actually on the wire.

Why this exists: ROS 2 Humble (rmw_fastrtps) does not check type hashes between
publisher and subscriber. If laksa_interfaces here does not *exactly* match the
message layout the flashed ESP32 firmware was built against, rclpy will still
"successfully" deserialize every message -- it will just silently read the
wrong bytes into the wrong fields. A raw-byte decode, computed independently
from first principles (field order + CDR alignment rules) and compared against
what rclpy handed us, is the only way to catch that class of mismatch instead
of trusting the deserializer that could itself be the thing that's wrong.

Only plain (non-string, non-sequence) fixed-layout messages are supported --
that covers VescState, Pca9685State and VehicleState (including its nested
geometry_msgs float64 fields), which is all laksa_readonly_check.py needs.
Do not extend this to variable-length fields without also handling CDR's
length-prefix + alignment rules for them.
"""
from __future__ import annotations

import struct


class CDRReader:
    """Reads a CDR little-endian payload as produced by rmw_fastrtps.

    The first 4 bytes of any ROS 2 serialized message are the encapsulation
    header (representation id + options), not message data. Alignment for
    every subsequent field is computed relative to the end of that header
    (the start of the message body), matching what Fast-CDR / Micro-CDR and
    rclcpp/rclpy generated (de)serializers do. For 1/2/4-byte fields this is
    indistinguishable from aligning to position 0 (the header is 4 bytes);
    it only matters for 8-byte fields such as float64.
    """

    _BODY_ORIGIN = 4

    def __init__(self, data: bytes):
        self.data = data
        if len(data) < 4:
            raise ValueError("payload too short to contain a CDR header")
        header = data[:4]
        # Fast-RTPS/CycloneDDS little-endian CDR encapsulation ids are
        # 0x00,0x01 (PL_CDR_LE uses 0x00,0x03; plain CDR_LE uses 0x00,0x01).
        if header[0] != 0x00 or header[1] not in (0x01, 0x03):
            raise ValueError(
                f"unexpected CDR encapsulation header {header!r}; "
                "this decoder assumes little-endian CDR"
            )
        self.pos = 4

    def _align(self, n: int) -> None:
        rem = (self.pos - self._BODY_ORIGIN) % n
        if rem:
            self.pos += n - rem

    def read_u8(self) -> int:
        v = self.data[self.pos]
        self.pos += 1
        return v

    def read_bool(self) -> bool:
        return self.read_u8() != 0

    def read_u16(self) -> int:
        self._align(2)
        v = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return v

    def read_u32(self) -> int:
        self._align(4)
        v = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_i32(self) -> int:
        self._align(4)
        v = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_f32(self) -> float:
        self._align(4)
        v = struct.unpack_from("<f", self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_f64(self) -> float:
        self._align(8)
        v = struct.unpack_from("<d", self.data, self.pos)[0]
        self.pos += 8
        return v

    def read_time(self) -> tuple[int, int]:
        """builtin_interfaces/Time: int32 sec, uint32 nanosec."""
        sec = self.read_i32()
        nanosec = self.read_u32()
        return sec, nanosec

    def remaining(self) -> int:
        return len(self.data) - self.pos
