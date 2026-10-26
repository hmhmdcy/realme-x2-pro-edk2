#!/usr/bin/env python3
"""Refresh the marked local commit-history block; do not change repository state."""
from pathlib import Path
import argparse
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--repo", type=Path, default=Path("/home/cy122/edk2-samurai/repo"))
    args = parser.parse_args()
    def git(*arguments):
        return subprocess.run(["git", "-C", str(args.repo), *arguments], capture_output=True,
                              text=True, check=True).stdout.strip()
    path = args.workspace / "HANDOVER-NEXT.md"
    text = path.read_text(encoding="utf-8")
    pattern = r"(?s)(<!-- repo-state:start -->\n).*?(<!-- repo-state:end -->)"
    if len(re.findall(pattern, text)) != 1:
        raise SystemExit("Expected one marked repo-state block in HANDOVER-NEXT.md.")
    branch = git("branch", "--show-current") or "detached-HEAD"
    history = git("log", "--oneline", "-5").splitlines()
    tip = history[0].split()[0]
    ahead = git("rev-list", "--count", "origin/master.." + tip)
    lines = [f"    {branch} = {history[0]}", *["             " + line for line in history[1:]], "",
             f"    {ahead} commits ahead of upstream origin/master, as of the tip named above;", "",
             "    fork remote: https://github.com/hmhmdcy/edk2-realme-x2-pro", "",
             "此块不证明未提交改动已构建、已部署或已推送；状态由本地git与检查点核对。", ""]
    updated = re.sub(pattern, lambda m: m[1] + "\n".join(lines) + "\n" + m[2], text)
    if updated != text:
        path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"Repo history refreshed at {tip}; working changes remain untouched.")


if __name__ == "__main__":
    main()
