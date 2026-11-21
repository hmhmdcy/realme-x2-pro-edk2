#!/usr/bin/env python3
"""Audit APKBUILD version constraints without guessing from grep output.

pmaports recipes contain several look-alike version strings that are not
dependency pins at all:

  pkgver= / pkgrel=       plain variables
  provides="foo=1.2"      versioned "provides"; apk resolves against the
                          provider's own version and the comment in the tree
                          requires it to stay below the real package version
  depends="x=$pkgver-r$pkgrel"  a subpackage depending on its own parent

Only real dependency arrays matter here.  This tool parses those arrays
(including the ones declared inside subpackage functions), expands the few
variables APKBUILD authors actually use, and classifies every entry:

  exact       pkg=ver          hard pin
  fuzzy       pkg~ver          same version, any revision (pkg~ver-rN also
                               matches only that exact revision)
  lower       pkg>=ver         minimum version
  upper       pkg<=ver / <ver  maximum version
  self        dependency on the recipe's own parent version
  plain       no version
  conflict    !pkg

Usage:
    pkg-pin-audit.py --repo DIR [--json OUT] [--packages REGEX]

The default is a human-readable summary of exact pins; --json gives the
full machine-readable record for downstream checks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

DEP_VARS = ("depends", "makedepends", "checkdepends", "provider_pref")
INFO_VARS = ("provides",)

ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
FUNC_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\)\s*\{?")
VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
ENTRY_RE = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9@._+-]*)"
                      r"(?P<op>==|>=|<=|>~|<~|=|>|<|~)?(?P<ver>[^\s]*)$")


@dataclass
class Entry:
    package: str
    variable: str
    owner: str            # recipe that declares the dependency
    function: str | None  # subpackage function, if any
    raw: str
    name: str
    op: str | None
    version: str | None
    kind: str
    target_in_tree: str | None = None
    target_pkgver: str | None = None


def logical_lines(text: str):
    """Yield (lineno, text) with backslash continuations joined."""

    buf = ""
    start = 0
    for number, line in enumerate(text.splitlines(), 1):
        if not buf:
            start = number
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
            continue
        yield start, buf + line
        buf = ""
    if buf:
        yield start, buf


def read_value(lines, index, first: str):
    """Read a shell assignment value starting after the '='."""

    out: list[str] = []
    quote: str | None = None
    continued = False
    while True:
        text = first if not out and not continued else lines[index][1]
        i = 0
        while i < len(text):
            ch = text[i]
            if quote:
                if ch == "\\" and quote == '"' and i + 1 < len(text):
                    out.append(text[i + 1])
                    i += 2
                    continue
                if ch == quote:
                    quote = None
                else:
                    out.append(ch)
                i += 1
                continue
            if ch in "\"'":
                quote = ch
                i += 1
                continue
            if ch == "#":
                # A comment ends the assignment.
                return "".join(out).strip(), index
            if ch == "\\" and i + 1 >= len(text):
                continued = True
                i += 1
                break
            out.append(ch)
            i += 1
        if quote and not continued:
            # Inside a quoted string that spans lines: keep going.
            pass
        elif continued:
            continued = False
        else:
            break
        if index + 1 >= len(lines):
            break
        index += 1
        out.append("\n")
    return "".join(out).strip(), index


def expand(value: str, variables: dict) -> str:
    def repl(match: re.Match) -> str:
        name = match.group(1) or match.group(2)
        return variables.get(name, "${" + name + "}")

    return VAR_RE.sub(repl, value)


def parse_recipe(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    # Drop comments-only lines early; APKBUILD has no heredoc use in deps.
    lines = list(logical_lines(text))
    variables: dict[str, str] = {}
    deps: list[tuple[str, str | None, str]] = []   # var, function, value
    provides: list[tuple[str, str | None, str]] = []
    index = 0
    function = None
    while index < len(lines):
        _, line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        match = FUNC_RE.match(stripped)
        if match and not stripped.startswith("\t"):
            function = match.group(1)
            index += 1
            continue
        match = ASSIGN_RE.match(stripped)
        if match:
            name = match.group(1)
            value, index = read_value(lines, index, match.group(2))
            if function and index >= 0:
                pass
            if name in DEP_VARS:
                deps.append((name, function, value))
            elif name in INFO_VARS:
                provides.append((name, function, value))
            else:
                variables[name] = expand(value, variables)
            index += 1
            continue
        index += 1
    return variables, deps, provides


def find_in_tree(repo: Path, name: str):
    for path in repo.rglob(name + "/APKBUILD"):
        if ".git" in path.parts:
            continue
        return path
    return None


def repo_of(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).parts[0]
    except ValueError:
        return "."


def split_entries(value: str) -> list[str]:
    # Dependency arrays are whitespace separated; nothing else appears in
    # practice, so a plain split is faithful to what apk sees.
    return [part for part in value.split() if part]


def classify(entry: str, owner_vars: dict, owner: str,
             subpackages: set[str]) -> tuple[str, str | None, str | None, str]:
    if entry.startswith("!"):
        return entry[1:], "!", None, "conflict"
    match = ENTRY_RE.match(entry)
    if not match:
        return entry, None, None, "plain"
    name = match.group("name")
    op = match.group("op")
    version = match.group("ver") or None
    if name in ("",):
        return entry, None, None, "plain"
    if not op or not version:
        return name, None, None, "plain"
    if op == "=":
        own_version = f"{owner_vars.get('pkgver')}-r{owner_vars.get('pkgrel')}"
        if version == own_version and (name == owner or name in subpackages):
            return name, op, version, "self"
        kind = "exact"
    elif op == "~":
        kind = "fuzzy"
    elif op == ">=":
        kind = "lower"
    elif op in ("<=", "<"):
        kind = "upper"
    else:
        kind = "other"
    return name, op, version, kind


def audit(repo: Path, only: re.Pattern | None) -> list[Entry]:
    results: list[Entry] = []
    target_cache: dict[str, tuple[str | None, str | None]] = {}
    for path in sorted(repo.rglob("APKBUILD")):
        if ".git" in path.parts:
            continue
        rel = path.parent.relative_to(repo).as_posix()
        if only and not only.search(rel):
            continue
        variables, deps, _provides = parse_recipe(path)
        owner = variables.get("pkgname") or path.parent.name
        subpackages = {
            part.split(":")[0].replace("$pkgname", owner)
            for part in split_entries(expand(variables.get("subpackages", ""), variables))
        }
        for variable, function, raw in deps:
            for item in split_entries(expand(raw, variables)):
                name, op, version, kind = classify(item, variables, owner, subpackages)
                if kind == "plain" and not op:
                    # Quick check: a bare dependency still matters for the
                    # "target not in this tree" report.
                    pass
                if name not in target_cache:
                    found = find_in_tree(repo, name)
                    if found:
                        tvars, _, _ = parse_recipe(found)
                        target_cache[name] = (
                            repo_of(repo, found),
                            tvars.get("pkgver"),
                        )
                    else:
                        target_cache[name] = (None, None)
                target_repo, target_pkgver = target_cache[name]
                results.append(Entry(
                    package=rel,
                    variable=variable,
                    owner=owner,
                    function=function,
                    raw=item,
                    name=name,
                    op=op,
                    version=version,
                    kind=kind,
                    target_in_tree=target_repo,
                    target_pkgver=target_pkgver,
                ))
    return results


def version_matches(pin: str, actual: str | None, fuzzy: bool = False) -> bool | None:
    if actual is None:
        return None
    base = pin.replace("$pkgver", actual)
    if fuzzy and "-r" not in base:
        # "~ver" ignores the revision, so compare the version part only.
        return base == actual.split("-r")[0]
    return base == actual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=Path("/home/cy122/samurai-dist-repo"))
    parser.add_argument("--json", type=Path)
    parser.add_argument("--packages", help="regex filter on the recipe path")
    parser.add_argument("--stale", action="store_true",
                        help="only print exact pins whose recipe version differs")
    args = parser.parse_args()

    if not args.repo.is_dir():
        print(f"no such repo: {args.repo}", file=sys.stderr)
        return 2
    only = re.compile(args.packages) if args.packages else None
    entries = audit(args.repo, only)

    counts: dict[str, int] = {}
    for e in entries:
        counts[e.kind] = counts.get(e.kind, 0) + 1

    rows = [e for e in entries if e.kind in ("exact", "fuzzy", "upper", "other")
            or (e.kind == "lower" and e.target_in_tree is None)]
    if args.stale:
        rows = [e for e in rows if e.kind == "exact"
                and version_matches(e.version or "", e.target_pkgver) is False]

    for e in rows:
        where = f"{e.package}:{e.variable}"
        if e.function:
            where += f" [{e.function}()]"
        verdict = ""
        if e.kind in ("exact", "fuzzy"):
            same = version_matches(e.version or "", e.target_pkgver, e.kind == "fuzzy")
            if same is True:
                verdict = "pin == in-tree version"
            elif same is False:
                verdict = f"STALE: pinned {e.version}, tree has {e.target_pkgver}"
            else:
                verdict = "target not in this tree"
        elif e.target_in_tree is None:
            verdict = "target comes from an external repository"
        print(f"{e.kind:9} {e.raw:46} {where}  {verdict}")

    print()
    print("summary:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if args.json:
        args.json.write_text(json.dumps({
            "repo": str(args.repo),
            "counts": counts,
            "entries": [asdict(e) for e in entries if e.kind != "plain"],
        }, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
