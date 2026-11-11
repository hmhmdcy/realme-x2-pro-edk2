#!/usr/bin/env python3
"""Generate the S5KGW1 9280x6944 mode-0 register table."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("records", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records = json.loads(args.records.read_text())["modes"][0]
    lines = [
        "/* SPDX-License-Identifier: GPL-2.0-only */",
        "/* Generated from the OEM sunny_s5kgw1 sensormodule mode 0. */",
        "#ifndef S5KGW1_MODE0_TABLES_H",
        "#define S5KGW1_MODE0_TABLES_H",
        "",
        "static const struct s5kgw1_reg s5kgw1_mode0_regs[] = {",
    ]

    for record in records:
        if record["operation"] != "WRITE":
            raise ValueError("mode 0 must contain only single writes")
        if len(record["values"]) != 1 or len(record["delays_us"]) != 1:
            raise ValueError("mode 0 record has an unexpected vector length")
        lines.append(
            "\t{ .address = 0x%04x, .value = 0x%04x, .value_bytes = %d, "
            ".delay_us = %d },"
            % (
                record["address"],
                record["values"][0],
                record["value_bytes"],
                record["delays_us"][0],
            )
        )

    lines += ["};", "", "#endif", ""]
    args.output.write_text("\n".join(lines))
    print(f"wrote {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
