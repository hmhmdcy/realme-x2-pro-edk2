from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
build=json.loads((R/'camss-build-validation.json').read_text());tests=json.loads((R/'camss-function-tests-validation.json').read_text())
assert tests['results']['video-actual']['passed'] and tests['results']['buffer-actual']['passed'] and tests['negative_controls_rejected']==4
module=P/'camss-build-r1/qcom-camss-unwind237.ko';assert hashlib.sha256(module.read_bytes()).hexdigest()==build['sha256']
lock=dict(stage=237,original_sha256='fae1ed40da4e2751c081aca3a990a5a3c44de47599883a045340b9f62f54803e',candidate_sha256=build['sha256'],worker_sha256=hashlib.sha256((R/'native-install-camss.py').read_bytes()).hexdigest())
lockfile=P/'install-lock-private.json';assert not lockfile.exists();lockfile.write_text(json.dumps(lock,indent=2)+'\n')
setup=r'''
from pathlib import Path
import os
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/'k237-tools';assert not p.exists();p.mkdir(mode=0o700);print('new237-tools-ready')
'''
host.ssh('python3 -',input=setup.encode(),timeout=10)
for source,dest in [(module,'qcom-camss-unwind237.ko'),(lockfile,'install-lock-private.json'),(R/'native-install-camss.py','native-install-camss.py')]:host.upload(source,'/var/lib/samurai/k237-tools/'+dest)
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert not (r/'k237-camss-install').exists();source=r/'k237-tools/native-install-camss.py';lock=json.loads((r/'k237-tools/install-lock-private.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==lock['worker_sha256'];compile(source.read_text(),str(source),'exec')
with (r/'k237-tools/install-launch-private.log').open('xb') as f:p=subprocess.Popen([sys.executable,str(source)],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (r/'k237-camss-install/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((r/'k237-camss-install/state-private.json').read_text());assert s['pid']==p.pid
print(json.dumps(dict(stage=237,launched_once=True,state=s['state'],phase=s['phase'])))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=12);(P/'install-launch-host-private.log').write_bytes(r.stdout+r.stderr)
p=P/'current-work-private.json';s=json.loads(p.read_text());s.update(state='one idleCAMSS replacement worker launched',active_native_context='/var/lib/samurai/k237-camss-install',next='Poll same install worker. Do not repeat load/unload.');p.write_text(json.dumps(s,indent=2)+'\n');print(r.stdout.decode().strip())
