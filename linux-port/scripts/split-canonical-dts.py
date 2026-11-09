#!/usr/bin/env python3
"""Generate the OS/vendor DTS split from the locked k363 samurai source."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


VENDOR_PROPERTIES = (
    "qcom,msm-id",
    "qcom,board-id",
    "oppo,dtsi_no",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def remove_vendor_block(source: str) -> str:
    marker = "\t/*\n\t * VENDOR: properties of the stock base DTB."
    start = source.index(marker)
    last = "\toppo,dtsi_no = <19781>;\n"
    end = source.index(last, start) + len(last)
    return source[:start] + source[end:]


parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True, type=Path)
parser.add_argument("--output-dir", required=True, type=Path)
parser.add_argument("--expect-sha256", required=True)
args = parser.parse_args()

source_bytes = args.source.read_bytes()
source_sha = sha256(source_bytes)
assert source_sha == args.expect_sha256, (source_sha, args.expect_sha256)
source = source_bytes.decode("utf-8")

directive = "/dts-v1/;\n"
assert source.count(directive) == 1
without_directive = source.replace(directive, "", 1)
common = remove_vendor_block(without_directive)
for prop in VENDOR_PROPERTIES:
    assert f"\n\t{prop} = " not in common

args.output_dir.mkdir(parents=True, exist_ok=True)
common_path = args.output_dir / "sm8150-samurai-common.dtsi"
os_path = args.output_dir / "sm8150-samurai-os.dts"
vendor_path = args.output_dir / "sm8150-samurai-vendor.dts"

header = """\
// SPDX-License-Identifier: BSD-3-Clause
/*
 * Realme X2 Pro (RMX1931CN), codename "samurai".
 *
 * OS-facing source split from the locked k363 board description.
 * Shared hardware lives in sm8150-samurai-common.dtsi.
 */
"""

common_path.write_text(common, encoding="utf-8")
os_path.write_text(
    header
    + "/dts-v1/;\n\n#include \"sm8150-samurai-common.dtsi\"\n",
    encoding="utf-8",
)
vendor_path.write_text(
    header
    + "/dts-v1/;\n\n#include \"sm8150-samurai-common.dtsi\"\n\n"
    + "/ {\n"
    + "\tqcom,msm-id = <339 0x20000>;\n"
    + "\tqcom,board-id = <0 0>;\n"
    + "\toppo,dtsi_no = <19781>;\n"
    + "};\n",
    encoding="utf-8",
)

print(
    json.dumps(
        {
            "schema": "samurai-dts-source-split-v1",
            "canonical_source": {
                "path": str(args.source),
                "sha256": source_sha,
                "bytes": len(source_bytes),
            },
            "outputs": {
                path.name: {
                    "path": str(path),
                    "sha256": sha256(path.read_bytes()),
                    "bytes": path.stat().st_size,
                }
                for path in (common_path, os_path, vendor_path)
            },
            "removed_vendor_properties": list(VENDOR_PROPERTIES),
        },
        indent=2,
        sort_keys=True,
    )
)
