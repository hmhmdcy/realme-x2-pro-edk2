from pathlib import Path
import base64,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel246');payloads={n:base64.b64encode((R/n).read_bytes()).decode() for n in ['diag_streaming.py','native-streaming-rf.py','loc_decode.py']}
for n,b in payloads.items():compile(base64.b64decode(b),n,'exec')
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel244/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();o=r/'k246-tools';assert not o.exists() and not (r/'k246-streaming-rf').exists();hashes={};o.mkdir(mode=0o700)
for name,payload in PAYLOADS.items():
 p=o/name;assert not p.exists();b=base64.b64decode(payload);compile(b,name,'exec');p.write_bytes(b);hashes[name]=hashlib.sha256(b).hexdigest()
with (o/'streaming-worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(o/'native-streaming-rf.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=246,worker_started=True,pid=child.pid,source_sha256=hashes)))
'''.replace('PAYLOADS',repr(payloads))
x=host.ssh('python3 -',input=code.encode(),timeout=20);(P/'launch-streaming-private.log').write_bytes(x.stdout+x.stderr);v=json.loads(x.stdout);(R/'streaming-launch-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
