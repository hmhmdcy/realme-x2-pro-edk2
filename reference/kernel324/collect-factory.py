"""Extract three selected stock tuning files with the existing read-only mount path."""
from pathlib import Path
import ast,gzip,hashlib,json,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
names=['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471']
inventory=json.loads((P.parent/'kernel298/oem-tuning-inventory-private.json').read_text())
expected={n:next(r for r in inventory['files'] if r['path']=='lib64/camera/com.qti.tuned.'+n+'.bin') for n in names}
tree=ast.parse((HERE.parent/'kernel298/oem-tuning-inventory.py').read_text())
code=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
code=code.replace("r/'k298-work/boot-id-private.txt'","r/'k305-geometry-r2/boot-id-private.txt'")
code=code.replace('k298-oem-tuning-inventory','k324-oem-selected-tuning-r1').replace('k298-oem-tuning-ro','k324-oem-tuning-ro')
begin=code.index(" for directory in ['lib64/camera'");end=code.index('\nfinally:',begin)
code=code[:begin]+'''
 import gzip
 for name,expected in EXPECTED.items():
  p=mount/expected['path']
  assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(mount)
  raw=p.read_bytes();assert len(raw)==expected['bytes'] and hashlib.sha256(raw).hexdigest()==expected['sha256']
  assert raw.startswith(b'QTI Chromatix Header')
  packed=gzip.compress(raw,compresslevel=3,mtime=0)
  (root/(name+'-tuning-private.bin.gz')).write_bytes(packed)
  rows.append(dict(name=name,path=expected['path'],bytes=len(raw),sha256=expected['sha256'],packed_bytes=len(packed),packed_sha256=hashlib.sha256(packed).hexdigest()))
'''+code[end:]
code=code.replace('stage=298','stage=324').replace('inventory-private.json','source-private.json')
receipt=P/'factory-source-private.json'
if '--fetch-only' not in sys.argv:
 assert not receipt.exists(),'Inspect saved extraction instead of repeating the mount'
 q=host.raw_ssh('python3 -',input=('EXPECTED='+repr(expected)+'\n'+code).encode(),timeout=55)
 receipt.write_bytes(q.stdout)
else:
 q=host.raw_ssh("cat /var/lib/samurai/k324-oem-selected-tuning-r1/source-private.json",timeout=15)
 receipt.write_bytes(q.stdout)
source=json.loads(receipt.read_text());assert source['unmounted'] and source['readonly_noload_noexec']
for row in source['files']:
 name=row['name'];dest=P/(name+'-tuning-private.bin')
 if dest.exists():
  assert len(dest.read_bytes())==row['bytes'];continue
 command="from pathlib import Path;import sys;sys.stdout.buffer.write(Path(%r).read_bytes())"%('/var/lib/samurai/k324-oem-selected-tuning-r1/'+name+'-tuning-private.bin.gz')
 q=host.raw_ssh('python3 -c '+shlex.quote(command),timeout=40)
 assert len(q.stdout)==row['packed_bytes'] and hashlib.sha256(q.stdout).hexdigest()==row['packed_sha256']
 (P/(name+'-tuning-private.bin.gz')).write_bytes(q.stdout)
 raw=gzip.decompress(q.stdout);assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'];dest.write_bytes(raw)
report=dict(stage=324,files=[{k:r[k] for k in ['name','bytes','sha256']} for r in source['files']],source_from_retained_factory_vendor=True,
 readonly_noload_noexec=True,unmounted=True,no_vendor_code_executed=True,no_individual_calibration_writes=True,transfer_verified=True,passed=True)
(HERE/'factory-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
