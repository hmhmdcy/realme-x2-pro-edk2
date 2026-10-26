"""Exercise actual portable policy/control code with sanitizers and bus faults."""
from pathlib import Path
import hashlib
import json
import subprocess

ref = Path(__file__).resolve().parent
private = Path('/home/cy122/charging-management-20261023')
binary = private / 'test-core'
command = ['gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           '-I' + str(ref), str(ref / 'test-core.c'), '-o', str(binary)]
subprocess.run(command, check=True)
result = subprocess.run([str(binary)], capture_output=True, text=True)
print(result.stdout, end='')
print(result.stderr, end='')
result.check_returncode()
report = json.loads(result.stdout)
report.update({'command': command, 'sanitizers': ['ASan', 'UBSan'],
               'tested_core_sha256': hashlib.sha256((ref / 'mp2650-core.h').read_bytes()).hexdigest(),
               'tested_profile_sha256': hashlib.sha256((ref / 'oem-profile.h').read_bytes()).hexdigest(),
               'harness_sha256': hashlib.sha256((ref / 'test-core.c').read_bytes()).hexdigest(),
               'scope': 'Actual policy and register transaction code; simulated bus, no hardware acceptance'})
(ref / 'test-result.json').write_text(json.dumps(report, indent=2) + '\n')
