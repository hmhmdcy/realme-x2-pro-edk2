"""Compare the candidate against actual independently extracted OEM functions."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ORACLE = HERE.parent / 'charging-oem-audit-20261023/software-full'
OUT = Path('/home/cy122/charging-session-20261023')
OUT.mkdir(parents=True, exist_ok=True)
provenance = json.loads((ORACLE / 'reference-result.json').read_text())
assert provenance['passed'] and provenance['commit'] == '23172a1571bd91156032cc9fef16284a82b63d2c'
for name in ['reference-functions.c', 'test-reference.c']:
    digest = hashlib.sha256((ORACLE / name).read_bytes()).hexdigest()
    expected = next(value for path, value in provenance['files'].items()
                    if path.replace('\\', '/').endswith('/software-full/' + name))
    assert digest == expected, 'oracle changed: ' + name
command = ['gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           '-I' + str(HERE), str(HERE / 'test-oem-differential.c'),
           '-o', str(OUT / 'test-oem-differential')]
subprocess.run(command, check=True)
result = subprocess.run([str(OUT / 'test-oem-differential')], capture_output=True, text=True)
print(result.stdout, end='')
print(result.stderr, end='')
result.check_returncode()
report = json.loads(result.stdout)
report.update({
    'tested_files': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                     for name in ['oem-full-cycle.h', 'test-oem-differential.c']},
    'oracle_files': {name: hashlib.sha256((ORACLE / name).read_bytes()).hexdigest()
                      for name in ['reference-functions.c', 'test-reference.c', 'reference-result.json']},
    'sanitizers': ['ASan', 'UBSan'], 'command': command,
    'scope': 'Exact OEM predicates/counters at nominal OEM targets; excludes explicit safer continuity/CV/TCA adaptations',
    'phone_accessed': False, 'shared_kernel_or_sdk_modified': False,
})
(HERE / 'oem-differential-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
