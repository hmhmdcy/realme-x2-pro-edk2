"""Read current boot hash and live FDT once; no partition writes."""
from pathlib import Path
import base64
import hashlib
import importlib.util
import json
import shlex

ref=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('window',ref/'device-window.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/boot-baseline')
private.mkdir(mode=0o700,exist_ok=True)
assert not (private/'metadata-private.json').exists()
code="""from pathlib import Path
import base64,hashlib,json,subprocess
p=Path('/dev/disk/by-partlabel/boot');size=int(subprocess.check_output(['blockdev','--getsize64',str(p)]))
assert size==100663296
with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
fdt=Path('/sys/firmware/fdt').read_bytes()
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'boot_bytes':size,'boot_sha256':digest,'fdt_base64':base64.b64encode(fdt).decode(),'taint':int(Path('/proc/sys/kernel/tainted').read_text())}))
"""
q=w.host.ssh('python3 -c '+shlex.quote(code),timeout=35);q.check_returncode()
data=json.loads(q.stdout)
raw=base64.b64decode(data.pop('fdt_base64'));(private/'live-private.dtb').write_bytes(raw)
data['fdt_sha256']=hashlib.sha256(raw).hexdigest()
(private/'metadata-private.json').write_text(json.dumps(data,indent=2))
expected=json.loads((ref.parent/'kernel390/flash-validation.json').read_text())
assert data['boot_sha256']==expected['boot_sha256'] and data['taint']==0
report={k:v for k,v in data.items() if k!='boot_id'}
report['matches_current_deployed_boot390']=True;report['partition_writes']=0
(ref/'boot-baseline-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
