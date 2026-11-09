#!/usr/bin/env python3
"""Remove only the debug-era PowerDevil AutoSuspendAction=0 overrides.

Dry-run by default. This never rewrites other PowerDevil settings and is
not installed by a package. Run it as the desktop user, then restart the
Plasma session so PowerDevil recomputes its upstream defaults.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path


PROFILE_GROUPS = {
    "[AC][SuspendAndShutdown]",
    "[Battery][SuspendAndShutdown]",
    "[LowBattery][SuspendAndShutdown]",
}
OVERRIDE = re.compile(r"^\s*AutoSuspendAction\s*=\s*0\s*$")


def default_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "powerdevilrc"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, default=default_path())
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    path = args.file
    if not path.is_file():
        print(f"no PowerDevil config: {path}")
        return 0

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    output: list[str] = []
    section = ""
    removed: list[int] = []
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped
        if section in PROFILE_GROUPS and OVERRIDE.match(line):
            removed.append(number)
            continue
        output.append(line)

    if not removed:
        print(f"no debug AutoSuspendAction=0 override in {path}")
        return 0

    print(f"{path}: remove AutoSuspendAction=0 lines {removed}")
    if not args.apply:
        print("dry-run only; pass --apply to write the file")
        return 0

    backup = path.with_suffix(path.suffix + ".samurai-debug.bak")
    shutil.copy2(path, backup)
    path.write_text("".join(output), encoding="utf-8")
    print(f"wrote {path}; backup {backup}")
    print("restart the Plasma session so PowerDevil recomputes defaults")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
