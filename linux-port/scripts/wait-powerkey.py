#!/usr/bin/env python3
"""Wait for one physical KEY_POWER press/release on pm8941_pwrkey."""

import glob
import os
import select
import struct
import sys
import time

EV_KEY = 1
KEY_POWER = 116


def find_powerkey_event():
    for name_path in glob.glob("/sys/class/input/event*/device/name"):
        try:
            with open(name_path, encoding="ascii") as f:
                if f.read().strip() == "pm8941_pwrkey":
                    return "/dev/input/" + name_path.split("/")[4]
        except OSError:
            continue
    raise SystemExit("pm8941_pwrkey event not found")


def main():
    timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 180.0
    event_path = find_powerkey_event()
    fd = os.open(event_path, os.O_RDONLY | os.O_NONBLOCK)
    event = struct.Struct("llHHi")
    deadline = time.monotonic() + timeout
    down_at = None

    print(f"powerkey_event={event_path}", flush=True)
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select(
                [fd], [], [], min(0.5, deadline - time.monotonic())
            )
            if not ready:
                continue
            data = os.read(fd, event.size * 64)
            for offset in range(0, len(data) - event.size + 1, event.size):
                sec, usec, kind, code, value = event.unpack_from(data, offset)
                timestamp = sec + usec / 1_000_000
                if kind == EV_KEY and code == KEY_POWER and value == 1:
                    down_at = timestamp
                    print(f"POWER_DOWN {timestamp:.6f}", flush=True)
                elif kind == EV_KEY and code == KEY_POWER and value == 0 and down_at:
                    print(
                        f"POWER_UP {timestamp:.6f} "
                        f"duration={timestamp - down_at:.6f}s",
                        flush=True,
                    )
                    return 0
    finally:
        os.close(fd)

    print("POWER_TIMEOUT", flush=True)
    return 124


if __name__ == "__main__":
    sys.exit(main())
