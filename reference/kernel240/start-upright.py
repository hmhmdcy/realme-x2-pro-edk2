from pathlib import Path
import hashlib
import json
import host

R = Path(__file__).resolve().parent
P = host.PRIVATE
build = json.loads((R / 'upright-build-validation.json').read_text())
binary = P / 'upright-paired-probe240'
native = R / 'native-upright.py'
assert hashlib.sha256(binary.read_bytes()).hexdigest() == build['binary_sha256']
digest = hashlib.sha256(native.read_bytes()).hexdigest()
host.ssh("mkdir -m 700 /var/lib/samurai/k240-tools", timeout=10)
host.upload(binary, '/var/lib/samurai/k240-tools/upright-paired-probe240')
host.upload(native, '/var/lib/samurai/k240-tools/native-upright.py')
code = r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
binary_sha,source_sha=sys.argv[1:];r=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert not (r/'k240-upright-paired-r15').exists()
assert json.loads((r/'k240-baseline/summary.json').read_text())['installed_r15_r10']
binary=r/'k240-tools/upright-paired-probe240';source=r/'k240-tools/native-upright.py'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==binary_sha and hashlib.sha256(source.read_bytes()).hexdigest()==source_sha
compile(source.read_text(),str(source),'exec')
target=Path('/run/samurai-camera240-probes');assert not target.exists();target.mkdir(mode=0o755)
shutil.copyfile(binary,target/'upright-paired-probe240');(target/'upright-paired-probe240').chmod(0o755)
smoke=subprocess.run([str(target/'upright-paired-probe240')],capture_output=True,timeout=5);assert smoke.returncode==2
with (r/'k240-tools/upright-launch-private.log').open('xb') as log:
 p=subprocess.Popen([sys.executable,str(source),'rear','rgb'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (r/'k240-upright-paired-r15/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((r/'k240-upright-paired-r15/state-private.json').read_text());assert s['pid']==p.pid
print(json.dumps(dict(stage=240,launched_once=True,state=s['state'],phase=s['phase'])))
'''
result = host.ssh('python3 - '+build['binary_sha256']+' '+digest, input=code.encode(), timeout=15)
(P / 'upright-launch-host-private.log').write_bytes(result.stdout+result.stderr)
state_path=P/'current-work-private.json';state=json.loads(state_path.read_text())
state.update(state='User upright check: paired24 RAW/RGB 2ms->32ms worker submitted once',
    active_native_context='/var/lib/samurai/k240-upright-paired-r15',
    next='Poll this same native identity; collect summary in bounded chunks; do not start another camera worker')
state_path.write_text(json.dumps(state,indent=2)+'\n')
print(result.stdout.decode().strip())
