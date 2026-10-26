"""Offline OEM normal-Full/recharge helper tests; no device access."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
OUT = Path('/home/cy122/charging-session-20261023')
OUT.mkdir(parents=True, exist_ok=True)
command = ['gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           '-I' + str(HERE), str(HERE / 'test-oem-full.c'),
           '-o', str(OUT / 'test-oem-full')]
subprocess.run(command, check=True)
result = subprocess.run([str(OUT / 'test-oem-full')], capture_output=True, text=True)
print(result.stdout, end='')
print(result.stderr, end='')
result.check_returncode()
report = json.loads(result.stdout)
report.update({
    'tested_files': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                     for name in ['oem-full-cycle.h', 'test-oem-full.c']},
    'sanitizers': ['ASan', 'UBSan'], 'command': command,
    'scope': 'Portable OEM ordinary Full/recharge candidate; not integrated, built as a module or tested on the phone',
    'phone_accessed': False, 'shared_kernel_or_sdk_modified': False,
})
(HERE / 'oem-full-test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
