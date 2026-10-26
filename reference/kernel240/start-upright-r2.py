from pathlib import Path
import hashlib
import json
import host

R = Path(__file__).resolve().parent
P = host.PRIVATE
build = json.loads((R / 'upright-build-validation.json').read_text())
binary = P / 'upright-paired-probe240'
native = R / 'native-upright-r2.py'
assert hashlib.sha256(binary.read_bytes()).hexdigest() == build['binary_sha256']
digest = hashlib.sha256(native.read_bytes()).hexdigest()
host.upload(binary, '/var/lib/samurai/k240-tools/upright-paired-probe240')
host.upload(native, '/var/lib/samurai/k240-tools/native-upright-r2.py')
code = r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
binary_sha,source_sha=sys.argv[1:];r=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert not (r/'k240-upright-paired-r15-r2').exists()
assert json.loads((r/'k240-upright-paired-r15/state-private.json').read_text())['state']=='terminal'
old=json.loads((r/'k240-upright-paired-r15/summary.json').read_text());assert not old['frames'] and old['worker_exception'] and not old['restore_errors']
assert b'other camera client' in (r/'k240-upright-paired-r15/failure-private.txt').read_bytes()
policies=[]
for proc in Path('/proc').glob('[0-9]*'):
 try:
  if (proc/'comm').read_text().strip()=='wireplumber' and int((proc/'status').read_text().split('Uid:',1)[1].split()[0])==10000:
   assert os.readlink(proc/'exe')=='/usr/bin/wireplumber'
   policies.append(dict(pid=int(proc.name),start_ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19]))
 except OSError:pass
assert len(policies)==1
assert all(Path('/sys/bus/i2c/devices',node,'power/runtime_status').read_text().strip()=='suspended' for node in ['7-0010','9-0010'])
(r/'k240-tools/idle-policy-identity-private.json').write_text(json.dumps(policies[0],indent=2)+'\n')

assert json.loads((r/'k240-baseline/summary.json').read_text())['installed_r15_r10']
binary=r/'k240-tools/upright-paired-probe240';source=r/'k240-tools/native-upright-r2.py'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==binary_sha and hashlib.sha256(source.read_bytes()).hexdigest()==source_sha
compile(source.read_text(),str(source),'exec')
target=Path('/run/samurai-camera240-probes');assert target.is_dir() and (target/'upright-paired-probe240').is_file()
shutil.copyfile(binary,target/'upright-paired-probe240');(target/'upright-paired-probe240').chmod(0o755)
smoke=subprocess.run([str(target/'upright-paired-probe240')],capture_output=True,timeout=5);assert smoke.returncode==2
with (r/'k240-tools/upright-r2-launch-private.log').open('xb') as log:
 p=subprocess.Popen([sys.executable,str(source),'rear','rgb'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (r/'k240-upright-paired-r15-r2/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((r/'k240-upright-paired-r15-r2/state-private.json').read_text());assert s['pid']==p.pid
print(json.dumps(dict(stage=240,launched_once=True,state=s['state'],phase=s['phase'])))
'''
result = host.ssh('python3 - '+build['binary_sha256']+' '+digest, input=code.encode(), timeout=15)
(P / 'upright-r2-launch-host-private.log').write_bytes(result.stdout+result.stderr)
state_path=P/'current-work-private.json';state=json.loads(state_path.read_text())
state.update(state='User upright check: paired24 RAW/RGB 2ms->32ms worker submitted once',
    active_native_context='/var/lib/samurai/k240-upright-paired-r15-r2',
    next='Poll this same native identity; collect summary in bounded chunks; do not start another camera worker')
state_path.write_text(json.dumps(state,indent=2)+'\n')
print(result.stdout.decode().strip())
