from pathlib import Path
import hashlib
import json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
source=R/'native-megapixels-startup.py';digest=hashlib.sha256(source.read_bytes()).hexdigest()
host.upload(source,'/var/lib/samurai/k240-tools/native-megapixels-startup.py')
code=r'''
from pathlib import Path
import hashlib,json,subprocess,sys,time
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((r/'k240-upright-paired-r15-r2/state-private.json').read_text())['state']=='terminal'
assert not (r/'k240-megapixels-startup').exists()
source=r/'k240-tools/native-megapixels-startup.py';assert hashlib.sha256(source.read_bytes()).hexdigest()==sys.argv[1];compile(source.read_text(),str(source),'exec')
with (r/'k240-tools/megapixels-launch-private.log').open('xb') as log:
 p=subprocess.Popen([sys.executable,str(source),'rear','rgb'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (r/'k240-megapixels-startup/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((r/'k240-megapixels-startup/state-private.json').read_text());assert s['pid']==p.pid
print(json.dumps(dict(stage=240,submitted_once=True,state=s['state'],phase=s['phase'])))
'''
result=host.ssh('python3 - '+digest,input=code.encode(),timeout=15)
(P/'megapixels-launch-host-private.log').write_bytes(result.stdout+result.stderr)
p=P/'current-work-private.json';state=json.loads(p.read_text());state.update(active_native_context='/var/lib/samurai/k240-megapixels-startup',
 state='Megapixels startup diagnostic submitted once; S5K candidate source retained, not built or installed',
 next='Poll this same GUI worker; inspect stderr/exit and cleanup. Prioritize actual camera app failure before S5K power work.')
p.write_text(json.dumps(state,indent=2)+'\n');print(result.stdout.decode().strip())
