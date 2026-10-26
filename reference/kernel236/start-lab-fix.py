"""Upload checked source/artifact, launch exactly one corrective observer."""
from pathlib import Path
import hashlib
import json
import host

R = Path(__file__).resolve().parent
P = host.PRIVATE
build = json.loads((R / 'lab-fix-build-validation.json').read_text())
tests = json.loads((R / 'live-of-dt-validation.json').read_text())
assert tests['source_sha256'] == build['source_inputs']['qcom-pm8008-imx319-lab.c']
assert tests['results']['actual']['passed']
module = P / 'lab-fix-build-r1/qcom-pm8008-imx319-lab.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest() == build['sha256']
lock = dict(stage=236, old_sha256='22c28914419c2be32d58967c0bbe73f0b2ccfb3ab074dda8830e6619b2f643fc',
            new_sha256=build['sha256'], source_inputs=build['source_inputs'],
            worker_sha256=hashlib.sha256((R / 'native-lab-fix.py').read_bytes()).hexdigest())
path = P / 'lab-fix-lock-private.json'
assert not path.exists()
path.write_text(json.dumps(lock, indent=2) + '\n')
host.upload(module, '/var/lib/samurai/k236-tools/qcom-pm8008-imx319-lab-fix.ko')
host.upload(path, '/var/lib/samurai/k236-tools/lab-fix-lock-private.json')
host.upload(R / 'native-lab-fix.py', '/var/lib/samurai/k236-tools/native-lab-fix.py')
code = r'''
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
assert not (root/'k236-lab-fix').exists()
source=root/'k236-tools/native-lab-fix.py'
lock=json.loads((root/'k236-tools/lab-fix-lock-private.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==lock['worker_sha256']
compile(source.read_text(),str(source),'exec')
with (root/'k236-tools/lab-fix-worker-launch-private.log').open('xb') as output:
 process=subprocess.Popen([sys.executable,str(source)],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (root/'k236-lab-fix/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
state=json.loads((root/'k236-lab-fix/state-private.json').read_text());assert state['pid']==process.pid
print(json.dumps(dict(stage=236,lab_fix_observer_launched_once=True,state=state['state'],phase=state['phase'])))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=15)
(P / 'lab-fix-launch-host-private.log').write_bytes(result.stdout + result.stderr)
state_path = P / 'current-work-private.json'
state = json.loads(state_path.read_text())
state.update(state='same236 boot, one unbound-lab corrective observer launched; trace armed before automatic rear reprobe',
             active_native_context='/var/lib/samurai/k236-lab-fix', active_native_session='lab fix observer',
             next='Poll same lab-fix observer; do not repeat launch, reload, reset or flash')
state_path.write_text(json.dumps(state, indent=2) + '\n')
print(result.stdout.decode().strip())
