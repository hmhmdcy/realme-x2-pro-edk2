"""Launch exactly one observer after a newly discovered, strictly keyed USB peer."""
from pathlib import Path
import json
import host

ref = Path(__file__).resolve().parent
host.upload(ref / 'collect-newboot.py', '/var/lib/samurai/k228-tools/collect-newboot.py')
code = r'''
from pathlib import Path
import json,os,subprocess,sys,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()!=(root/'k228-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and not (root/'k228-runtime').exists()
with (root/'k228-tools/runtime-observer-launch-private.log').open('xb') as output:
 p=subprocess.Popen([sys.executable,str(root/'k228-tools/collect-newboot.py')],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (root/'k228-runtime/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
s=json.loads((root/'k228-runtime/state-private.json').read_text());assert s['pid']==p.pid
print(json.dumps(dict(new_identity_observed=True,observer_launched_once=True,state=s['state'])))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=15)
(host.PRIVATE / 'observer-launch-host-private.log').write_bytes(result.stdout + result.stderr)
state = json.loads((host.PRIVATE / 'current-work-private.json').read_text())
state.update(state='new Linux boot observed; single runtime observer running',
             active_native_context='/var/lib/samurai/k228-runtime', active_native_session='runtime observer',
             transition_pending=False, guard='/var/lib/samurai/k228-runtime/boot-id-private.txt')
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(result.stdout.decode().strip())
