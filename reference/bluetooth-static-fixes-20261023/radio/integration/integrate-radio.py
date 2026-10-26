#!/usr/bin/env python3
"""Stage a helper-only samurai-platform recipe delta; never build/install an APK."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

HERE = Path(__file__).resolve().parent
NAME = "usr_sbin_samurai-radio-address"
TARGET = "usr/sbin/samurai-radio-address"


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(data, algorithm="sha256"):
    return hashlib.new(algorithm, data).hexdigest()


def regular(path):
    require(stat.S_ISREG(path.lstat().st_mode), f"not a regular, non-symlink file: {path}")
    return path.read_bytes()


def skeleton(recipe):
    text = recipe.replace("\r\n", "\n")
    text, count = re.subn(r"(?m)^pkgrel=[0-9]+$", "pkgrel=<NEXT>", text)
    require(count == 1, "expected one numeric pkgrel")
    text, count = re.subn(r'(?ms)^sha512sums="\n.*?^"\n?\Z', 'sha512sums="<LOCKED_SOURCES>"\n', text)
    require(count == 1, "unsupported checksum block")
    return digest(text.encode())


def inventory(root):
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        require(stat.S_ISDIR(mode) or stat.S_ISREG(mode), f"unexpected staged object: {relative}")
        if stat.S_ISREG(mode):
            data = path.read_bytes()
            result[relative] = {"bytes": len(data), "sha256": digest(data), "mode": oct(stat.S_IMODE(mode))}
    return result


def integrate(baseline, expected_recipe_hash, output):
    lock = json.loads(regular(HERE / "source-lock.json"))
    baseline = baseline.resolve(strict=True)
    recipe_path = baseline / "APKBUILD"
    original = regular(recipe_path)
    require(digest(original) == expected_recipe_hash, "baseline APKBUILD SHA256 mismatch")
    recipe = original.decode("utf-8")
    require(skeleton(recipe) == lock["recipe_skeleton_sha256"], "recipe structure/dependencies/package() differ; re-review required")
    text = recipe.replace("\r\n", "\n")
    sources_match = re.search(r'(?m)^source="([^"\n]+)"$', text)
    require(sources_match is not None, "unsupported source list")
    sources = sources_match.group(1).split()
    require(len(sources) == 19 and len(set(sources)) == 19, "expected 19 unique local sources")
    require(all(PurePosixPath(name).name == name and name not in (".", "..") for name in sources), "source path is not flat")
    checksum_block = re.search(r'(?ms)^sha512sums="\n(.*?)"\n?\Z', text)
    require(checksum_block is not None and re.fullmatch(r"(?:[0-9a-f]{128}  [A-Za-z0-9_.-]+\n){19}", checksum_block.group(1)), "checksum block must contain only 19 literal checksum lines")
    checksum_pairs = re.findall(r"(?m)^([0-9a-f]{128})  ([A-Za-z0-9_.-]+)$", checksum_block.group(1))
    checksums = {name: sha for sha, name in checksum_pairs}
    require(len(checksum_pairs) == 19 and set(checksums) == set(sources), "incomplete/duplicate checksum list")
    inputs = {}
    source_bytes = {}
    for name in sources:
        data = regular(baseline / name)
        require(digest(data, "sha512") == checksums[name], f"source SHA512 mismatch: {name}")
        source_bytes[name] = data
        inputs[name] = {"bytes": len(data), "sha256": digest(data), "sha512": checksums[name]}
    require(inputs[NAME]["sha256"] == lock["old_helper_sha256"], "helper baseline changed/already fixed; rebase explicitly")
    replacement = regular(HERE.parent / NAME)
    require(digest(replacement) == lock["new_helper_sha256"] and digest(replacement, "sha512") == lock["new_helper_sha512"], "replacement source lock mismatch")
    release = int(re.search(r"(?m)^pkgrel=([0-9]+)$", text).group(1))
    require(release >= 2, "unsupported historical pkgrel")
    candidate = re.sub(r"(?m)^pkgrel=[0-9]+(?=\r?$)", f"pkgrel={release + 1}", recipe)
    checksum_line = f"{checksums[NAME]}  {NAME}"
    require(candidate.count(checksum_line) == 1, "helper checksum is not unique")
    candidate = candidate.replace(checksum_line, f"{lock['new_helper_sha512']}  {NAME}")
    require(skeleton(candidate) == lock["recipe_skeleton_sha256"], "candidate changed recipe structure")
    # Only metadata above changed; the source directory is a private shallow overlay.
    # Eighteen links read their already-checksummed baseline files; install creates
    # independent regular payload files with the real recipe's requested modes.
    require(os.name == "posix" and Path("/bin/sh").is_file(), "staging requires Linux /bin/sh")
    require(output.is_absolute() and not output.exists() and not output.is_symlink(), "output must be a new absolute directory")
    parent = output.parent.resolve(strict=True)
    output = parent / output.name
    repo = HERE.parents[3]
    require(not output.is_relative_to(repo) and not output.is_relative_to(baseline), "output must be outside the repository/baseline")
    output.mkdir(mode=0o700)
    overlay = output / "source-overlay"
    overlay.mkdir(mode=0o700)
    for name in sources:
        if name == NAME:
            (overlay / name).write_bytes(replacement)
        else:
            (overlay / name).symlink_to(baseline / name)
    (overlay / "APKBUILD").write_bytes(candidate.encode())
    patch = "".join(difflib.unified_diff(text.splitlines(True), candidate.replace("\r\n", "\n").splitlines(True), fromfile="a/APKBUILD", tofile="b/APKBUILD"))
    (output / "APKBUILD.patch").write_text(patch)
    inventories = {}
    for label, script, srcdir in (("before", recipe, baseline), ("after", candidate, overlay)):
        script_path = output / f"{label}-execution.APKBUILD"
        # Normalize shell syntax only; staged source bytes remain unmodified.
        script_path.write_text(script.replace("\r\n", "\n"))
        payload = output / f"{label}-payload"
        payload.mkdir(mode=0o700)
        env = dict(os.environ, srcdir=str(srcdir), pkgdir=str(payload))
        completed = subprocess.run(["/bin/sh", "-c", 'set -eu; . "$1"; package', "stage", str(script_path)], env=env, capture_output=True, text=True)
        (output / f"{label}-package.log").write_text(completed.stdout + completed.stderr)
        require(completed.returncode == 0, f"actual {label} package() failed; see private log")
        inventories[label] = inventory(payload)
        install_map = re.findall(r'install -Dm([0-7]{3}) "\$srcdir"/([A-Za-z0-9_.-]+) "\$pkgdir"/([^\s]+)', script)
        require(len(install_map) == 19 and len({x[2] for x in install_map}) == 19, "unsupported package install map")
        require(set(inventories[label]) == {target for _, _, target in install_map}, "staged inventory differs from package()")
        for mode, name, target in install_map:
            expected = replacement if label == "after" and name == NAME else source_bytes[name]
            actual = inventories[label][target]
            require(actual["sha256"] == digest(expected) and actual["mode"] == oct(int(mode, 8)), f"staged bytes/mode mismatch: {label}/{target}")
    changed = [name for name in inventories["before"] if inventories["before"][name] != inventories["after"][name]]
    require(changed == [TARGET], "payload delta is not helper-only")
    require(inventories["before"][TARGET]["mode"] == inventories["after"][TARGET]["mode"] == "0o755", "helper mode changed")
    require(regular(recipe_path) == original, "baseline recipe changed during staging")
    require(all(regular(baseline / name) == source_bytes[name] for name in sources), "baseline source changed during staging")
    report = {
        "schema": 1, "passed": True,
        "scope": "offline_actual_package_staging_only_not_an_apk_or_deployment",
        "historical_fixture": expected_recipe_hash == lock["historical_fixture"]["recipe_sha256"],
        "baseline_recipe_sha256": expected_recipe_hash,
        "candidate_recipe_sha256": digest(candidate.encode()),
        "baseline_version": f"5-r{release}", "candidate_version": f"5-r{release + 1}",
        "source_inputs": inputs, "replacement_sha256": digest(replacement),
        "all_source_sha512_checked": True, "actual_package_executions": 2,
        "payloads": inventories, "changed_payloads": changed,
        "unchanged_payloads": 18, "helper_mode_preserved": "0755",
        "baseline_unchanged": True, "other_source_files_copied": 0,
        "new_package_name_or_owner": False, "apk_built_signed_installed": False,
        "current_complete_platform_baseline_confirmed": False,
        "device_sdk_service_accessed": False,
    }
    (output / "staging-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--baseline-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{64}", args.baseline_sha256), "invalid recipe hash")
    report = integrate(args.baseline, args.baseline_sha256, args.output)
    print(json.dumps({"passed": report["passed"], "candidate_version": report["candidate_version"], "changed_payloads": report["changed_payloads"], "apk_built": False}))


if __name__ == "__main__":
    main()
