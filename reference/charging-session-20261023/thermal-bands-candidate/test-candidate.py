"""Host-only actual candidate functions and independent OEM differential."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'kernel-v2'
baseline = json.loads((HERE / 'baseline.json').read_text())
original = {n: hashlib.sha256((BASE / n).read_bytes()).hexdigest() for n in baseline}
assert original == baseline
oracle = json.loads((HERE / 'oracle-result.json').read_text())
assert oracle['passed'] and oracle['assertions'] == 97
# Preserve the completed independent oracle; do not rerun its build/test.
oracle_before = (HERE / 'oracle-result.json').read_bytes()
source = (HERE / 'samurai-mp2650.c').read_text()
start = source.index('static int sm_step_locked('); end = source.index('\n}\n', start) + 3
body = source[start:end]; (HERE / 'sm-step-extracted.inc').write_bytes(body.encode())
test = (BASE / 'test-step.c').read_text().replace('c->thermal.hold = SM_THERMAL_NONE;', 'c->thermal = (struct sm_thermal_state){ 0 };')
# OEM's native hot status is strict >530. Its absolute 530 stop is an
# intentional r6 safety overlay, not authorization for a new 2 C latch.
test = test.replace('temp_decic = 530', 'temp_decic = 531')
point = '\tprintf("{\\"integration_sequences'
where = test.index(point)
test = test[:where] + (HERE / 'extra-step.inc').read_text() + '\n' + test[where:]
(HERE / 'test-step.c').write_bytes(test.encode())
linux = '/mnt/e/RealmeX2Pro edk2/reference/charging-session-20261023/thermal-bands-candidate'
results = {}
for name in ['test-differential', 'test-step']:
    command = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--', 'gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
               '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-I' + linux,
               linux + '/' + name + '.c', '-o', linux + '/' + name]
    subprocess.run(command, check=True)
    done = subprocess.run(['wsl', '-d', 'Ubuntu', '-u', 'root', '--', linux + '/' + name], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    results[name] = dict(result=json.loads(done.stdout), command=command)
assert original == {n: hashlib.sha256((BASE / n).read_bytes()).hexdigest() for n in baseline}
assert (HERE / 'oracle-result.json').read_bytes() == oracle_before
names = ['samurai-mp2650.c', 'mp2650-core.h', 'oem-full-cycle.h', 'thermal-bands.h']
patch = ''
for name in names:
    before = (BASE / name).read_text() if (BASE / name).exists() else ''
    after = (HERE / name).read_text()
    patch += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                   fromfile='a/' + name if before else '/dev/null', tofile='b/' + name))
(HERE / 'thermal-bands.patch').write_bytes(patch.encode())
receipt = dict(passed=True, tests=results, extracted_step_sha256=hashlib.sha256(body.encode()).hexdigest(),
               files={n: hashlib.sha256((HERE / n).read_bytes()).hexdigest() for n in names},
               test_files={n: hashlib.sha256((HERE / n).read_bytes()).hexdigest() for n in
                    ['test-candidate.py','test-differential.c','test-step.c','extra-step.inc',
                     'oracle-fixture.h','oracle-functions.inc','oracle-limits.inc','oracle-limit-fields.inc','oracle-result.json']},
               baseline=baseline, frozen_v2_unchanged=True, completed_oracle_97_unchanged=True,
               patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
               phone_accessed=False, sdk_accessed=False, shared_source_modified=False,
               scope='single OEM effective band, inherited caps; explicit stricter immutable outer stop and conservative Full continuity')
(HERE / 'test-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
