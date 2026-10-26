"""Compile actual candidate function bodies with recording transport boundaries.

Run on WSL Linux (not in the camera SDK). Outputs remain in this audit directory.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parent
source = (ROOT / 'candidate/samurai-mp2650.c').read_text()
before = (ROOT / 'before-notification-samurai-mp2650.c').read_text()


def function(text, name):
    # All selected bodies have balanced C braces and no brace-containing strings.
    match = re.search(r'^static (?:int|bool|void) ' + re.escape(name) + r'\(', text, re.M)
    assert match, name
    opening = text.index('{', match.start())
    depth = 1
    index = opening + 1
    while depth:
        depth += (text[index] == '{') - (text[index] == '}')
        index += 1
    return text[match.start():index]


unchanged = ['sm_step_locked', 'sm_collect', 'sm_gauge_sample', 'sm_set_property',
             'sm_supply_changed', 'sm_get_property', 'sm_suspend', 'sm_cleanup']
assert all(function(source, name) == function(before, name) for name in unchanged)
actual = '\n\n'.join(function(source, name) for name in ['sm_notification_locked', 'sm_poll', 'sm_resume'])
harness = (ROOT / 'test-notification.c.in').read_text()
assert harness.count('/* ACTUAL_FUNCTIONS */') == 1
(ROOT / 'test-notification-generated.c').write_text(harness.replace('/* ACTUAL_FUNCTIONS */', actual))
command = ['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-g',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           '-I' + str(ROOT / 'candidate'), str(ROOT / 'test-notification-generated.c'),
           '-o', str(ROOT / 'test-notification-bin')]
subprocess.run(command, check=True)
result = subprocess.run([str(ROOT / 'test-notification-bin')], text=True, capture_output=True)
print(result.stdout, end='')
print(result.stderr, end='')
result.check_returncode()
report = json.loads(result.stdout)
report.update(scope='Actual candidate notification/poll/resume functions with simulated kernel boundaries; no kernel-module/hardware acceptance',
              unchanged_functions=unchanged, sanitizers=['ASan', 'UBSan'], command=command,
              tested_files={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in [
                  'candidate/samurai-mp2650.c', 'candidate/charging-notify.h', 'test-notification.c.in',
                  'test-notification-generated.c', 'test-notification.py']})
(ROOT / 'notification-test-result.json').write_text(json.dumps(report, indent=2) + '\n')
