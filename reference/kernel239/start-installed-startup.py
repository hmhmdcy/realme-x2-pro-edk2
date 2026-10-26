from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'baseline-validation.json').read_text())['current236_boot_verified']
build=json.loads((R/'startup-build-validation.json').read_text());binary=P/'startup-probe239';source=R/'native-installed-startup.py'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==build['binary_sha256']
digest=hashlib.sha256(source.read_bytes()).hexdigest()
host.upload(binary,'/var/lib/samurai/k239-tools/startup-probe239');host.upload(source,'/var/lib/samurai/k239-tools/native-installed-startup.py')
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
binary_sha,source_sha=sys.argv[1:];r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();assert not (r/'k239-r15-installed-startup').exists()
assert json.loads((r/'k239-baseline/summary.json').read_text())['camera_idle_no_other_clients']
binary=r/'k239-tools/startup-probe239';source=r/'k239-tools/native-installed-startup.py';assert hashlib.sha256(binary.read_bytes()).hexdigest()==binary_sha and hashlib.sha256(source.read_bytes()).hexdigest()==source_sha;compile(source.read_text(),str(source),'exec')
target=Path('/run/samurai-camera238-probes');assert target.is_dir();target.chmod(0o755);shutil.copyfile(binary,target/'startup-probe239');(target/'startup-probe239').chmod(0o755)
smoke=subprocess.run([str(target/'startup-probe239')],capture_output=True,timeout=5);assert smoke.returncode==2
with (r/'k239-tools/r15-installed-startup-launch-private.log').open('xb') as log:p=subprocess.Popen([sys.executable,str(source),'rear','rgb'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (r/'k239-r15-installed-startup/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((r/'k239-r15-installed-startup/state-private.json').read_text());assert s['pid']==p.pid;print(json.dumps(dict(stage=239,launched_once=True,state=s['state'],phase=s['phase'])))
'''
result=host.ssh('python3 - '+build['binary_sha256']+' '+digest,input=code.encode(),timeout=12)
(P/'r15-installed-startup-launch-host-private.log').write_bytes(result.stdout+result.stderr)
state_path=P/'current-work-private.json';state=json.loads(state_path.read_text());state.update(active_native_context='/var/lib/samurai/k239-r15-installed-startup',state='r15 two-startup RGB diagnostic running once',next='Poll same native handle; inspect all Debayer DEBUG lines and captured IPA metadata, retain strict black-frame failure.');state_path.write_text(json.dumps(state,indent=2)+'\n')
print(result.stdout.decode().strip())
