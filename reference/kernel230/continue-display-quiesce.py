"""Continue after an old taint0 precondition stopped before any modeset."""
from pathlib import Path
import ast,hashlib,json
import host
ref=Path(__file__).resolve().parent
source=(ref/'quiesce-current183.sh').read_text();point='python3 /tmp/k230-disable-crtc.py';assert source.count(point)==1
tail='''#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k230-baseline
dest=/var/lib/samurai/k230-quiesce
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 4096
test ! -e /run/k230-bootloader-state
'''+source[source.index(point):]
target=host.PRIVATE/'quiesce-display-tail-private.sh';assert not target.exists();target.write_text(tail)
code=r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');out=root/'k230-quiesce';tools=root/'k230-tools'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k230-baseline/boot-id-private.txt').read_bytes()
assert json.loads((root/'k230-quiesce-runner-r2/state-private.json').read_text())['exit_code']==1
log=(out/'explicit-crtc-disable.txt').read_text();assert 'disable-crtc.py", line 7' in log
assert "Path('/proc/sys/kernel/tainted').read_text().strip() == '0'" in log
assert Path('/sys/module/drm_kms_helper/parameters/fbdev_emulation').read_text().strip()=='Y'
assert not list(out.glob('drm-explicit-disable-*.txt'))
assert Path('/sys/class/vtconsole/vtcon1/bind').read_text().strip()=='0'
assert len(Path('/sys/kernel/debug/dri/1/clients').read_text().splitlines())==1
assert all(Path('/sys/class/remoteproc/remoteproc%d/state'%n).read_text().strip()=='offline' for n in range(3))
assert json.loads((out/'camera-quiesce-validation.json').read_text())['all_six_camera_modules_unloaded']
assert not Path('/sys/bus/platform/devices/18800000.wifi/driver').exists()
assert not Path('/run/k230-bootloader-state').exists() and not Path('/run/k230-linux-restart2-phase-private.json').exists()
saved=out/'explicit-crtc-first-precondition-error-private.txt';assert not saved.exists();saved.write_text(log)
saved=out/'disable-crtc-first-precondition-error-private.py';assert not saved.exists();saved.write_bytes(Path('/tmp/k230-disable-crtc.py').read_bytes())
manifest=tools/'uploaded-sources-private.json';backup=tools/'uploaded-sources-r2-private.json';assert not backup.exists();backup.write_bytes(manifest.read_bytes())
print('SECOND_PRECONDITION_FAILURE_RETAINED_NO_MODESET_NO_FREEZE')
'''
r=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'display-continuation-precheck-private.log').write_bytes(r.stdout+r.stderr)
host.upload(ref/'disable-crtc.py','/tmp/k230-disable-crtc.py');host.upload(target,'/tmp/k230-quiesce-display-tail.sh')
manifest=json.loads((host.PRIVATE/'uploaded-sources-r2-private.json').read_text());manifest['/tmp/k230-disable-crtc.py']=hashlib.sha256((ref/'disable-crtc.py').read_bytes()).hexdigest();manifest['/tmp/k230-quiesce-display-tail.sh']=hashlib.sha256(target.read_bytes()).hexdigest()
p=host.PRIVATE/'uploaded-sources-r3-private.json';assert not p.exists();p.write_text(json.dumps(manifest,indent=2)+'\n');host.upload(p,'/var/lib/samurai/k230-tools/uploaded-sources-private.json')
t=ast.parse((ref/'run-quiesce.py').read_text());code=ast.literal_eval(next(n.value for n in t.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='code' for v in n.targets)))
code=code.replace('k230-quiesce-runner','k230-quiesce-runner-r3').replace('/tmp/k230-quiesce-current183.sh','/tmp/k230-quiesce-display-tail.sh')
code=code.replace("assert not out.exists() and not (root/'k230-quiesce').exists()", "assert not out.exists() and (root/'k230-quiesce').exists()")
code=code.replace("out.mkdir(mode=0o700)","""manifest=json.loads((root/'k230-tools/uploaded-sources-private.json').read_text())
import hashlib
for name,digest in manifest.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
out.mkdir(mode=0o700)""")
r=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'display-continuation-launch-private.log').write_bytes(r.stdout+r.stderr)
s=json.loads((host.PRIVATE/'current-work-private.json').read_text());s.update(state='camera/DSP/radio cleanup passed; old display taint0 gate failed before modeset and retained; corrected display tail running once',active_native_context='/var/lib/samurai/k230-quiesce-runner-r3',active_native_session='display continuation worker')
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(s,indent=2)+'\n');print(r.stdout.decode().strip())
