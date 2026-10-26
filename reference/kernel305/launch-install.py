"""Submit the one transaction as an identifiable detached worker."""
from pathlib import Path
import base64,json,shlex
import host
HERE=Path(__file__).resolve().parent
proof=json.loads((HERE/'intree-module-stage-validation.json').read_text())
build=json.loads((HERE/'kernel-build-validation.json').read_text())
assert proof['intree'] and proof['new_sha256']==build['module_sha256']
proof['vermagic']=build['vermagic']
worker=(HERE/'native-install-geometry.py').read_bytes();compile(worker,str(HERE/'native-install-geometry.py'),'exec')
code=f'''
from pathlib import Path
import base64,json,os,subprocess
root=Path('/var/lib/samurai/k305-geometry-r3')
assert not (root/'worker-private.py').exists() and not (root/'transaction-state-private.json').exists()
worker=root/'worker-private.py';worker.write_bytes(base64.b64decode({base64.b64encode(worker).decode()!r}))
(root/'install-proof-private.json').write_text(json.dumps({proof!r},indent=2)+'\\n')
with (root/'worker-launch-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(worker),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 fields=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()
 receipt=dict(pid=child.pid,start_ticks=fields[19]);(root/'launch-identity-private.json').write_text(json.dumps(receipt)+'\\n')
 print(json.dumps(receipt))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/'install-r3-launch-private.json').write_bytes(q.stdout)
print(q.stdout.decode())
