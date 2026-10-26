from pathlib import Path
import hashlib,json,sys
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
which,kind=sys.argv[1:];assert (which,kind) in [('rear','raw'),('front','raw'),('front','rgb')]
build=json.loads((R/'physical-probe-build-validation.json').read_text());binary=P/'native-physical-probe237';assert hashlib.sha256(binary.read_bytes()).hexdigest()==build['binary_sha256']
if which=='front':assert json.loads((R/'rear-raw-capture-r2-validation.json').read_text())['passed']
host.upload(binary,'/var/lib/samurai/k237-tools/native-physical-probe237')
host.upload(R/'native-capture-r2.py','/var/lib/samurai/k237-tools/native-capture-r2.py')
worker_sha=hashlib.sha256((R/'native-capture-r2.py').read_bytes()).hexdigest()
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
which,kind,binary_sha,worker_sha=sys.argv[1:]
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((r/'k237-camss-install/state-private.json').read_text())['exit_code']==0
out=r/f'k237-capture-{which}-{kind}-r2';assert not out.exists()
binary=r/'k237-tools/native-physical-probe237';source=r/'k237-tools/native-capture-r2.py'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==binary_sha and hashlib.sha256(source.read_bytes()).hexdigest()==worker_sha
compile(source.read_text(),str(source),'exec')
target=Path('/run/samurai-camera237-probes');target.mkdir(mode=0o755,exist_ok=True);shutil.copyfile(binary,target/'native-physical-probe');(target/'native-physical-probe').chmod(0o755)
smoke=subprocess.run([str(target/'native-physical-probe')],capture_output=True,timeout=5);assert smoke.returncode==2 and not smoke.stdout
with (r/f'k237-tools/capture-{which}-{kind}-r2-launch-private.log').open('xb') as log:p=subprocess.Popen([sys.executable,str(source),which,kind],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (out/'state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((out/'state-private.json').read_text());assert s['pid']==p.pid
print(json.dumps(dict(stage=237,camera=which,kind=kind,launched_once=True,state=s['state'],phase=s['phase'])))
'''
command='python3 - '+which+' '+kind+' '+build['binary_sha256']+' '+worker_sha
r=host.ssh(command,input=code.encode(),timeout=12);(P/f'{which}-{kind}-launch-host-private.log').write_bytes(r.stdout+r.stderr)
p=P/'current-work-private.json';s=json.loads(p.read_text());s.update(state=f'one {which}/{kind} RAM capture worker launched',active_native_context=f'/var/lib/samurai/k237-capture-{which}-{kind}-r2',next='Poll same capture worker, preserve failure/cleanup. Never relaunch solely due observation timeout.');p.write_text(json.dumps(s,indent=2)+'\n');print(r.stdout.decode().strip())
