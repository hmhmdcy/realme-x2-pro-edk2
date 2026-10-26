"""Exercise only the isolated thermal candidate with the real core regression."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path(__file__).resolve().parent
candidate = root / 'thermal-candidate'
linux_root = '/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/thermal-candidate'
report = {'phone_accessed': False, 'production_sources_modified': False,
          'sanitizers': ['ASan', 'UBSan'], 'results': {}}
for name in ('core', 'thermal'):
    command = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--', 'gcc', '-std=c11',
               '-g', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
               '-fno-omit-frame-pointer', linux_root + '/test-' + name + '.c',
               '-o', linux_root + '/test-' + name]
    build = subprocess.run(command, capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr
    result = subprocess.run(['wsl', '-d', 'Ubuntu', '-u', 'root', '--',
                             linux_root + '/test-' + name], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    report['results'][name] = {'command': command, 'output': json.loads(result.stdout),
                              'stderr': result.stderr}
report['files_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in candidate.iterdir() if p.suffix in ('.c', '.h')}
report['passed'] = True
report['scope'] = 'Isolated current-production-core candidate plus unchanged production regressions; no physical acceptance'
(root / 'thermal-test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
