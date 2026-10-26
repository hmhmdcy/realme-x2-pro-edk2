from pathlib import Path
import base64,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel242')
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
o=r/'k242-tools';assert not o.exists();o.mkdir(mode=0o700)
p=o/'native-clock-session.py';p.write_bytes(base64.b64decode(PAYLOAD));compile(p.read_bytes(),str(p),'exec')
with (o/'worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=242,worker_started=True,pid=child.pid,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
'''.replace('PAYLOAD',repr(base64.b64encode((R/'native-clock-session.py').read_bytes()).decode()))
p=host.ssh('python3 -',input=code.encode(),timeout=20)
(P/'clock-launch-private.log').write_bytes(p.stdout+p.stderr);print(p.stdout.decode())
