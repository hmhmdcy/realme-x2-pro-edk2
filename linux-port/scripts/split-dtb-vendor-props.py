#!/usr/bin/env python3
"""Build an OS-facing DTB and logdump FAT image without vendor match fields."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

VENDOR_PROPERTIES = (
    "qcom,msm-id",
    "qcom,board-id",
    "oppo,dtsi_no",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, env=None):
    return subprocess.run(
        [str(item) for item in command],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout


def decompile(dtc, source, target):
    subprocess.run(
        [str(dtc), "-I", "dtb", "-O", "dts", "-o", str(target), str(source)],
        check=True,
        capture_output=True,
        text=True,
    )
    return target.read_text(encoding="utf-8")


parser = argparse.ArgumentParser()
parser.add_argument("--source-dtb", required=True, type=Path)
parser.add_argument("--source-fat", required=True, type=Path)
parser.add_argument("--output-dir", required=True, type=Path)
parser.add_argument("--dtc", default="dtc", type=Path)
parser.add_argument("--fdtput", default="fdtput", type=Path)
parser.add_argument("--mcopy", default="mcopy", type=Path)
parser.add_argument("--mdir", default="mdir", type=Path)
parser.add_argument("--fsck-fat", default="fsck.fat", type=Path)
args = parser.parse_args()

for path in (args.source_dtb, args.source_fat):
    assert path.is_file(), path
args.output_dir.mkdir(parents=True, exist_ok=True)

os_dtb = args.output_dir / "samurai-os-dtb.dtb"
fat_image = args.output_dir / "logdump-os-dtb.img"
shutil.copyfile(args.source_dtb, os_dtb)
shutil.copyfile(args.source_fat, fat_image)

for prop in VENDOR_PROPERTIES:
    run([args.fdtput, "-d", os_dtb, "/", prop])

before_dts = decompile(
    args.dtc, args.source_dtb, args.output_dir / "source.dts")
after_dts = decompile(
    args.dtc, os_dtb, args.output_dir / "os-facing.dts")
expected = before_dts
removed = []
for prop in VENDOR_PROPERTIES:
    matches = [
        line for line in expected.splitlines()
        if line.strip().startswith(prop + " = ")
    ]
    assert len(matches) == 1, (prop, matches)
    removed.extend(matches)
    expected = "\n".join(
        line for line in expected.splitlines()
        if line not in matches
    ) + "\n"
assert after_dts == expected, "DTB split changed more than vendor properties"

env = {"MTOOLS_SKIP_CHECK": "1"}
subprocess.run(
    [str(args.mcopy), "-o", "-i", str(fat_image),
     str(os_dtb), "::/samurai.dtb"],
    check=True,
    env=env,
)
listing = run([args.mdir, "-b", "-i", fat_image, "::"]).splitlines()
assert sorted(listing) == ["::/Image", "::/samurai.dtb"], listing

image_readback = args.output_dir / "Image-readback"
dtb_readback = args.output_dir / "samurai-readback.dtb"
source_image = args.output_dir / "Image-source"
subprocess.run(
    [str(args.mcopy), "-o", "-i", str(fat_image),
     "::/Image", str(image_readback)],
    check=True,
    env=env,
)
subprocess.run(
    [str(args.mcopy), "-o", "-i", str(args.source_fat),
     "::/Image", str(source_image)],
    check=True,
    env=env,
)
subprocess.run(
    [str(args.mcopy), "-o", "-i", str(fat_image),
     "::/samurai.dtb", str(dtb_readback)],
    check=True,
    env=env,
)
assert image_readback.read_bytes() == source_image.read_bytes()
assert dtb_readback.read_bytes() == os_dtb.read_bytes()
run([args.fsck_fat, "-n", fat_image])

manifest = {
    "schema": "samurai-os-dtb-vendor-split-v1",
    "source_dtb": str(args.source_dtb),
    "source_dtb_sha256": sha256(args.source_dtb),
    "os_dtb": str(os_dtb),
    "os_dtb_sha256": sha256(os_dtb),
    "fat_image": str(fat_image),
    "fat_image_sha256": sha256(fat_image),
    "removed_root_properties": list(VENDOR_PROPERTIES),
    "removed_lines": removed,
    "fat_members": sorted(listing),
    "image_unchanged": image_readback.read_bytes()
    == source_image.read_bytes(),
    "dtb_readback_sha256": sha256(dtb_readback),
}
(args.output_dir / "result.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(manifest, indent=2, sort_keys=True))
