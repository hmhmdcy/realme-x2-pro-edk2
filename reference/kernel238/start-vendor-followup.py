from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent;source=R/'native-vendor-followup.py';digest=hashlib.sha256(source.read_bytes()).hexdigest()
setup=r'''
from pathlib import Path
import os
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/'k238-tools';assert p.is_dir()
'''
host.ssh('python3 -',input=setup.encode(),timeout=10);host.upload(source,'/var/lib/samurai/k238-tools/native-vendor-followup.py')
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();assert not (r/'k238-vendor-followup').exists()
source=r/'k238-tools/native-vendor-followup.py';assert hashlib.sha256(source.read_bytes()).hexdigest()==sys.argv[1];compile(source.read_text(),str(source),'exec')
with (r/'k238-tools/vendor-followup-launch-private.log').open('xb') as f:p=subprocess.Popen([sys.executable,str(source)],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (r/'k238-vendor-followup/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((r/'k238-vendor-followup/state-private.json').read_text());assert s['pid']==p.pid;print(json.dumps(dict(stage=238,launched_once=True,state=s['state'],phase=s['phase'])))
'''
r=host.ssh('python3 - '+digest,input=code.encode(),timeout=12);(host.PRIVATE/'vendor-followup-launch-host-private.log').write_bytes(r.stdout+r.stderr)
p=host.PRIVATE/'current-work-private.json';s=json.loads(p.read_text());s.update(active_native_context='/var/lib/samurai/k238-vendor-followup',next='Poll same vendor audit and build55563; no relaunch solely on observation timeout.');p.write_text(json.dumps(s,indent=2)+'\n');print(r.stdout.decode().strip())
