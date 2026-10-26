"""Submit one verified quiesce worker and record its process identity."""
from pathlib import Path
import json
import host

code=r'''
from pathlib import Path
import json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k296-work/boot-id-private.txt').read_bytes()
assert not (r/'k297-quiesce').exists()
with (r/'k297-tools/quiesce-worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(r/'k297-tools/native-quiesce.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=297,pid=child.pid,start_ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19])))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
path=host.PRIVATE/'quiesce-launch-private.json';assert not path.exists();path.write_bytes(q.stdout)
print(q.stdout.decode())
