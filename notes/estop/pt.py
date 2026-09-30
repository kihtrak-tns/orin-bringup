import struct, sys
d = open(sys.argv[1], "rb").read()
for i in range(0, len(d), 32):
    e = d[i:i+32]
    if e[:2] != b"\xaa\x50":
        break
    t, s = e[2], e[3]
    off, size = struct.unpack("<II", e[4:12])
    name = e[12:28].rstrip(b"\x00").decode(errors="replace")
    print("type=%d sub=0x%02x off=0x%06x size=0x%06x name=%s" % (t, s, off, size, name))
