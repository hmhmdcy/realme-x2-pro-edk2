"""Test-only external-I/O fixture for running the original hooks with real APK3.

APK3 supplies /proc inside its script sandbox. Its /proc has no device tree on
the WSL test host. This adapter changes only that read path in the executed
script; every original signed hook is saved verbatim for SHA verification.
It is never used by the installer or restoration tool and is not deployable.
"""
from pathlib import Path
import re
import shutil
import subprocess


def copy_utility(root, name, destination=None):
    source = Path(shutil.which(name))
    target = root / 'bin' / (destination or name)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(0o755)
    for path in re.findall(r'(/[^\s()]+)', subprocess.check_output(['ldd', str(source)], text=True)):
        library = root / path.lstrip('/')
        library.parent.mkdir(parents=True, exist_ok=True)
        if not library.exists():
            shutil.copyfile(path, library)
            library.chmod(0o755)


def prepare(root, release):
    for name in ['dash', 'tr', 'grep', 'sha256sum', 'sed', 'cat']:
        copy_utility(root, name)
    fixture = root / 'samurai-fixture'
    fixture.mkdir(exist_ok=True)
    (fixture / 'compatible').write_bytes(b'realme,samurai\0qcom,sm8150\0')
    (root / 'bin/uname').write_text('#!/bin/dash\nprintf "%s\\n" "' + release + '"\n')
    (root / 'bin/uname').chmod(0o755)
    process_state(root, 1)
    shell = root / 'bin/sh'
    shell.write_text('''#!/bin/dash
case "${1:-}" in
 /proc/self/fd/*|lib/apk/exec/*|/lib/apk/exec/*)
    fixture=/samurai-fixture/executed-hook.$$
    cat "$1" > "$fixture.original"
    sed 's,/proc/device-tree/compatible,/samurai-fixture/compatible,g' "$fixture.original" > "$fixture.adapted"
    shift
    exec /bin/dash "$fixture.adapted" "$@"
    ;;
 *) exec /bin/dash "$@" ;;
esac
''')
    shell.chmod(0o755)


def process_state(root, status):
    path = root / 'bin/pgrep'
    path.write_text('#!/bin/dash\nexit ' + str(status) + '\n')
    path.chmod(0o755)
