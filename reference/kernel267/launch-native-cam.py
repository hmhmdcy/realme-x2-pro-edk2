"""Launch a single bounded native cam worker under the new guard."""
from pathlib import Path
import base64
import json
import host

R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import base64,json,os,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
assert not (r/'k267-native-cam').exists()
p=r/'k267-tools/native-cam-cycles.py';assert not p.exists();p.write_bytes(base64.b64decode(PAYLOAD))
with (r/'k267-tools/native-cam-worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=267,worker_started=True,pid=child.pid)))
'''.replace('PAYLOAD',repr(base64.b64encode((R/'native-cam-cycles.py').read_bytes()).decode()))
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'native-cam-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
