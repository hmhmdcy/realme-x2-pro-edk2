#!/usr/bin/env python3
"""Arm the qcom watchdog before a diagnostic kexec transition."""

import fcntl
import os
import struct
import time

fd = os.open("/dev/watchdog", os.O_WRONLY)
try:
    try:
        fcntl.ioctl(fd, 0xC0045706, struct.pack("i", 30))
        print("watchdog timeout=30", flush=True)
    except OSError as exc:
        print(f"watchdog settimeout failed: {exc}", flush=True)
    time.sleep(120)
    os.write(fd, b"V")
finally:
    os.close(fd)
