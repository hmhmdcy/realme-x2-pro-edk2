from pathlib import Path
import base64,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel244');b=(R/'native-power-diag.py').read_bytes();compile(b,'native-power-diag.py','exec')
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();assert not (r/'k244-power-diag').exists()
o=r/'k244-tools';assert not o.exists();o.mkdir(mode=0o700);p=o/'native-power-diag.py';p.write_bytes(base64.b64decode(PAYLOAD));compile(p.read_bytes(),str(p),'exec')
with (o/'worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=244,worker_started=True,pid=child.pid,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
'''.replace('PAYLOAD',repr(base64.b64encode(b).decode()))
x=host.ssh('python3 -',input=code.encode(),timeout=20);(P/'launch-power-diag-private.log').write_bytes(x.stdout+x.stderr);v=json.loads(x.stdout);(R/'power-diag-launch-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
