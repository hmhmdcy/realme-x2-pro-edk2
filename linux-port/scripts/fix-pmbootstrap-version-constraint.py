#!/usr/bin/env python3
"""Fix pmbootstrap's dependency check to compare the full version.

pmaports stores pkgver and pkgrel separately, but pmb/helpers/pmaports.py
passes only pkgver to check_version_constraints().  Any constraint that names
a release, e.g. ``unudhcpd>=0.5.0-r2``, then fails even when the local
APKBUILD satisfies it, so the package cannot be built at all.

Usage: fix-pmbootstrap-version-constraint.py [PMAPORTS_PY]
"""

from pathlib import Path
import sys

DEFAULT = Path("/home/cy122/samurai-build/pmbootstrap/pmb/helpers/pmaports.py")

OLD = '''        if pkgname_no_op == pkgname or pmb.helpers.package.check_version_constraints(
            pkgname, apkbuild["pkgver"]
        ):'''

NEW = '''        # pmaports stores pkgver and pkgrel separately; compare the full
        # version so a constraint such as ">=0.5.0-r2" can match the local
        # APKBUILD instead of failing on pkgver alone.
        full_version = f"{apkbuild['pkgver']}-r{apkbuild['pkgrel']}"
        if pkgname_no_op == pkgname or pmb.helpers.package.check_version_constraints(
            pkgname, full_version
        ):'''


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    text = path.read_text()
    if "full_version" in text:
        print(f"{path}: already patched")
        return 0
    if OLD not in text:
        print(f"{path}: anchor not found", file=sys.stderr)
        return 1
    path.write_text(text.replace(OLD, NEW, 1))
    print(f"{path}: patched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
