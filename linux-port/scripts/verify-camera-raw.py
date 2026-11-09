#!/usr/bin/env python3
"""Validate the two-frame RAW10 captures produced by test-camera-four-raw.sh."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None


CAMERAS = {
    "front": (1928, 1088, 2416),
    "rear": (1632, 1224, 2048),
    "tele": (2104, 1560, 2640),
    "wide": (4608, 3456, 5760),
}


def unpack_raw10(frame, width, height, stride):
    rows = frame.reshape(height, stride)[:, : width * 10 // 8]
    groups = rows.reshape(height, width // 4, 5).astype(np.uint16)
    pixels = np.empty((height, width), dtype=np.uint16)
    for index in range(4):
        pixels[:, index::4] = groups[:, :, index] | (
            ((groups[:, :, 4] >> (2 * index)) & 3) << 8
        )
    return pixels


def analyze_python(path, width, height, stride):
    data = path.read_bytes()
    frame_size = height * stride
    if len(data) != frame_size * 2:
        raise ValueError(f"{path}: expected {frame_size * 2}, got {len(data)}")
    if width % 4:
        raise ValueError(f"{path}: width must be divisible by four")

    stats = [
        {"min": 1023, "max": 0, "sum": 0, "nonzero": 0, "saturated": 0}
        for _ in range(2)
    ]
    row_bytes = width * 10 // 8
    different = 0
    for row in range(height):
        first = row * stride
        second = frame_size + first
        for offset in range(0, row_bytes, 5):
            a = first + offset
            b = second + offset
            a0, a1, a2, a3, a4 = data[a : a + 5]
            b0, b1, b2, b3, b4 = data[b : b + 5]
            a_pixels = (
                a0 | ((a4 & 0x03) << 8),
                a1 | (((a4 >> 2) & 0x03) << 8),
                a2 | (((a4 >> 4) & 0x03) << 8),
                a3 | (((a4 >> 6) & 0x03) << 8),
            )
            b_pixels = (
                b0 | ((b4 & 0x03) << 8),
                b1 | (((b4 >> 2) & 0x03) << 8),
                b2 | (((b4 >> 4) & 0x03) << 8),
                b3 | (((b4 >> 6) & 0x03) << 8),
            )
            for index, pixels in enumerate((a_pixels, b_pixels)):
                current = stats[index]
                current["sum"] += sum(pixels)
                current["nonzero"] += sum(pixel != 0 for pixel in pixels)
                current["saturated"] += sum(pixel >= 1023 for pixel in pixels)
                current["min"] = min(current["min"], *pixels)
                current["max"] = max(current["max"], *pixels)
            different += sum(
                first_pixel != second_pixel
                for first_pixel, second_pixel in zip(a_pixels, b_pixels)
            )

    total_pixels = width * height
    frame_stats = []
    for current in stats:
        frame_stats.append(
            {
                "min": current["min"],
                "max": current["max"],
                "mean": round(current["sum"] / total_pixels, 3),
                "nonzero_percent": round(
                    current["nonzero"] / total_pixels * 100, 3
                ),
                "saturated_percent": round(
                    current["saturated"] / total_pixels * 100, 3
                ),
            }
        )
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "width": width,
        "height": height,
        "stride": stride,
        "frames": frame_stats,
        "frame_diff_percent": round(different / total_pixels * 100, 3),
    }


def analyze(path, width, height, stride):
    if np is None:
        return analyze_python(path, width, height, stride)

    data = path.read_bytes()
    frame_size = height * stride
    if len(data) != frame_size * 2:
        raise ValueError(f"{path}: expected {frame_size * 2}, got {len(data)}")
    frames = [
        unpack_raw10(
            np.frombuffer(data[offset : offset + frame_size], np.uint8),
            width,
            height,
            stride,
        )
        for offset in (0, frame_size)
    ]
    frame_stats = [
        {
            "min": int(frame.min()),
            "max": int(frame.max()),
            "mean": round(float(frame.mean()), 3),
            "nonzero_percent": round(
                float(np.count_nonzero(frame) / frame.size * 100), 3
            ),
            "saturated_percent": round(
                float(np.count_nonzero(frame >= 1023) / frame.size * 100), 3
            ),
        }
        for frame in frames
    ]
    diff = np.count_nonzero(frames[0] != frames[1]) / frames[0].size * 100
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "width": width,
        "height": height,
        "stride": stride,
        "frames": frame_stats,
        "frame_diff_percent": round(float(diff), 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    result = {}
    for name, (width, height, stride) in CAMERAS.items():
        result[name] = analyze(
            args.directory / f"two-{name}.raw", width, height, stride
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
