"""Stage and detach a single bounded worker; never replace an existing run."""
from pathlib import Path
import base64,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel243')
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
source=(R/'native-gnss-diag.py').read_bytes();compile(source,'native-gnss-diag.py','exec')
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert not (r/'k243-gnss-diag').exists()
o=r/'k243-tools';assert not o.exists();o.mkdir(mode=0o700)
p=o/'native-gnss-diag.py';p.write_bytes(base64.b64decode(PAYLOAD));compile(p.read_bytes(),str(p),'exec')
with (o/'worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=243,worker_started=True,pid=child.pid,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
'''.replace('PAYLOAD',repr(base64.b64encode(source).decode()))
p=host.ssh('python3 -',input=code.encode(),timeout=20)
(P/'gnss-diag-launch-private.log').write_bytes(p.stdout+p.stderr);v=json.loads(p.stdout)
(R/'gnss-diag-launch-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
