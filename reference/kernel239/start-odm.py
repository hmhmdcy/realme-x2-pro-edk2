from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent;source=R/'native-odm.py';digest=hashlib.sha256(source.read_bytes()).hexdigest()
assert json.loads((R/'paired-validation.json').read_text())['diagnostic_capture_completed']
host.upload(source,'/var/lib/samurai/k239-tools/native-odm.py')
code=r'''
from pathlib import Path
import hashlib,json,subprocess,sys,time
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();assert not (r/'k239-odm-source').exists()
source=r/'k239-tools/native-odm.py';assert hashlib.sha256(source.read_bytes()).hexdigest()==sys.argv[1];compile(source.read_text(),str(source),'exec')
with (r/'k239-tools/odm-launch-private.log').open('xb') as log:p=subprocess.Popen([sys.executable,str(source)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (r/'k239-odm-source/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
state=json.loads((r/'k239-odm-source/state-private.json').read_text());assert state['pid']==p.pid;print(json.dumps(dict(stage=239,launched_once=True,state=state['state'],phase=state['phase'])))
'''
result=host.ssh('python3 - '+digest,input=code.encode(),timeout=12);(host.PRIVATE/'odm-launch-host-private.log').write_bytes(result.stdout+result.stderr)
p=host.PRIVATE/'current-work-private.json';state=json.loads(p.read_text());state.update(active_native_context='/var/lib/samurai/k239-odm-source',next='Poll exact ODM worker; preserve ownership/unmount evidence and never relaunch on observation timeout.');p.write_text(json.dumps(state,indent=2)+'\n');print(result.stdout.decode().strip())
