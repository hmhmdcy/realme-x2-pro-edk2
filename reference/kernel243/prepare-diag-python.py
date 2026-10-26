from pathlib import Path
import base64,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel243')
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
o=r/'k243-diag-python-r3';assert not o.exists();o.mkdir(mode=0o700)
b=base64.b64decode(PAYLOAD);compile(b,'diag_transport.py','exec');(o/'diag_transport.py').write_bytes(b)
print(json.dumps(dict(stage=243,source_sha256=hashlib.sha256(b).hexdigest(),library_staged_no_execution=True)))
'''.replace('PAYLOAD',repr(base64.b64encode((R/'diag_transport.py').read_bytes()).decode()))
x=host.ssh('python3 -',input=code.encode(),timeout=15);(P/'prepare-diag-python-private.log').write_bytes(x.stdout+x.stderr);print(x.stdout.decode())
