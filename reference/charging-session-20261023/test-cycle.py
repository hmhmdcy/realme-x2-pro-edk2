"""Run pure cycle fault/boundary tests. No phone, SDK or shared kernel access."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
OUT = Path('/home/cy122/charging-session-20261023')
OUT.mkdir(parents=True, exist_ok=True)
command = ['gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           '-I' + str(HERE), str(HERE / 'test-charge-cycle.c'),
           '-o', str(OUT / 'test-charge-cycle')]
subprocess.run(command, check=True)
result = subprocess.run([str(OUT / 'test-charge-cycle')],
                        capture_output=True, text=True, check=True)
report = json.loads(result.stdout)
report.update({
    'tested_files': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                     for name in ['charge-cycle.h', 'test-charge-cycle.c',
                                  '../charging-management-20261023/mp2650-core.h',
                                  '../charging-management-20261023/oem-profile.h']},
    'sanitizers': ['ASan', 'UBSan'], 'command': command,
    'scope': 'Actual portable cycle helper, not kernel deployment or physical recharge acceptance',
    'phone_accessed': False, 'shared_kernel_or_sdk_modified': False,
})
(HERE / 'test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
