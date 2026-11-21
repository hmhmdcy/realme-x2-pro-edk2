#!/usr/bin/env python3
"""Unbind the NCM gadget, sync, then request RESTART2("bootloader")."""

import ctypes
import json
import os
import sys
import time

UDC = "/sys/class/udc/a600000.usb"
GADGET = "/sys/kernel/config/usb_gadget/samurai"
RESTART2_SYSCALL = 142
RESTART2_MAGIC1 = 0xFEE1DEAD
RESTART2_MAGIC2 = 672274793
RESTART2_BOOTLOADER = 0xA1B2C3D4


def read(path):
    try:
        with open(path) as handle:
            return handle.read().strip()
    except OSError:
        return ""


def write(path, value):
    with open(path, "w") as handle:
        handle.write(value)


def main():
    inspect = "--inspect" in sys.argv[1:]
    if os.geteuid() != 0:
        print("must run as root", file=sys.stderr)
        return 2

    bound = read(f"{GADGET}/UDC")
    report = {
        "gadget": GADGET,
        "udc": UDC,
        "bound_udc": bound,
        "state": read(f"{UDC}/state"),
        "inspect": inspect,
    }
    print(json.dumps(report, sort_keys=True), flush=True)
    if inspect:
        return 0

    if bound:
        write(f"{GADGET}/UDC", "\n")
        deadline = time.time() + 5
        while time.time() < deadline and read(f"{GADGET}/UDC"):
            time.sleep(0.1)
        if read(f"{GADGET}/UDC"):
            print("failed to unbind gadget UDC", file=sys.stderr)
            return 1

    os.sync()
    command = ctypes.create_string_buffer(b"bootloader\0")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    libc.syscall.argtypes = [
        ctypes.c_long,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    result = libc.syscall(
        RESTART2_SYSCALL,
        RESTART2_MAGIC1,
        RESTART2_MAGIC2,
        RESTART2_BOOTLOADER,
        ctypes.cast(command, ctypes.c_void_p),
    )
    print(
        f"restart2 returned result={result} errno={ctypes.get_errno()}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
