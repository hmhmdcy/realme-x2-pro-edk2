#!/usr/bin/env python3
"""Inspect or retire the running SM8150 EUD owner from a root Linux shell."""

from __future__ import annotations

import argparse
import mmap
import os
import struct
import sys
import time
from pathlib import Path


EUD_BASE = 0x088E0000
EUD_WINDOW = 0x2000
EUD_CSR_EN = 0x1014
KNOWN_ENABLED_WORDS = {0x00000001, 0x01010101}
EUD_DEVICE = "88e0000.serial"
EUD_DRIVER = Path("/sys/bus/platform/drivers/qcom_eud_com")
DWC3_DEVICE = "a600000.usb"
DWC3_DRIVER = Path("/sys/bus/platform/drivers/dwc3-qcom")
GADGET_UDC = Path("/sys/kernel/config/usb_gadget/samurai/UDC")


def fail(message: str) -> None:
    raise SystemExit(message)


def sysfs_write(path: Path, value: str) -> None:
    with path.open("w", encoding="ascii") as handle:
        handle.write(value)


def read_csr() -> int:
    if os.geteuid() != 0:
        fail("root is required to read /dev/mem")
    with open("/dev/mem", "r+b", buffering=0) as memory:
        mapping = mmap.mmap(
            memory.fileno(), EUD_WINDOW, offset=EUD_BASE,
            access=mmap.ACCESS_WRITE,
        )
        try:
            return struct.unpack_from("<I", mapping, EUD_CSR_EN)[0]
        finally:
            mapping.close()


def write_csr(value: int) -> int:
    if os.geteuid() != 0:
        fail("root is required to write /dev/mem")
    with open("/dev/mem", "r+b", buffering=0) as memory:
        mapping = mmap.mmap(
            memory.fileno(), EUD_WINDOW, offset=EUD_BASE,
            access=mmap.ACCESS_WRITE,
        )
        try:
            struct.pack_into("<I", mapping, EUD_CSR_EN, value)
            mapping.flush()
            return struct.unpack_from("<I", mapping, EUD_CSR_EN)[0]
        finally:
            mapping.close()


def eud_bound() -> bool:
    return (EUD_DRIVER / EUD_DEVICE).exists()


def disable_eud() -> int:
    original = read_csr()
    print(f"CSR_EUD_EN initial=0x{original:08x}")
    if original not in KNOWN_ENABLED_WORDS | {0}:
        fail("refusing unknown EUD enable value")
    if eud_bound():
        print("unbinding qcom_eud_com")
        sysfs_write(EUD_DRIVER / "unbind", EUD_DEVICE)
    else:
        print("qcom_eud_com is already unbound")
    current = write_csr(0)
    print(f"CSR_EUD_EN after_write=0x{current:08x}")
    if current != 0:
        fail("EUD did not acknowledge disable")
    return 0


def rebind_dwc3() -> int:
    bound = (DWC3_DRIVER / DWC3_DEVICE).exists()
    print(f"dwc3-qcom bound={bound}")
    if bound:
        print("unbinding dwc3-qcom")
        sysfs_write(DWC3_DRIVER / "unbind", DWC3_DEVICE)
        time.sleep(1)
    print("binding dwc3-qcom")
    sysfs_write(DWC3_DRIVER / "bind", DWC3_DEVICE)
    time.sleep(3)
    udc = Path("/sys/class/udc") / DWC3_DEVICE
    print(f"udc_present={udc.exists()}")
    if udc.exists():
        print(f"udc_state={udc.joinpath('state').read_text().strip()}")
        current = GADGET_UDC.read_text().strip() if GADGET_UDC.exists() else ""
        print(f"gadget_udc={current or '<empty>'}")
        if not current:
            GADGET_UDC.write_text(f"{DWC3_DEVICE}\n", encoding="ascii")
            time.sleep(2)
            print(f"gadget_udc_after={GADGET_UDC.read_text().strip()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--disable", action="store_true")
    actions.add_argument("--rebind", action="store_true")
    args = parser.parse_args()
    print(f"CSR_EUD_EN=0x{read_csr():08x}")
    print(f"qcom_eud_com_bound={eud_bound()}")
    if args.disable:
        return disable_eud()
    if args.rebind:
        return rebind_dwc3()
    return 0


if __name__ == "__main__":
    sys.exit(main())
