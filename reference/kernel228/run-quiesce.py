"""Start one detached quiesce worker and retain its exact process identity."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import json,os,subprocess,sys,time
root=Path('/var/lib/samurai');out=root/'k228-quiesce-runner'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k228-baseline/boot-id-private.txt').read_bytes()
assert json.loads((root/'k228-module-install/transaction-state-private.json').read_text())['state']=='verified'
assert not out.exists() and not (root/'k228-quiesce').exists()
for name in ['display','radio']:assert Path('/sys/kernel/tracing/instances',name,'tracing_on').exists()
assert Path('/sys/bus/platform/devices/88e0000.serial/driver').resolve().name=='qcom_eud_com'
assert Path('/sys/kernel/debug/dri/1/clients').exists()
out.mkdir(mode=0o700)
worker=out/'worker-private.py'
worker.write_text("""from pathlib import Path
import json,os,subprocess,time
p=Path('/var/lib/samurai/k228-quiesce-runner')
with (p/'quiesce-private.log').open('xb') as log:
 child=subprocess.Popen(['sh','/tmp/k228-quiesce-current183.sh'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
 identity=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
 state=dict(state='running',worker_pid=os.getpid(),worker_start_ticks=identity,child_pid=child.pid)
 (p/'state-private.json').write_text(json.dumps(state)+'\\n')
 code=child.wait()
 state.update(state='terminal',exit_code=code)
 (p/'state-private.json').write_text(json.dumps(state)+'\\n')
""")
with (out/'worker-launch-private.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,str(worker)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+3
while not (out/'state-private.json').exists() and time.monotonic()<deadline:time.sleep(.05)
assert (out/'state-private.json').exists()
state=json.loads((out/'state-private.json').read_text());assert state['worker_pid']==child.pid
print(json.dumps(dict(stage=228,quiesce_started_once=True,state=state['state'],native_context=str(out))))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=15)
(host.PRIVATE / 'quiesce-launch-host-private.log').write_bytes(result.stdout + result.stderr)
state = json.loads((host.PRIVATE / 'current-work-private.json').read_text())
state.update(state='quiesce worker launched once; observe same native context',
             active_native_context='/var/lib/samurai/k228-quiesce-runner', active_native_session='native worker')
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(result.stdout.decode().strip())
