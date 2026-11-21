#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


HERE = Path(__file__).resolve().parent


def function(source: str, name: str) -> str:
    match = re.search(r"^static [^\n]+\b" + re.escape(name) + r"\(", source, re.M)
    if not match:
        raise SystemExit(f"missing function: {name}")
    brace = source.index("{", match.end())
    depth = 1
    pos = brace + 1
    while depth:
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
        pos += 1
    return source[match.start() : pos]


def main() -> None:
    source = (HERE / "source/samurai-usb-input.c").read_text()
    names = [
        "samurai_usb_stop",
        "samurai_usb_clear_wake",
        "samurai_usb_arm_wake",
        "samurai_usb_restart_work",
        "samurai_usb_cleanup_wake",
        "samurai_usb_suspend",
        "samurai_usb_resume",
        "samurai_usb_event",
        "samurai_usb_request_events",
        "samurai_usb_shutdown",
    ]
    (HERE / "actual-functions.inc").write_text(
        "\n\n".join(function(source, name) for name in names) + "\n"
    )
    probe = function(source, "samurai_usb_probe")
    request = probe.index("samurai_usb_request_events")
    supply = probe.index("devm_power_supply_register")
    cleanup = probe.index("dev, samurai_usb_cleanup_wake")
    stop = probe.index("dev, samurai_usb_stop")
    if not request < supply < cleanup < stop:
        raise SystemExit("probe initialization or devres order changed")


if __name__ == "__main__":
    main()
