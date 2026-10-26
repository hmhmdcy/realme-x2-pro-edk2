from pathlib import Path
import hashlib
import json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
source=R/'native-snapshot-mmap-r2.py';digest=hashlib.sha256(source.read_bytes()).hexdigest()
host.upload(source,'/var/lib/samurai/k240-tools/native-snapshot-mmap-r2.py')
code=r'''
from pathlib import Path
import hashlib,json,subprocess,sys,time
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((r/'k240-upright-paired-r15-r2/state-private.json').read_text())['state']=='terminal'
assert json.loads((r/'k240-snapshot-fault-stop/summary.json').read_text())['camera_devices_suspended'];assert not (r/'k240-snapshot-mmap-r2').exists()
source=r/'k240-tools/native-snapshot-mmap-r2.py';assert hashlib.sha256(source.read_bytes()).hexdigest()==sys.argv[1];compile(source.read_text(),str(source),'exec')
with (r/'k240-tools/snapshot-mmap-r2-launch-private.log').open('xb') as log:
 p=subprocess.Popen([sys.executable,str(source),'front','rgb'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (r/'k240-snapshot-mmap-r2/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((r/'k240-snapshot-mmap-r2/state-private.json').read_text());assert s['pid']==p.pid
print(json.dumps(dict(stage=240,submitted_once=True,state=s['state'],phase=s['phase'])))
'''
result=host.ssh('python3 - '+digest,input=code.encode(),timeout=15)
(P/'snapshot-mmap-r2-launch-host-private.log').write_bytes(result.stdout+result.stderr)
p=P/'current-work-private.json';state=json.loads(p.read_text());state.update(active_native_context='/var/lib/samurai/k240-snapshot-mmap-r2',
 state='Bounded Snapshot CPU-rendered diagnostic submitted once; observed default Vulkan faults retained',
 next='Poll this exact GUI worker; verify real new buffers, sink renders, no new faults and full camera-state cleanup. No shutter.')
p.write_text(json.dumps(state,indent=2)+'\n');print(result.stdout.decode().strip())
