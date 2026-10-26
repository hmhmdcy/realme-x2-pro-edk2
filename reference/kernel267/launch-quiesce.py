"""Upload transition code and start exactly one detached current-boot worker."""
from pathlib import Path
import base64
import hashlib
import json
import host

R=Path(__file__).resolve().parent
assert json.loads((R/'module-transaction-validation.json').read_text())['all_loaded_modules_still_original']
sources={n:base64.b64encode((R/n).read_bytes()).decode() for n in ['native-quiesce.py','restart-bootloader.py']}
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k260-work/boot-id-private.txt').read_bytes()
assert not (r/'k267-quiesce').exists()
p=r/'k267-tools';p.mkdir(mode=0o700)
for name,data in SOURCES.items():
 (p/name).write_bytes(base64.b64decode(data));compile((p/name).read_bytes(),name,'exec')
with (p/'quiesce-worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p/'native-quiesce.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=267,worker_started=True,pid=child.pid,source_sha256=hashlib.sha256((p/'native-quiesce.py').read_bytes()).hexdigest())))
'''.replace('SOURCES',repr(sources))
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'quiesce-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
