"""Offline evidence collection only. Does not use a phone or shared build tree."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path(__file__).resolve().parent
candidate = root.parent / 'charging-management-20261023'
cache = Path('E:/edk2-samurai-out/kernel83')
prefix = 'realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--'
files = {
    'oem_dts': cache / (prefix + 'arch--arm64--boot--dts--19781--pm8150b.dtsi'),
    'oem_policy': cache / (prefix + 'drivers--power--oppo--oplus_charger.c'),
    'oem_mp2650': cache / (prefix + 'drivers--power--oppo--charger_ic--oplus_mp2650.c'),
    'oem_gauge': cache / (prefix + 'drivers--power--oppo--gauge_ic--oplus_bq27541.c'),
    'core': candidate / 'mp2650-core.h',
    'profile': candidate / 'oem-profile.h',
    'driver': candidate / 'samurai-mp2650.c',
    'gauge_protocol': candidate / 'gauge-protocol.h',
    'ti_manual': Path('E:/edk2-samurai-out/charging-management-20261023/ti-manual-private.txt'),
    'probe': root / 'probe-current-policy.c',
}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = {name: sha(p) for name, p in files.items()}
linux_root = '/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023'
command = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--', 'gcc', '-std=c11',
           '-g', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
           '-fno-omit-frame-pointer', linux_root + '/probe-current-policy.c',
           '-o', linux_root + '/probe-current-policy']
build = subprocess.run(command, capture_output=True, text=True)
assert build.returncode == 0, build.stdout + build.stderr
run = subprocess.run(['wsl', '-d', 'Ubuntu', '-u', 'root', '--',
                      linux_root + '/probe-current-policy'], capture_output=True, text=True)
assert run.returncode == 0, run.stdout + run.stderr
after = {name: sha(p) for name, p in files.items()}
assert before == after, 'Production source changed during audit; evidence must be rerun'
report = {
    'date': '2026-10-23',
    'repository': 'https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source',
    'commit': '23172a1571bd91156032cc9fef16284a82b63d2c',
    'files': {name: {'path': str(p), 'sha256': before[name]} for name, p in files.items()},
    'build_command': command,
    'probe_output': run.stdout,
    'probe_passed': True,
    'meaning': 'The probe confirms two current behavior gaps; it is not a repaired implementation or physical acceptance',
    'phone_accessed': False,
    'shared_build_modified': False,
    'candidate_sources_modified': False,
}
(root / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
