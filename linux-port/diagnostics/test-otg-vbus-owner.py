#!/usr/bin/env python3
"""Read-only cross-check of the RMX1931 USB-C VBUS source ownership.

The stock firmware describes both the PM8150B/SMB5 DCDC path and an MP2650
``qcom,mps_otg_en-gpio`` on PM8150 GPIO4.  Hardware testing on this
handset showed that the populated OTG boost is the MP2650 path: enabling
the PM8150B ``usb-vbus-regulator@1100`` path produced
``vbus vsafe5v fail`` and no external device, while the MP2650
``usb-otg-vbus`` regulator drove VBUS and enumerated a mouse.  The board
candidate therefore uses the MP2650 child and leaves the PM8150B
standalone regulator disabled.

Historical stock SMB5 register references still use PM8150B DCDC base
0x1100:

    DCDC_CMD_OTG_REG                = 0x1140
    DCDC_OTG_CURRENT_LIMIT_CFG_REG  = 0x1152
    DCDC_OTG_CFG_REG                = 0x1153

This test checks the board DTS ownership and, when KERNEL_ROOT is
supplied, the standard MP2650 regulator and PMIC Type-C driver hooks.  It
never touches a device or sysfs.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"missing input: {path}") from None


def require(pattern: str, text: str, label: str) -> None:
    if re.search(pattern, text, re.MULTILINE | re.DOTALL) is None:
        raise SystemExit(f"FAIL: {label}")
    print(f"PASS: {label}")


def reject(pattern: str, text: str, label: str) -> None:
    if re.search(pattern, text, re.MULTILINE | re.DOTALL) is not None:
        raise SystemExit(f"FAIL: {label}")
    print(f"PASS: {label}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root (default: inferred from this script)",
    )
    parser.add_argument(
        "--kernel-root",
        type=Path,
        default=Path(os.environ.get("KERNEL_ROOT", "")).expanduser()
        if os.environ.get("KERNEL_ROOT")
        else None,
        help="Linux tree root for the optional mainline-source checks",
    )
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    oem = repo / "reference" / "charging-oem-audit-20261023" / "apsd-lifecycle" / "oem"
    stock_pm = oem / "arch--arm64--boot--dts--19781--pm8150b.dtsi"
    stock_overlay = oem / "arch--arm64--boot--dts--19781--sm8150-pmic-overlay.dtsi"
    stock_smb5_reg = oem / "drivers--power--supply--qcom--smb5-reg.h"
    otg_dts = repo / "linux-port" / "dts" / "experiments" / "sm8150-samurai-usb-otg.dts"
    common_dtsi = (
        repo / "linux-port" / "dts" / "split-ba61" / "sm8150-samurai-common.dtsi"
    )
    stock_mtp = repo / "linux-port" / "refs" / "19781" / "sm8150-mtp.dtsi"

    pm = read(stock_pm)
    overlay = read(stock_overlay)
    smb5_reg = read(stock_smb5_reg)
    otg = read(otg_dts)
    common = read(common_dtsi)
    stock_mtp_text = read(stock_mtp)

    print("== stock VBUS owner ==")
    require(
        r"vbus-supply\s*=\s*<&smb5_vbus>;",
        pm,
        "stock PD PHY uses smb5_vbus",
    )
    require(
        r"smb5_vbus:\s*qcom,smb5-vbus\s*\{",
        overlay,
        "stock SMB5 charger registers smb5_vbus",
    )
    require(
        r"#define\s+DCDC_BASE\s+0x1100",
        smb5_reg,
        "stock SMB5 DCDC base is 0x1100",
    )
    require(
        r"#define\s+DCDC_CMD_OTG_REG\s+\(DCDC_BASE\s*\+\s*0x40\)",
        smb5_reg,
        "stock OTG enable register is 0x1140",
    )
    require(
        r"#define\s+DCDC_OTG_CURRENT_LIMIT_CFG_REG\s+\(DCDC_BASE\s*\+\s*0x52\)",
        smb5_reg,
        "stock OTG current-limit register is 0x1152",
    )
    require(
        r"#define\s+DCDC_OTG_CFG_REG\s+\(DCDC_BASE\s*\+\s*0x53\)",
        smb5_reg,
        "stock OTG config register is 0x1153",
    )
    require(
        r"qcom,mps_otg_en-gpio\s*=\s*<&pm8150_gpios\s+4\s+0x00>;",
        stock_mtp_text,
        "stock charger describes the MP2650 MPS OTG GPIO",
    )

    print("== board OTG VBUS owner ==")
    require(
        r"mp2650_vbus:\s*usb-otg-vbus\s*\{.*?regulator-name\s*=\s*\"mp2650-vbus\";",
        common,
        "board MP2650 child is the standard usb-otg-vbus regulator",
    )
    require(
        r"otg-gpios\s*=\s*<&pm8150_gpios\s+4\s+GPIO_ACTIVE_HIGH>;",
        common,
        "board MP2650 child owns the PM8150 GPIO4 OTG enable",
    )
    require(
        r"vbus-supply\s*=\s*<&mp2650_vbus>;",
        otg,
        "candidate connector uses mp2650_vbus",
    )
    require(
        r"&usb_1_dwc3\s*\{.*?dr_mode\s*=\s*\"otg\";.*?usb-role-switch;",
        otg,
        "candidate uses DWC3 OTG with the standard role switch",
    )
    reject(
        r"&pm8150b_vbus\s*\{.*?status\s*=\s*\"okay\";",
        otg,
        "candidate does not enable the unconnected PM8150B VBUS path",
    )

    if args.kernel_root is not None:
        kernel = args.kernel_root.resolve()
        mp2650 = read(
            kernel / "drivers" / "power" / "supply" / "mp2650_charger.c"
        )
        typec_port = read(
            kernel
            / "drivers"
            / "usb"
            / "typec"
            / "tcpm"
            / "qcom"
            / "qcom_pmic_typec_port.c"
        )
        print("== mainline driver source ==")
        require(
            r"#define\s+MP2650_OTG_EN\s+BIT\(5\)",
            mp2650,
            "MP2650 driver carries the standard OTG enable bit",
        )
        require(
            r"static int mp2650_vbus_enable\(struct regulator_dev \*rdev\)",
            mp2650,
            "MP2650 driver exposes the regulator enable op",
        )
        require(
            r"devm_gpiod_get_optional\(&client->dev,\s*\"otg\",\s*GPIOD_OUT_LOW\)",
            mp2650,
            "MP2650 driver requests the board OTG GPIO",
        )
        require(
            r"devm_regulator_register\(dev,\s*&mp2650_vbus_desc,\s*&config\)",
            mp2650,
            "MP2650 driver registers the standard VBUS regulator",
        )
        require(
            r"devm_of_regulator_get_optional\(dev,\s*to_of_node\(connector\),\s*\"vbus\"\)",
            typec_port,
            "mainline PMIC Type-C gets the connector vbus supply",
        )

    print("RESULT: OTG VBUS owner test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
