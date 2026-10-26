from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'fixed-rgb-validation.json').read_text())['diagnostic_capture_completed']
build=json.loads((R/'paired-build-validation.json').read_text());binary=P/'paired-probe239';source=R/'native-paired.py'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==build['binary_sha256']
digest=hashlib.sha256(source.read_bytes()).hexdigest()
host.upload(binary,'/var/lib/samurai/k239-tools/paired-probe239');host.upload(source,'/var/lib/samurai/k239-tools/native-paired.py')
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
binary_sha,source_sha=sys.argv[1:];r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();assert not (r/'k239-paired-r14').exists()
assert json.loads((r/'k239-baseline/summary.json').read_text())['camera_idle_no_other_clients']
binary=r/'k239-tools/paired-probe239';source=r/'k239-tools/native-paired.py';assert hashlib.sha256(binary.read_bytes()).hexdigest()==binary_sha and hashlib.sha256(source.read_bytes()).hexdigest()==source_sha;compile(source.read_text(),str(source),'exec')
target=Path('/run/samurai-camera238-probes');assert target.is_dir();target.chmod(0o755);shutil.copyfile(binary,target/'paired-probe239');(target/'paired-probe239').chmod(0o755)
smoke=subprocess.run([str(target/'paired-probe239')],capture_output=True,timeout=5);assert smoke.returncode==2
with (r/'k239-tools/paired-launch-private.log').open('xb') as log:p=subprocess.Popen([sys.executable,str(source),'rear','rgb'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (r/'k239-paired-r14/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((r/'k239-paired-r14/state-private.json').read_text());assert s['pid']==p.pid;print(json.dumps(dict(stage=239,launched_once=True,state=s['state'],phase=s['phase'])))
'''
result=host.ssh('python3 - '+build['binary_sha256']+' '+digest,input=code.encode(),timeout=12)
(P/'paired-launch-host-private.log').write_bytes(result.stdout+result.stderr)
state_path=P/'current-work-private.json';state=json.loads(state_path.read_text());state.update(active_native_context='/var/lib/samurai/k239-paired-r14',state='paired12 RAW/RGB diagnostic running once',next='Poll same native handle; inspect all Debayer DEBUG lines and captured IPA metadata, retain strict black-frame failure.');state_path.write_text(json.dumps(state,indent=2)+'\n')
print(result.stdout.decode().strip())
