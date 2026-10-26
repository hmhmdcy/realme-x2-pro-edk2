"""Compile the exact production sm_step_locked body against its real helpers."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
PRODUCTION = HERE.parent / 'charging-management-20261023'
OUT = Path('/home/cy122/charging-session-20261023')
OUT.mkdir(parents=True, exist_ok=True)
source = (PRODUCTION / 'samurai-mp2650.c').read_text()
start = source.index('static int sm_step_locked(struct sm_charger *c)\n{')
end = source.index('\n}\n', start) + 3
step = source[start:end]
(HERE / 'sm-step-extracted.inc').write_text(step)
# Production include path must precede the candidate directory: this verifies
# the integrated headers, including future changes, rather than stale copies.
command = ['gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           '-I' + str(PRODUCTION), '-I' + str(HERE),
           str(HERE / 'test-integrated-step.c'), '-o', str(OUT / 'test-integrated-step')]
subprocess.run(command, check=True)
result = subprocess.run([str(OUT / 'test-integrated-step')],
                        capture_output=True, text=True)
print(result.stdout, end='')
print(result.stderr, end='')
result.check_returncode()
report = json.loads(result.stdout)
names = ['samurai-mp2650.c', 'mp2650-core.h', 'charge-cycle.h', 'oem-profile.h']
report.update({
    'production_files': {name: hashlib.sha256((PRODUCTION / name).read_bytes()).hexdigest()
                         for name in names},
    'extracted_function_sha256': hashlib.sha256(step.encode()).hexdigest(),
    'harness_sha256': hashlib.sha256((HERE / 'test-integrated-step.c').read_bytes()).hexdigest(),
    'sanitizers': ['ASan', 'UBSan'], 'command': command,
    'scope': 'Exact production sm_step_locked and headers; fake collection/BOOTTIME/register bus boundaries',
    'phone_accessed': False, 'shared_kernel_or_sdk_modified': False,
})
(HERE / 'integration-test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
