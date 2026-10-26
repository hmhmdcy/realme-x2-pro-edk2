#!/usr/bin/env python3
"""Validate current entry points, historical ownership, archives and mirror coverage."""
from pathlib import Path
from functools import lru_cache
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from fnmatch import fnmatch
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True


def load_manifest(root):
    return json.loads((root / "linux-port/scripts/docs-sync-manifest.json").read_text(encoding="utf-8"))


def public_module(root):
    spec = importlib.util.spec_from_file_location('public_docs', root/'linux-port/scripts/public-docs.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=None)
def resolved_directory(path):
    return path.resolve()


def safe_path(root, relative):
    root = resolved_directory(root)
    candidate = root / relative
    target = resolved_directory(candidate.parent) / candidate.name
    if target.is_symlink():
        target = target.resolve()
    if not target.is_relative_to(root) or target == root:
        raise ValueError(f"Path outside intended documentation root: {relative}")
    return target


def sync_files(root, manifest):
    paths = {Path(relative) for relative in manifest["files"]}
    for relative in manifest["directories"]:
        directory = safe_path(root, relative)
        if not directory.is_dir():
            raise ValueError(f"Missing directory: {relative}")
        for parent, directories, files in os.walk(directory):
            for name in directories + files:
                path = Path(parent) / name
                if path.is_symlink():
                    raise ValueError(f"Symlink not supported in documentation sync: {path.relative_to(root)}")
            paths.update((Path(parent) / name).relative_to(root) for name in files)
    for relative in manifest["files"]:
        if not safe_path(root, relative).is_file():
            raise ValueError(f"Missing sync file: {relative}")
    patterns = manifest.get('exclude', [])
    overrides = manifest.get('include_overrides', [])
    return sorted(path for path in paths if not any(fnmatch(path.as_posix(), pattern) for pattern in patterns) or any(fnmatch(path.as_posix(), pattern) for pattern in overrides))


def selected_files(root, manifest, requested):
    """Validate explicit manifest paths without walking unrelated history."""
    paths = set()
    for name in requested:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or path == Path("."):
            raise ValueError(f"Expected a workspace-relative file: {name}")
        target = safe_path(root, path)
        # Match full sync's refusal of symlinks, including linked parent directories.
        if any(part.is_symlink() for part in [root / path, *(root / path).parents] if part.is_relative_to(root)):
            raise ValueError(f"Symlink not supported in documentation sync: {name}")
        if not target.is_file():
            raise ValueError(f"Missing selected file: {name}")
        covered = path.as_posix() in manifest["files"] or any(
            path.is_relative_to(Path(directory)) for directory in manifest["directories"]
        )
        excluded = any(fnmatch(path.as_posix(), pattern) for pattern in manifest.get("exclude", []))
        override = any(fnmatch(path.as_posix(), pattern) for pattern in manifest.get("include_overrides", []))
        if not covered or (excluded and not override):
            raise ValueError(f"Selected file outside sync manifest: {name}")
        paths.add(path)
    return sorted(paths)


def selected_errors(root, manifest, files):
    errors = []
    for relative in files:
        if relative.suffix.lower() in (".md", ".mdx", ".txt"):
            errors += link_errors(root, relative)
        limit = manifest["size_limits"].get(relative.as_posix())
        if limit is not None and safe_path(root, relative).stat().st_size > limit:
            errors.append(f"Entry point grew beyond {limit} bytes: {relative}")
    return errors


def prose_lines(text):
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence):
                fence = None
            continue
        if match:
            fence = match[1]
        else:
            yield number, line


def heading_ids(path):
    counts = {}
    result = set()
    for _, line in prose_lines(path.read_text(encoding="utf-8-sig")):
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            text = re.sub(r"<[^>]+>", "", match[1]).lower()
            text = re.sub(r"[^\w\s-]", "", text)
            slug = re.sub(r"\s", "-", text)
            count = counts.get(slug, 0)
            counts[slug] = count + 1
            result.add(slug if count == 0 else f"{slug}-{count}")
    return result


LINK = re.compile(r"!?\[[^\]\n]*\]\((?:<([^>\n]+)>|([^\s)\n]+))(?:\s+[\"'][^\n]*?[\"'])?\)")


def link_errors(root, relative):
    path = safe_path(root, relative)
    errors = []
    for number, line in prose_lines(path.read_text(encoding="utf-8-sig")):
        for match in LINK.finditer(line):
            target = match[1] or match[2]
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            local = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not local.exists():
                errors.append(f"{relative}:{number}: missing link target {target}")
            elif parsed.fragment and local.is_file() and local.suffix.lower() == ".md":
                if unquote(parsed.fragment) not in heading_ids(local):
                    errors.append(f"{relative}:{number}: missing heading {target}")
    return errors


def archive_errors(root):
    errors = []
    count = 0
    for manifest in (root / "archive").glob("docs-before-maintenance-*/manifest.json"):
        for entry in json.loads(manifest.read_text(encoding="utf-8")):
            target = safe_path(manifest.parent, entry.get("snapshot_path", entry["path"]))
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
                errors.append(f"Archive hash mismatch: {target.relative_to(root)}")
            count += 1
    if not count:
        errors.append("No maintenance snapshot manifest found.")
    return errors, count


def history_errors(root):
    files = [root / "HANDOVER-NEXT.md"]
    for directory in ("reference", "sessions", "linux-port/docs"):
        files += list((root / directory).rglob("*.md"))
    owners = {number: [] for number in range(8, 31)}
    for path in files:
        content = path.read_text(encoding="utf-8-sig")
        for number in owners:
            if re.search(rf"(?m)^## {number}\. ", content):
                owners[number].append(str(path.relative_to(root)))
    return [f"Old section {number}: expected one owner, found {paths}"
            for number, paths in owners.items() if len(paths) != 1]


def mirror_errors(root, mirror, files):
    errors = []
    exporter = public_module(root)
    for relative in files:
        target = safe_path(mirror, relative)
        if not target.is_file():
            errors.append(f"Missing mirror file: {relative}")
        elif exporter.public_bytes(root, relative) != target.read_bytes():
            errors.append(f"Mirror drift: {relative}")
    return errors


def repo_errors(root, repo):
    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    text = (root / "HANDOVER-NEXT.md").read_text(encoding="utf-8")
    tips = re.findall(r"(?m)^    [^\n=]+ = ([0-9a-f]{7,40})\b", text)
    counts = re.findall(r"(?m)^    (\d+) commits ahead of upstream origin/master", text)
    if len(tips) != 1 or len(counts) != 1:
        return ["Expected one generated commit-history tip and upstream count."]
    errors = []
    if git("merge-base", "--is-ancestor", tips[0], "HEAD").returncode:
        errors.append("Recorded commit-history tip is not in this repository's HEAD history.")
    actual = git("rev-list", "--count", "origin/master.." + tips[0])
    if actual.returncode or actual.stdout.strip() != counts[0]:
        errors.append("Recorded upstream commit count does not match the named tip.")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--repo", type=Path, default=Path("/home/cy122/edk2-samurai/repo"))
    parser.add_argument("--mirror", type=Path)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--audit-history", action="store_true")
    parser.add_argument("--files", nargs="+", metavar="PATH", help="Check only these workspace-relative manifest files; skip historical/index/repo audits.")
    args = parser.parse_args()
    if args.files and args.audit_history:
        parser.error("--files and --audit-history select different check scopes")
    root = args.workspace.resolve()
    manifest = load_manifest(root)
    if args.files:
        try:
            files = selected_files(root, manifest, args.files)
            errors = selected_errors(root, manifest, files)
            if not args.local_only:
                errors += mirror_errors(root, args.mirror or args.repo / "Platform/Realme/sm8150", files)
        except (ValueError, OSError) as error:
            print(f"RESULT: {error}")
            return 1
        print(f"Checked {len(files)} selected files; historical, index and repository audits skipped.")
        for error in errors:
            print("  ERROR: " + error)
        print(f"RESULT: {len(errors)} problem(s)" if errors else "RESULT: clean (selected files)")
        return 1 if errors else 0
    errors = []
    print("Checking current navigation, size limits and generated index...", flush=True)
    for relative in manifest["entrypoints"]:
        if not (root / relative).is_file():
            errors.append(f"Missing entry point: {relative}")
        else:
            errors += link_errors(root, relative)
    for relative, limit in manifest["size_limits"].items():
        if (root / relative).stat().st_size > limit:
            errors.append(f"Entry point grew beyond {limit} bytes: {relative}")
    for relative in ("README.md", "linux-port/README.md", "HANDOVER-NEXT.md", "DOCS-INDEX.md"):
        for number, line in prose_lines((root / relative).read_text(encoding="utf-8")):
            if re.match(r"^(?:最新阶段|当前阶段|当前交接以|Previous kernel (?:audit|fix):)", line):
                errors.append(f"Accumulated stage-state paragraph: {relative}:{number}")
    spec = importlib.util.spec_from_file_location("session_index", root / "linux-port/scripts/generate-session-index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if (root / "sessions/INDEX.md").read_text(encoding="utf-8") != module.render(root):
        errors.append("Session/evidence index is stale; regenerate it.")
    errors += history_errors(root)
    hashes, hash_count = archive_errors(root)
    errors += hashes
    print("Checking documentation sync coverage...", flush=True)
    files = sync_files(root, manifest)
    covered = {path.as_posix() for path in files}
    for relative in manifest["entrypoints"]:
        if relative not in covered:
            errors.append(f"Entry point omitted from sync manifest: {relative}")
    if not args.local_only:
        print("Comparing source documents with the repository mirror...", flush=True)
        mirror = args.mirror or args.repo / "Platform/Realme/sm8150"
        errors += mirror_errors(root, mirror, files)
        errors += repo_errors(root, args.repo)
    if args.audit_history:
        warnings = []
        active = set(manifest["entrypoints"])
        for directory in ("reference", "sessions", "linux-port/docs"):
            for path in (root / directory).rglob("*.md"):
                relative = str(path.relative_to(root))
                if relative not in active:
                    warnings += link_errors(root, relative)
        print(f"Historical link warnings: {len(warnings)} (original experimental records preserved)")
        for warning in warnings[:20]:
            print("  WARN: " + warning)
    print(f"Checked {len(manifest['entrypoints'])} entry points, 23 old section owners, {hash_count} archived originals, {len(files)} sync files.")
    for error in errors[:40]:
        print("  ERROR: " + error)
    if len(errors) > 40:
        print(f"  ... {len(errors) - 40} more errors")
    if errors:
        print(f"RESULT: {len(errors)} problem(s)")
        return 1
    print("RESULT: clean (local only)" if args.local_only else "RESULT: clean (entry points and public mirror)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
