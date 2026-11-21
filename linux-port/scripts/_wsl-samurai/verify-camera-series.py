#!/usr/bin/env python3
"""Replay the complete libcamera patch queue and verify the resulting tree."""
from pathlib import Path
from urllib.request import urlopen, Request
import argparse
import hashlib
import json
import os
import re
import subprocess
import tarfile


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def tree_digest(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode()
        if path.is_symlink():
            digest.update(b"L\0" + relative + b"\0" + os.readlink(path).encode() + b"\0")
        elif path.is_file():
            digest.update(b"F\0" + relative + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--work", type=Path, required=True)
args = parser.parse_args()
work = args.work.resolve()
work.mkdir(parents=True)

repo = Path(__file__).resolve().parents[1]
ports = repo / "temp/libcamera"
lock = json.loads((repo / "samurai/libcamera-source-lock.json").read_text())
version = lock["source_version"]
name = "libcamera-v" + version + ".tar.gz"
recipe = (ports / "APKBUILD").read_text()
expected = re.search(r"^([0-9a-f]{128})  " + re.escape(name) + r"$", recipe, re.M)[1]
url = "https://gitlab.freedesktop.org/camera/libcamera/-/archive/v" + version + "/" + name
data = urlopen(
    Request(url, headers={"User-Agent": "samurai-source-replay"}),
    timeout=90,
).read()
assert hashlib.sha512(data).hexdigest() == expected

archive = work / name
archive.write_bytes(data)
with tarfile.open(archive) as tar:
    tar.extractall(work, filter="data")
tree = work / ("libcamera-v" + version)

patches = sorted(ports.glob("00*.patch"))
assert len(patches) == lock["patch_count"], (len(patches), lock["patch_count"])
for patch in patches:
    result = subprocess.run(
        ["patch", "--fuzz=0", "-p1", "-i", str(patch)],
        cwd=tree,
        capture_output=True,
        text=True,
    )
    (work / (patch.stem + ".log")).write_text(result.stdout + result.stderr)
    assert result.returncode == 0, patch.name

actual_tree = tree_digest(tree)
expected_tree = lock.get("patched_tree_sha256")
if expected_tree:
    assert actual_tree == expected_tree, (actual_tree, expected_tree)

report = {
    "source_version": version,
    "package_version": lock["package_version"],
    "patch_count": len(patches),
    "zero_fuzz": True,
    "patched_tree_sha256": actual_tree,
    "patched_tree_checked_against_lock": bool(expected_tree),
    "source_sdk_used": False,
    "hardware_tested": False,
}
(work / "results.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
