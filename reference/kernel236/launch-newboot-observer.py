"""Launch one preinstalled observer after confirming a different Linux boot."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()!=(root/'k236-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and not (root/'k236-runtime').exists()
source=root/'k236-tools/collect-newboot.py'
manifest=json.loads((root/'k236-tools/uploaded-sources-private.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest[str(source)]
with (root/'k236-tools/runtime-observer-launch-private.log').open('xb') as output:
 process=subprocess.Popen([sys.executable,str(source)],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (root/'k236-runtime/state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
state=json.loads((root/'k236-runtime/state-private.json').read_text());assert state['pid']==process.pid
print(json.dumps(dict(new_identity_observed=True,observer_launched_once=True,state=state['state'])))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=15)
(host.PRIVATE / 'observer-launch-host-private.log').write_bytes(result.stdout + result.stderr)
state_path = host.PRIVATE / 'current-work-private.json'
state = json.loads(state_path.read_text())
state.update(state='new Linux boot observed; single runtime observer launched',
             active_native_context='/var/lib/samurai/k236-runtime', active_native_session='runtime observer',
             transition_pending=False, guard='/var/lib/samurai/k236-runtime/boot-id-private.txt')
state_path.write_text(json.dumps(state, indent=2) + '\n')
print(result.stdout.decode().strip())
