from pathlib import Path
import base64,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel246');b=(R/'native-quiesce.py').read_bytes();compile(b,'native-quiesce.py','exec')
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel244/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();assert not (r/'k246-quiesce').exists()
p=r/'k246-tools/native-quiesce.py';assert not p.exists();p.write_bytes(base64.b64decode(PAYLOAD));compile(p.read_bytes(),str(p),'exec')
with (r/'k246-tools/quiesce-worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=246,worker_started=True,pid=child.pid,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
'''.replace('PAYLOAD',repr(base64.b64encode(b).decode()))
x=host.ssh('python3 -',input=code.encode(),timeout=20);(P/'quiesce-launch-private.log').write_bytes(x.stdout+x.stderr);v=json.loads(x.stdout);(R/'quiesce-launch-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
