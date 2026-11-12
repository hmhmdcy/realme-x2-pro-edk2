#!/usr/bin/env python3
"""Export the PM8150B Type-C wake patch from the kernel worktree."""

from pathlib import Path
import argparse
import subprocess

FILES = (
    "Documentation/devicetree/bindings/usb/qcom,pmic-typec.yaml",
    "drivers/usb/typec/tcpm/qcom/qcom_pmic_typec.c",
    "drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.c",
    "drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.h",
)

HEADER = """\
From 0000000000000000000000000000000000000000 Mon Sep 17 00:00:00 2001
From: Codex <codex@localhost>
Date: Wed, 11 Nov 2026 22:15:00 +0800
Subject: [PATCH] usb: typec: qcom-pmic: arm attach/VBUS IRQs as wake sources

The Qualcomm PMIC Type-C port driver requests its SPMI child interrupts
with IRQF_NO_AUTOEN and enables them only while the Type-C port is active.
None of those interrupts is armed as a system wakeup source, so a charger
or USB cable cannot wake the SoC through PM8150B even when the SPMI
periph_irq parent is routed through the Qualcomm PDC.

Allow a Type-C node to opt in with the standard wakeup-source property.
While suspended, arm the CC-state, VBUS-change, and attach-detach IRQs with
enable_irq_wake(); the SPMI PMIC arbiter propagates the wake request to its
PDC parent. Disarm them on resume.

Upstream-Status: Pending

Signed-off-by: Codex <codex@localhost>
---
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    result = subprocess.run(
        [
            "git",
            "-C",
            str(args.kernel),
            "diff",
            "--",
            *FILES,
        ],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    if not result.stdout:
        raise SystemExit("the kernel worktree has no Type-C wake diff")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(HEADER + result.stdout, encoding="utf-8")

    check = subprocess.run(
        [
            "git",
            "-C",
            str(args.kernel),
            "apply",
            "--check",
            "--reverse",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if check.returncode:
        raise SystemExit(
            "reverse apply check failed: "
            + (check.stderr or check.stdout).strip()
        )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
