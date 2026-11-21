#!/usr/bin/env python3
"""Toggle unused SM8150 GCC branch gates through /dev/mem for diagnosis."""

import argparse
import fcntl
import json
import mmap
import os
import struct
import sys
import time

GCC_BASE = 0x00100000
GCC_SIZE = 0x001F0000
WDIOC_SETTIMEOUT = 0xC0045706
WDIOC_KEEPALIVE = 0x80045705

CLOCKS = [
    ("gcc_pcie_0_clkref_clk", 0x8C00C, 1 << 0, False),
    ("gcc_pcie_1_clkref_clk", 0x8C02C, 1 << 0, False),
    ("gcc_pcie0_phy_refgen_clk", 0x6F02C, 1 << 0, False),
    ("gcc_pcie1_phy_refgen_clk", 0x6F030, 1 << 0, False),
    ("gcc_aggre_noc_pcie_tbu_clk", 0x90018, 1 << 0, False),
    ("gcc_ufs_card_clkref_clk", 0x8C004, 1 << 0, False),
    ("gcc_sdcc2_ahb_clk", 0x14008, 1 << 0, False),
    ("gcc_sdcc2_apps_clk", 0x14004, 1 << 0, False),
    ("gcc_qupv3_wrap1_s4_clk", 0x5200C, 1 << 26, False),
    ("gcc_boot_rom_ahb_clk", 0x52004, 1 << 10, False),
    ("gcc_gpu_iref_clk", 0x8C010, 1 << 0, False),
    ("gcc_usb3_prim_clkref_clk", 0x8C008, 1 << 0, False),
    ("gcc_usb3_prim_phy_com_aux_clk", 0xF054, 1 << 0, False),
    ("gcc_usb3_prim_phy_aux_clk", 0xF050, 1 << 0, False),
    ("gcc_usb3_prim_phy_pipe_clk", 0xF058, 1 << 0, False),
    ("gcc_cpuss_rbcpr_clk", 0x48008, 1 << 0, True),
]


def log(path, message):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}"
    print(line, flush=True)
    with open(path, "a") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read32(region, offset):
    return struct.unpack_from("<I", region, offset)[0]


def write32(region, offset, value):
    struct.pack_into("<I", region, offset, value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    parser.add_argument("--include-critical", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-watchdog", action="store_true")
    parser.add_argument("--watchdog-timeout", type=int, default=20)
    parser.add_argument("--log", default="/root/gcc-clk-gate-sweep.log")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        for entry in CLOCKS:
            print("%-34s off=0x%05x mask=0x%08x critical=%s" % entry)
        return 0

    if os.geteuid() != 0:
        print("must run as root", file=sys.stderr)
        return 2

    selected = []
    for entry in CLOCKS:
        name, offset, mask, critical = entry
        if args.only and name != args.only:
            continue
        if critical and not args.include_critical:
            continue
        selected.append(entry)
    if not selected:
        print("no clocks selected", file=sys.stderr)
        return 2

    fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
    region = mmap.mmap(fd, GCC_SIZE, flags=mmap.MAP_SHARED,
                       prot=mmap.PROT_READ | mmap.PROT_WRITE,
                       offset=GCC_BASE)
    log(args.log, json.dumps({"event": "start", "base": hex(GCC_BASE),
                              "count": len(selected), "dry_run": args.dry_run}))

    watchdog = None
    if not args.no_watchdog:
        watchdog = os.open("/dev/watchdog", os.O_WRONLY)
        try:
            fcntl.ioctl(watchdog, WDIOC_SETTIMEOUT,
                        struct.pack("i", args.watchdog_timeout))
        except OSError as exc:
            log(args.log, json.dumps({"event": "watchdog_settimeout_error",
                                      "error": str(exc)}))

    try:
        for name, offset, mask, critical in selected:
            before = read32(region, offset)
            log(args.log, json.dumps({
                "event": "begin", "clock": name, "offset": hex(offset),
                "mask": hex(mask), "value": hex(before), "critical": critical,
            }))
            if not args.dry_run:
                write32(region, offset, before | mask)
                time.sleep(0.2)
                write32(region, offset, before & ~mask)
                time.sleep(1.0)
                after = read32(region, offset)
                log(args.log, json.dumps({
                    "event": "after_off", "clock": name,
                    "value": hex(after), "changed": after != before,
                }))
                write32(region, offset, after | mask)
                time.sleep(0.2)
                restored = read32(region, offset)
                log(args.log, json.dumps({
                    "event": "restored", "clock": name,
                    "value": hex(restored),
                }))
            if watchdog is not None:
                try:
                    fcntl.ioctl(watchdog, WDIOC_KEEPALIVE, 0)
                except OSError:
                    pass
        log(args.log, json.dumps({"event": "done"}))
    finally:
        if watchdog is not None:
            try:
                os.write(watchdog, b"V")
            except OSError:
                pass
            os.close(watchdog)
        region.close()
        os.close(fd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
