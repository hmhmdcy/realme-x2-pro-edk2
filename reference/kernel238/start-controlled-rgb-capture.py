from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'candidate-stage-validation.json').read_text())['ram_candidate_staged']
build=json.loads((R/'rgb-control-probe-build-validation.json').read_text());binary=P/'physical-rgb-control-probe238';assert hashlib.sha256(binary.read_bytes()).hexdigest()==build['binary_sha256']
source=R/'native-controlled-rgb-capture.py';digest=hashlib.sha256(source.read_bytes()).hexdigest()
host.upload(binary,'/var/lib/samurai/k238-tools/physical-rgb-control-probe238');host.upload(source,'/var/lib/samurai/k238-tools/native-controlled-rgb-capture.py')
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
binary_sha,source_sha=sys.argv[1:];r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();assert not (r/'k238-controlled-rear-rgb-r14').exists()
assert json.loads((r/'k238-vendor-audit/state-private.json').read_text())['state']=='terminal'
binary=r/'k238-tools/physical-rgb-control-probe238';source=r/'k238-tools/native-controlled-rgb-capture.py';assert hashlib.sha256(binary.read_bytes()).hexdigest()==binary_sha and hashlib.sha256(source.read_bytes()).hexdigest()==source_sha;compile(source.read_text(),str(source),'exec')
target=Path('/run/samurai-camera238-probes');assert target.is_dir();target.chmod(0o755);shutil.copyfile(binary,target/'physical-rgb-control-probe');(target/'physical-rgb-control-probe').chmod(0o755)
smoke=subprocess.run([str(target/'physical-rgb-control-probe')],capture_output=True,timeout=5);assert smoke.returncode==2
with (r/'k238-tools/controlled-rgb-capture-launch-private.log').open('xb') as log:p=subprocess.Popen([sys.executable,str(source),'rear','rgb'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (r/'k238-controlled-rear-rgb-r14/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((r/'k238-controlled-rear-rgb-r14/state-private.json').read_text());assert s['pid']==p.pid;print(json.dumps(dict(stage=238,launched_once=True,state=s['state'],phase=s['phase'])))
'''
r=host.ssh('python3 - '+build['binary_sha256']+' '+digest,input=code.encode(),timeout=12);(P/'controlled-rgb-capture-launch-host-private.log').write_bytes(r.stdout+r.stderr)
p=P/'current-work-private.json';s=json.loads(p.read_text());s.update(active_native_context='/var/lib/samurai/k238-controlled-rear-rgb-r14',active_build_session=None,active_gain_test_session=None,active_vendor_export_session=None,state='one r14 controlled48-frame rear experiment running; installedr13 unchanged',next='Poll same controlled worker; preserve failure, trace and full restoration. No repeat launch.');p.write_text(json.dumps(s,indent=2)+'\n');print(r.stdout.decode().strip())
