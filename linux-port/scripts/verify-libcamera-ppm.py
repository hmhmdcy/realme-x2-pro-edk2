#!/usr/bin/env python3
"""Summarize libcamera RGB888 PPM captures without making image-quality claims."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read_ppm(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    magic, dimensions, maximum, pixels = data.split(b"\n", 3)
    width, height = (int(value) for value in dimensions.split())
    if magic != b"P6" or maximum != b"255":
        raise ValueError(f"{path}: expected binary 8-bit RGB PPM")
    if len(pixels) != width * height * 3:
        raise ValueError(f"{path}: payload does not match dimensions")
    return width, height, pixels


def summarize(path: Path) -> dict[str, object]:
    width, height, pixels = read_ppm(path)
    return {
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "width": width,
        "height": height,
        "min": min(pixels),
        "max": max(pixels),
        "mean": round(sum(pixels) / len(pixels), 3),
        "nonzero_percent": round(
            sum(value != 0 for value in pixels) / len(pixels) * 100,
            6,
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    captures = {
        path.name: summarize(path)
        for path in sorted(args.directory.glob("cam*.ppm"))
    }
    print(json.dumps(captures, indent=2, sort_keys=True))
    return 0 if captures else 1


if __name__ == "__main__":
    raise SystemExit(main())
