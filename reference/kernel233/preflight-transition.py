"""Check the exact uploaded restart path before freezing this boot."""
from pathlib import Path
import hashlib,json,os,subprocess
root=Path('/var/lib/samurai');tools=root/'k233-tools'
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(root/'k233-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert {p.parent.name:p.read_text().strip() for p in Path('/sys/module').glob('*/taint') if p.read_text().strip()}=={}
manifest=json.loads((tools/'uploaded-sources-private.json').read_text())
for name,digest in manifest.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
assert '/var/lib/samurai/k233-tools/linux-restart2-bootloader.py' in manifest
assert '/tmp/k233-freeze-for-bootloader.sh' in manifest
assert not Path('/run/k233-linux-restart2-phase-private.json').exists()
assert not Path('/run/k233-bootloader-state').exists()
p=subprocess.run(['python3','/tmp/k233-check-quiesce.py'],capture_output=True,timeout=15)
(tools/'final-preflight-quiesce-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
print(json.dumps(dict(stage=233,exact_uploaded_paths_verified=True,fresh_boot_guard_verified=True,quiesce_rechecked=True,freeze_not_started=True,fastrpc_refcount=int(Path('/sys/module/fastrpc/refcnt').read_text()))))
