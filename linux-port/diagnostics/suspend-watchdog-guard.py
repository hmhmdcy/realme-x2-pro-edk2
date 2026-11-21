#!/usr/bin/env python3
"""Keep a bounded hardware watchdog armed across an s2idle suspend test."""

import fcntl
import os
import struct
import sys
import time

WDIOC_GETTIMEOUT = 0x80045707
WDIOC_SETTIMEOUT = 0xC0045706


def ioctl_timeout(fd, request, value=0):
    return struct.unpack("i", fcntl.ioctl(fd, request, struct.pack("i", value)))[0]


def write_text(path, value):
    with open(path, "w", encoding="ascii") as output:
        output.write(value)


timeout_s = int(sys.argv[1])
stop_path = sys.argv[2]
param_path = sys.argv[3]
ready_path = sys.argv[4]

fd = os.open("/dev/watchdog", os.O_WRONLY)
original_param = open(param_path, encoding="ascii").read().strip()
try:
    requested = ioctl_timeout(fd, WDIOC_SETTIMEOUT, timeout_s)
    actual = ioctl_timeout(fd, WDIOC_GETTIMEOUT)
    if actual != timeout_s:
        raise RuntimeError(f"watchdog timeout {actual}s, requested {timeout_s}s")

    write_text(param_path, "Y\n")
    write_text(ready_path, f"timeout={actual}\n")
    print(f"suspend watchdog armed timeout={actual}s", flush=True)

    while not os.path.exists(stop_path):
        os.write(fd, b"1")
        time.sleep(5)
finally:
    try:
        write_text(param_path, original_param + "\n")
    except OSError:
        pass
    os.write(fd, b"V")
    os.close(fd)
