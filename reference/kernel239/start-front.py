from pathlib import Path
import hashlib,json,sys
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;kind=sys.argv[1];assert kind in ['raw','rgb']
assert json.loads((R/'r15-startup-analysis.json').read_text())['r15_initial_snapshot_verified']
if kind=='rgb':assert json.loads((R/'front-raw-validation.json').read_text())['passed']
binary=P/'front-physical-probe239';source=R/'native-front.py';binary_sha=hashlib.sha256(binary.read_bytes()).hexdigest();source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
assert binary_sha==json.loads((R.parent/'kernel237/physical-probe-build-validation.json').read_text())['binary_sha256']
host.upload(binary,'/var/lib/samurai/k239-tools/front-physical-probe239');host.upload(source,'/var/lib/samurai/k239-tools/native-front.py')
code=r'''
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
kind,binary_sha,source_sha=sys.argv[1:];r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();out=r/('k239-front-r15-'+kind);assert not out.exists()
binary=r/'k239-tools/front-physical-probe239';source=r/'k239-tools/native-front.py';assert hashlib.sha256(binary.read_bytes()).hexdigest()==binary_sha and hashlib.sha256(source.read_bytes()).hexdigest()==source_sha;compile(source.read_text(),str(source),'exec')
target=Path('/run/samurai-camera239-probes');target.mkdir(mode=0o755,exist_ok=True);shutil.copyfile(binary,target/'front-physical-probe');(target/'front-physical-probe').chmod(0o755)
with (r/f'k239-tools/front-{kind}-launch-private.log').open('xb') as log:p=subprocess.Popen([sys.executable,str(source),'front',kind],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (out/'state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
state=json.loads((out/'state-private.json').read_text());assert state['pid']==p.pid;print(json.dumps(dict(stage=239,kind=kind,launched_once=True,state=state['state'],phase=state['phase'])))
'''
result=host.ssh('python3 - '+kind+' '+binary_sha+' '+source_sha,input=code.encode(),timeout=12);(P/f'front-{kind}-launch-host-private.log').write_bytes(result.stdout+result.stderr)
p=P/'current-work-private.json';state=json.loads(p.read_text());state.update(active_native_context='/var/lib/samurai/k239-front-r15-'+kind,state='One front r15 '+kind+' capture running',next='Poll same front worker; no repeated launch on observation timeout.');p.write_text(json.dumps(state,indent=2)+'\n');print(result.stdout.decode().strip())
