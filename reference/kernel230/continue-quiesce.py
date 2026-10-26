"""Continue after a failed pre-unload assertion, preserving the first worker."""
from pathlib import Path
import hashlib,json
import host
ref=Path(__file__).resolve().parent
source=(ref/'quiesce-current183.sh').read_text()
point='python3 /tmp/k230-quiesce-camera.py\n';assert source.count(point)==1
tail=source[source.index(point):]
head='''#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k230-baseline
dest=/var/lib/samurai/k230-quiesce
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 4096
test -d "$dest"
test -z "$(pgrep -u 10000 || true)"
test -z "$(pgrep -x phosh || true)"
test -z "$(pgrep -x phoc || true)"
test ! -e /run/k230-bootloader-state
'''
continuation=host.PRIVATE/'quiesce-tail-private.sh';assert not continuation.exists();continuation.write_text(head+tail)
code=r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');out=root/'k230-quiesce';old=root/'k230-quiesce-runner'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k230-baseline/boot-id-private.txt').read_bytes()
assert json.loads((old/'state-private.json').read_text())['exit_code']==1
log=(old/'quiesce-private.log').read_text();assert 'quiesce-camera.py", line 18' in log
assert "(p/'num_users').read_text().strip()=='4096'" in log
assert not list(out.glob('camera-unload-*')) and not (out/'camera-quiesce-validation.json').exists()
assert Path('/sys/module/qcom_camss').exists()
assert not Path('/run/k230-bootloader-state').exists() and not Path('/run/k230-linux-restart2-phase-private.json').exists()
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()=='offline'
assert subprocess.run(['pgrep','-u','10000'],stdout=subprocess.DEVNULL).returncode==1
assert not json.loads((root/'gnss-assist/watch-state.json').read_text())['running']
for name in ['display','radio']:assert Path('/sys/kernel/tracing/instances',name,'tracing_on').read_text().strip()=='0'
oldsource=Path('/tmp/k230-quiesce-camera.py');saved=out/'camera-first-precondition-error-private.py';assert not saved.exists();saved.write_bytes(oldsource.read_bytes())
manifest=root/'k230-tools/uploaded-sources-private.json';backup=root/'k230-tools/uploaded-sources-first-private.json';assert not backup.exists();backup.write_bytes(manifest.read_bytes())
print('FIRST_FAILURE_RETAINED_NO_CAMERA_UNLOAD_NO_FREEZE')
'''
r=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'continuation-precheck-private.log').write_bytes(r.stdout+r.stderr)
host.upload(ref/'quiesce-camera.py','/tmp/k230-quiesce-camera.py')
host.upload(continuation,'/tmp/k230-quiesce-tail.sh')
manifest=json.loads((host.PRIVATE/'uploaded-sources-private.json').read_text())
manifest['/tmp/k230-quiesce-camera.py']=hashlib.sha256((ref/'quiesce-camera.py').read_bytes()).hexdigest()
manifest['/tmp/k230-quiesce-tail.sh']=hashlib.sha256(continuation.read_bytes()).hexdigest()
p=host.PRIVATE/'uploaded-sources-r2-private.json';p.write_text(json.dumps(manifest,indent=2)+'\n')
host.upload(p,'/var/lib/samurai/k230-tools/uploaded-sources-private.json')
source=(ref/'run-quiesce.py').read_text()
import ast
t=ast.parse(source);code=ast.literal_eval(next(n.value for n in t.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='code' for v in n.targets)))
code=code.replace('k230-quiesce-runner','k230-quiesce-runner-r2')
code=code.replace("assert not out.exists() and not (root/'k230-quiesce').exists()", "assert not out.exists() and (root/'k230-quiesce').exists()")
code=code.replace('/tmp/k230-quiesce-current183.sh','/tmp/k230-quiesce-tail.sh')
code=code.replace("out.mkdir(mode=0o700)","""manifest=json.loads((root/'k230-tools/uploaded-sources-private.json').read_text())
import hashlib
for name,digest in manifest.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
out.mkdir(mode=0o700)""")
r=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'continuation-launch-private.log').write_bytes(r.stdout+r.stderr)
s=json.loads((host.PRIVATE/'current-work-private.json').read_text());s.update(state='first quiesce stopped at generated pre-unload assertion; preserved; confirmed no camera unload/freeze; corrected tail running once',active_native_context='/var/lib/samurai/k230-quiesce-runner-r2',active_native_session='continuation worker')
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(s,indent=2)+'\n');print(r.stdout.decode().strip())
