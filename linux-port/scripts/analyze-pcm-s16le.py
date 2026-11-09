#!/usr/bin/env python3
"""Report basic continuity and level statistics for raw S16_LE PCM."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from array import array
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--rate", type=int, default=48000)
    parser.add_argument("--channels", type=int, default=1)
    args = parser.parse_args()

    raw = args.path.read_bytes()
    frame_bytes = 2 * args.channels
    if len(raw) % frame_bytes:
        raise SystemExit(f"{args.path}: partial PCM frame")

    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()

    if not samples:
        raise SystemExit(f"{args.path}: empty PCM stream")

    total = len(samples)
    nonzero = sum(sample != 0 for sample in samples)
    clipped = sum(sample >= 32767 or sample <= -32768 for sample in samples)
    square_sum = sum(sample * sample for sample in samples)
    longest_zero = 0
    current_zero = 0
    for sample in samples:
        if sample == 0:
            current_zero += 1
            longest_zero = max(longest_zero, current_zero)
        else:
            current_zero = 0

    frames = total // args.channels
    report = {
        "schema": "samurai-pcm-s16le-analysis-v1",
        "path": str(args.path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "sample_rate": args.rate,
        "channels": args.channels,
        "samples": total,
        "frames": frames,
        "duration_seconds": round(frames / args.rate, 6),
        "min": min(samples),
        "max": max(samples),
        "rms": round(math.sqrt(square_sum / total), 3),
        "nonzero_percent": round(nonzero / total * 100, 6),
        "clipped_percent": round(clipped / total * 100, 6),
        "longest_zero_run_seconds": round(longest_zero / args.rate, 6),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
