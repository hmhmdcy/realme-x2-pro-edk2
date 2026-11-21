#!/usr/bin/env python3
"""Read and restore the hardware watchdog timeout without leaving it armed."""

import fcntl
import os
import struct

WDIOC_GETTIMEOUT = 0x80045707
WDIOC_SETTIMEOUT = 0xC0045706


def get_timeout(fd):
    return struct.unpack("i", fcntl.ioctl(fd, WDIOC_GETTIMEOUT,
                                         struct.pack("i", 0)))[0]


fd = os.open("/dev/watchdog", os.O_WRONLY)
try:
    original = get_timeout(fd)
    print(f"original_timeout={original}", flush=True)
    probe = struct.unpack(
        "i", fcntl.ioctl(fd, WDIOC_SETTIMEOUT, struct.pack("i", 30))
    )[0]
    restored = struct.unpack(
        "i", fcntl.ioctl(fd, WDIOC_SETTIMEOUT, struct.pack("i", original))
    )[0]
    print("requested_probe_timeout=30")
    print(f"probe_timeout={probe}")
    print(f"restored_timeout={restored}")
finally:
    os.write(fd, b"V")
    os.close(fd)
