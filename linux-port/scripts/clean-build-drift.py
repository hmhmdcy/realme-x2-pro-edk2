#!/usr/bin/env python3
"""Measure how far the delivery image is from the official stable channel.

Every installed package is looked up in the official repository indices for
the channel the image claims to target.  The result is a complete, offline
statement of what a "clean official stable build" would have to change:

  match          the image already carries the version the channel publishes
  stripped       same upstream build, only postmarketOS' 9999 rebuild prefix
                 differs; a plain reinstall removes it without changing code
  drifted        the image carries a different version than the channel offers
  absent         no configured official repository publishes this name (board
                 packages and local additions land here by design)

This never contacts a device and never writes to a root.
"""
from pathlib import Path
import argparse
import json
import re
import sys
import tarfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--index", type=Path, action="append", required=True,
               help="APKINDEX.tar.gz; repeat for each repository, in priority order")
p.add_argument("--db", type=Path, required=True)
p.add_argument("--json", type=Path)
p.add_argument("--show", choices=["drifted", "absent", "stripped"], action="append")
args = p.parse_args()

# Packages that exist only in this port.  They cannot come from any upstream
# repository, so "absent" is their correct classification and not a defect.
BOARD = re.compile(
    r"^(samurai-|device-realme-samurai|usb-signaller|unudhcpd"
    r"|libcamera-samurai|mesa-vulkan-freedreno-samurai)"
)


def read_index(path, label):
    """name -> (version, label), first record wins within one repository."""
    out = {}
    with tarfile.open(path, "r:gz") as archive:
        try:
            member = archive.extractfile("APKINDEX")
        except KeyError:
            return out
        if member is None:
            return out
        text = member.read().decode("utf-8", "replace")
    name = version = None
    for line in text.splitlines():
        if line.startswith("P:"):
            name = line[2:]
        elif line.startswith("V:") and name:
            version = line[2:]
        elif not line:
            if name and version and name not in out:
                out[name] = (version, label)
            name = version = None
    if name and version and name not in out:
        out[name] = (version, label)
    return out


def read_db(path):
    rows = []
    name = version = None
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("P:"):
            name = line[2:]
        elif line.startswith("V:") and name:
            version = line[2:]
        elif not line:
            if name and version:
                rows.append((name, version))
            name = version = None
    if name and version:
        rows.append((name, version))
    return rows


official = {}
labels = []
for path in args.index:
    label = path.parent.name if path.parent.name != "work" else path.stem
    labels.append(label)
    for name, (version, source) in read_index(path, label).items():
        official.setdefault(name, (version, source))

installed = read_db(args.db)
buckets = {"match": [], "stripped": [], "drifted": [], "absent": []}

for name, version in sorted(installed):
    entry = official.get(name)
    if entry is None:
        buckets["absent"].append({
            "name": name, "installed": version,
            "board": bool(BOARD.match(name)),
        })
        continue
    want, source = entry
    if version == want:
        buckets["match"].append({"name": name, "version": version,
                                 "repo": source})
    elif re.sub(r"^9999", "", version) == want:
        buckets["stripped"].append({
            "name": name, "installed": version, "official": want,
            "repo": source,
        })
    else:
        buckets["drifted"].append({
            "name": name, "installed": version, "official": want,
            "repo": source,
            "prefix_only": re.sub(r"^9999", "", version).split("-r")[0]
            == want.split("-r")[0],
        })

print("installed packages: %d" % len(installed))
print("repositories: %s" % ", ".join(labels))
print()
total = len(installed) or 1
for key, text in (
    ("match", "already the official version"),
    ("stripped", "same upstream, only the 9999 rebuild prefix differs"),
    ("drifted", "image version differs from the channel"),
    ("absent", "no official repository publishes this name"),
):
    count = len(buckets[key])
    print("  %-9s %4d  (%5.1f%%)  %s"
          % (key, count, 100.0 * count / total, text))

absent_board = sum(1 for item in buckets["absent"] if item["board"])
absent_other = len(buckets["absent"]) - absent_board
print()
print("  of the absent set: %d board packages (expected), %d unexpected"
      % (absent_board, absent_other))

show = set(args.show or ["drifted", "absent"])
for key in ("drifted", "absent", "stripped"):
    if key not in show:
        continue
    rows = buckets[key]
    if not rows:
        continue
    print()
    print("== %s (%d) ==" % (key, len(rows)))
    for item in rows:
        if key == "absent" and item["board"]:
            continue
        if key == "absent":
            print("  %-34s %s" % (item["name"], item["installed"]))
        else:
            print("  %-34s %-20s -> %-20s [%s]"
                  % (item["name"], item["installed"], item["official"],
                     item["repo"]))

if args.json:
    args.json.write_text(json.dumps({
        "schema": "samurai-clean-build-drift-v1",
        "installed": len(installed),
        "repositories": labels,
        "counts": {k: len(v) for k, v in buckets.items()},
        "absent_board": absent_board,
        "absent_unexpected": absent_other,
        **{k: v for k, v in buckets.items()},
    }, indent=2) + "\n")

sys.exit(0)
