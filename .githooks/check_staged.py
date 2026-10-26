"""Fail a commit when staged content looks private, secret, or binary."""
import re
import subprocess
import sys

MAX_BYTES = 20 * 1024 * 1024
SECRET_PATTERNS = [
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"ghp_[A-Za-z0-9]{20,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
    r"AKIA[0-9A-Z]{16}",
    r"client_secret[[:space:]]*[:=][[:space:]]*['\"]?[A-Za-z0-9_./+-]{16,}",
    r"access_token[[:space:]]*[:=][[:space:]]*['\"]?[A-Za-z0-9_./+-]{16,}",
]
FORBIDDEN_NAMES = re.compile(
    r"(^|/)(\.env(\..*)?|\.git-credentials|\.netrc|_netrc|"
    r"id_rsa|id_dsa|id_ecdsa|id_ed25519|known_hosts(\..*)?|authorized_keys|"
    r".*\.(pem|key|p12|pfx|jks|keystore))$",
    re.I,
)
BINARY_MAGIC = (
    b"\x7fELF",
    b"MZ",
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
)


def staged_files():
    raw = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"]
    )
    return [item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item]


def binary_paths():
    raw = subprocess.check_output(["git", "diff", "--cached", "--numstat", "-z"])
    result = []
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        fields = entry.split(b"\t", 2)
        if len(fields) != 3:
            continue
        added, deleted, path = fields
        if added == b"-" and deleted == b"-":
            result.append(path.decode("utf-8", "surrogateescape"))
    return result


def main():
    failures = []
    paths = staged_files()
    for path in paths:
        if FORBIDDEN_NAMES.search(path):
            failures.append(f"{path}: forbidden key/credential filename")
    for path in binary_paths():
        failures.append(f"{path}: binary executable/object")

    # One index-wide grep, instead of spawning git once per staged path.
    argv = ["git", "grep", "--cached", "--full-name", "-I", "-l"]
    for pattern in SECRET_PATTERNS:
        argv.extend(["-e", pattern])
    grep = subprocess.run(argv, capture_output=True, text=True)
    if grep.returncode not in (0, 1):
        failures.append(f"git grep failed: {grep.stderr.strip()}")
    elif grep.returncode == 0:
        for path in grep.stdout.splitlines():
            failures.append(f"{path}: matched secret/key pattern")

    # Check oversized indexed blobs using one cat-file process.
    stage = subprocess.check_output(["git", "ls-files", "--stage", "-z"])
    objects = []
    for entry in stage.split(b"\0"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        _mode, object_id, _stage_no = meta.split(b" ", 2)
        objects.append((object_id, path.decode("utf-8", "surrogateescape")))
    if objects:
        batch = subprocess.run(
            ["git", "cat-file", "--batch-check=%(objectsize)"],
            input=b"".join(object_id + b"\n" for object_id, _ in objects),
            capture_output=True,
        )
        if batch.returncode:
            failures.append("git cat-file size check failed")
        else:
            sizes = batch.stdout.splitlines()
            if len(sizes) != len(objects):
                failures.append("git cat-file size check returned an unexpected count")
            else:
                for (_, path), size in zip(objects, sizes):
                    try:
                        if int(size) > MAX_BYTES:
                            failures.append(f"{path}: {size.decode()} bytes exceeds {MAX_BYTES}")
                    except ValueError:
                        failures.append(f"{path}: unreadable object size {size!r}")
    if failures:
        print("Commit blocked by repository safety checks:", file=sys.stderr)
        for failure in failures:
            print("  " + failure, file=sys.stderr)
        print("Remove or ignore these files, then retry the commit.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
