#!/usr/bin/env python3
"""Local protocol tests only. No phone, SDK, source mount or deploy path."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-g']
    with tempfile.TemporaryDirectory(prefix='samurai-apsd-once-') as tmp:
        binary = Path(tmp) / 'test-once'
        subprocess.run(['cc', *flags, str(ROOT / 'test-once.c'), '-o', str(binary)],
                       check=True, capture_output=True, text=True)
        env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:abort_on_error=1',
                   UBSAN_OPTIONS='halt_on_error=1')
        result = subprocess.run([str(binary)], check=False, capture_output=True,
                                text=True, env=env)
        if result.returncode:
            print(result.stdout, end='')
            print(result.stderr, end='')
            result.check_returncode()
        assert result.stdout == '14 protocol groups passed\n' and not result.stderr
    report = {
        'passed': True,
        'scope': 'serialized protocol core only; actual header functions',
        'groups': 14, 'compiler_flags': flags,
        'stdout': result.stdout.strip(),
        'files_sha256': {n: sha(ROOT / n) for n in
                         ['samurai-apsd-once.h', 'test-once.c', 'run-tests.py']},
        'hardware_accessed': False, 'sdk_accessed': False,
        'kernel_build_or_link_proven': False,
        'hardware_owner_or_pd_inactive_proven': False,
        'apsd_or_budget_or_icon_accepted': False,
        'affected_previous_protocol_groups_rerun': 13,
        'other_component_test_suites_rerun': False,
    }
    (ROOT / 'test-result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
