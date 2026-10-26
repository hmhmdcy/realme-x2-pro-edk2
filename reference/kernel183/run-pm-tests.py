from pathlib import Path
import json
import os
import subprocess

os.umask(0o077)
root = Path('/var/lib/samurai')
assert os.uname().version.startswith('#183 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (root / 'k183-runtime/boot-id-private.txt').read_bytes()
out = root / 'k183-pm-sequence'
out.mkdir(mode=0o700)
for script, result in [('test-system-suspend.py', 'k183-suspend-idle'),
                       ('test-active-suspend.py', 'k183-suspend-active')]:
    (out / 'phase-private.json').write_text(json.dumps(dict(script=script, phase='dispatching')) + '\n')
    with (out / (script + '-private.log')).open('wb') as log:
        subprocess.run(['python3', '/tmp/k183-' + script], stdout=log, stderr=log, check=True)
    report = json.loads((root / result / 'validation.json').read_text())
    assert report['same_boot'] and report['taint'] == 0 and report['suspend_and_rtc_resume_passed'], report
    if result.endswith('active'):
        assert report['active_duplex_survived'], report['active_duplex']
(out / 'phase-private.json').write_text(json.dumps(dict(phase='completed', both_passed=True)) + '\n')
print('CURRENT183_IDLE45_AND_ACTIVE90_PM_PASSED', flush=True)
