from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent
host.upload(R/'native-pmic-cycles.py','/var/lib/samurai/k233-tools/native-pmic-cycles.py')
digest=hashlib.sha256((R/'native-pmic-cycles.py').read_bytes()).hexdigest()
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k233-runtime/boot-id-private.txt').read_bytes()
source=root/'k233-tools/native-pmic-cycles.py';assert hashlib.sha256(source.read_bytes()).hexdigest()==EXPECTED
assert not (root/'k233-pmic-cycles').exists()
with (root/'k233-tools/pmic-cycles-launch-private.log').open('xb') as log:
 p=subprocess.Popen([sys.executable,str(source)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (root/'k233-pmic-cycles/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((root/'k233-pmic-cycles/state-private.json').read_text());assert s['pid']==p.pid
print(json.dumps(dict(stage=233,launched_once=True,state=s['state'],phase=s['phase'])))
'''.replace('EXPECTED',repr(digest))
r=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'pmic-cycles-launch-host-private.log').write_bytes(r.stdout+r.stderr)
state=json.loads((host.PRIVATE/'current-work-private.json').read_text());state.update(state='native per-device PMIC cycle worker launched once; inspect same handle',active_native_context='/var/lib/samurai/k233-pmic-cycles',active_native_session='native-pmic-cycles');(host.PRIVATE/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
print(r.stdout.decode().strip())
