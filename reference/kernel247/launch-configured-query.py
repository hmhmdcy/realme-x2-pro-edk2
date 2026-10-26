from pathlib import Path
import base64,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel247');payload={name:base64.b64encode((R/name).read_bytes()).decode() for name in ['native-configured-query.py','memshare_configured.py','loc_decode.py']}
spec=importlib.util.spec_from_file_location('host',R/'host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k247-runtime/boot-id-private.txt').read_bytes();target=r/'k247-query-tools';assert not target.exists();target.mkdir(mode=0o700);hashes={}
for name,encoded in PAYLOAD.items():
 b=base64.b64decode(encoded);compile(b,name,'exec');(target/name).write_bytes(b);hashes[name]=hashlib.sha256(b).hexdigest()
with (target/'worker-private.log').open('xb') as log:child=subprocess.Popen(['python3',str(target/'native-configured-query.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=247,worker_started=True,pid=child.pid,source_sha256=hashes)))
'''.replace('PAYLOAD',repr(payload))
x=host.ssh('python3 -',input=code.encode(),timeout=20);(P/'configured-query-launch-private.log').write_bytes(x.stdout+x.stderr);v=json.loads(x.stdout);(R/'configured-query-launch-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
