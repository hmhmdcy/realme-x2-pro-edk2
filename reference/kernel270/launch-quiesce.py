"""Start one current-boot hardware quiesce worker and return its live identity."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
assert json.loads((R/'rollback-validation.json').read_text())['pc_and_phone_module_rollback_verified']
code=r'''
from pathlib import Path
import json,os,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k269-work/boot-id-private.txt').read_bytes()
assert not (root/'k270-quiesce').exists()
with (root/'k270-tools/quiesce-worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(root/'k270-tools/native-quiesce.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=270,worker_started=True,pid=child.pid,start_ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19])))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'quiesce-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
