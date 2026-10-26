"""Upload locked modules, run the guarded atomic disk-only transaction once."""
from pathlib import Path
import hashlib
import json
import host

R = Path(__file__).resolve().parent
P = host.PRIVATE
lock = json.loads((P / 'deployment-lock-private.json').read_text())
for info in lock['files'].values():
    assert hashlib.sha256(Path(info['path']).read_bytes()).hexdigest() == info['sha256']
code = '''from pathlib import Path
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k233-runtime/boot-id-private.txt').read_bytes()==(root/'k235-baseline/boot-id-private.txt').read_bytes()
out=root/'k235-tools';assert not out.exists();out.mkdir(mode=0o700)
print('FRESH_TOOLS_CREATED')
'''
result = host.ssh('python3 -', input=code.encode(), timeout=15)
(P / 'tools-create-private.log').write_bytes(result.stdout + result.stderr)
for key, name in [('mfd_module', 'qcom-pm8008.ko'), ('lab_module', 'qcom-pm8008-imx319-lab.ko'), ('sensor_module', 'imx319.ko')]:
    host.upload(Path(lock['files'][key]['path']), '/var/lib/samurai/k235-tools/' + name)
host.upload(P / 'deployment-lock-private.json', '/var/lib/samurai/k235-tools/deployment-lock-private.json')
result = host.ssh('python3 -', input=(R / 'install-modules.py').read_bytes(), timeout=110)
(P / 'module-stage-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(R / 'module-stage-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state = json.loads((P / 'current-work-private.json').read_text())
state.update(state='235 three candidate module files/options staged on disk; current233 boot/232 PMIC still live; new hardware candidate NOT tested',
             module_files_staged=True, transition_pending=False,
             priority='Prepare fresh guarded235/236 quiesce and one boot-only flash235; never hot-unload live P/Q MFD',
             active_native_worker=None, active_build_session=None)
(P / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
