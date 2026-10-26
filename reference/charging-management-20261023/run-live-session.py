"""Execute one phase after the camera chat explicitly hands over the phone.

This is a manual entry point, never scheduled or run by a build script.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import shlex
import sys

ref = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('charging_window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec)
spec.loader.exec_module(window)
host = window.host
assert len(sys.argv) in [3,4] and sys.argv[1] == '--owned-window'
name = sys.argv[3] if len(sys.argv) == 4 else 'window3'
assert name in ['window3','window4','window5']
private = Path('/mnt/e/edk2-samurai-out/charging-management-20261023') / name
private.mkdir(exist_ok=True, mode=0o700)
remote = '/root/charging-management-20261023'
action = sys.argv[2]
assert action in ['stage', 'snapshot', 'shadow', 'state', 'diagnostic', 'finish']

if action == 'stage':
    manifest = json.loads((ref / 'integrated-build-result.json').read_text())
    host.ssh('install -d -m 700 ' + shlex.quote(remote), timeout=15).check_returncode()
    files = {'live-session.py': ref / 'live-session.py'}
    for name, info in manifest['modules'].items():
        p = Path(info['path'])
        assert hashlib.sha256(p.read_bytes()).hexdigest() == info['sha256']
        assert 'intree:         Y' in info['modinfo']
        files[name + '.ko'] = p
    receipt = {}
    for name, path in files.items():
        data = path.read_bytes()
        target = remote + '/' + name
        code = 'from pathlib import Path; import sys; p=Path(' + repr(target) + '); p.write_bytes(sys.stdin.buffer.read()); p.chmod(0o600)'
        host.ssh('python3 -c ' + shlex.quote(code), input=data, timeout=30).check_returncode()
        q = host.ssh('sha256sum ' + shlex.quote(target), timeout=15); q.check_returncode()
        digest = q.stdout.decode().split()[0]
        assert digest == hashlib.sha256(data).hexdigest()
        receipt[name] = digest
    (private / 'staged.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps({'staged_files': receipt, 'modules_loaded': False}))
else:
    command = 'python3 ' + shlex.quote(remote + '/live-session.py') + ' ' + action
    if action == 'diagnostic':
        code = """from pathlib import Path
import json,subprocess
p=Path('/sys/bus/i2c/devices/0-005c')
print(json.dumps({'driver':str((p/'driver').resolve()),'taint':Path('/proc/sys/kernel/tainted').read_text(),
'modules':Path('/proc/modules').read_text(), 'dmesg':subprocess.check_output(['dmesg'],text=True).splitlines()[-100:],
'before':Path('/root/charging-management-20261023/shadow-before-private.json').read_text(),
'restored':Path('/root/charging-management-20261023/shadow-restored-private.json').read_text()}))
"""
        command = 'python3 -c ' + shlex.quote(code)
    if action == 'finish':
        code="""from pathlib import Path
import json,subprocess
names=['samurai_mp2650','samurai_usb_input','samurai_gauge_protection']
modules={n:Path('/sys/module',n).exists() for n in names}
log=subprocess.check_output(['dmesg'],text=True)
faults={n:log.count(n) for n in ['cannot create duplicate filename','refcount_t: underflow','WARNING:','Oops:']}
taint=int(Path('/proc/sys/kernel/tainted').read_text())
assert not any(modules.values()) and not any(faults.values()) and taint==0
assert Path('/sys/bus/i2c/devices/0-005c/driver').resolve().name=='mp2650'
print(json.dumps({'taint':taint,'candidate_modules_present':modules,'boot_fault_counts':faults,'original_observer_restored':True}))
"""
        command='python3 -c '+shlex.quote(code)
    q = host.ssh(command, timeout=45, check=False)
    (private / (action + '-stdout-private.json')).write_bytes(q.stdout)
    (private / (action + '-stderr-private.txt')).write_bytes(q.stderr)
    if q.returncode:
        print(q.stderr.decode(errors='replace')[-4000:])
    q.check_returncode()
    data = json.loads(q.stdout)
    if action == 'shadow':
        for name in ['shadow-restored-private.json', 'shadow-before-private.json', 'shadow-captured-private.json']:
            q = host.ssh('cat ' + shlex.quote(remote + '/' + name), timeout=15)
            q.check_returncode(); (private / name).write_bytes(q.stdout)
    print(json.dumps({k:v for k,v in data.items() if k not in ['boot_id','supplies','m2m']}, indent=2))
