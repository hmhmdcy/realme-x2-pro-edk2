"""Reuse matching cached descriptors, extracting only the two changed factory files."""
from pathlib import Path
import ast,gzip,hashlib,json,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
names=['sunny_s5kgw1','qtech_s5kgw1','sunny_imx471','qtech_s5k3m5sx'];inventory=json.loads((P.parent/'kernel298/oem-tuning-inventory-private.json').read_text())['files']
expected={n:next(r for r in inventory if r['path']=='lib64/camera/com.qti.sensormodule.'+n+'.bin') for n in names};selected={};sources={}
for name,row in expected.items():
 old=P.parent/'kernel115/vendor-camera-bins'/Path(row['path']).name
 if old.exists() and hashlib.sha256(old.read_bytes()).hexdigest()==row['sha256']:sources[name]=dict(local_path=str(old),cache_matches_current_factory=True,**row)
 else:selected[name]=row
tree=ast.parse((HERE.parent/'kernel298/oem-tuning-inventory.py').read_text());code=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
code=code.replace("r/'k298-work/boot-id-private.txt'","r/'k305-geometry-r2/boot-id-private.txt'").replace('k298-oem-tuning-inventory','k326-oem-descriptions-r1').replace('k298-oem-tuning-ro','k326-oem-descriptions-ro')
begin=code.index(" for directory in ['lib64/camera'");end=code.index('\nfinally:',begin)
code=code[:begin]+'''
 import gzip
 for name,expected in EXPECTED.items():
  p=mount/expected['path'];assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(mount)
  raw=p.read_bytes();assert len(raw)==expected['bytes'] and hashlib.sha256(raw).hexdigest()==expected['sha256']
  packed=gzip.compress(raw,mtime=0);(root/(name+'-description-private.bin.gz')).write_bytes(packed)
  rows.append(dict(name=name,bytes=len(raw),sha256=expected['sha256'],packed_bytes=len(packed),packed_sha256=hashlib.sha256(packed).hexdigest()))
'''+code[end:]
code=code.replace('stage=298','stage=326').replace('inventory-private.json','source-private.json')
receipt=P/'description-source-private.json'
if '--fetch-only' not in sys.argv:
 assert not receipt.exists()
 q=host.raw_ssh('python3 -',input=('EXPECTED='+repr(selected)+'\n'+code).encode(),timeout=40);receipt.write_bytes(q.stdout)
else:
 q=host.raw_ssh('cat /var/lib/samurai/k326-oem-descriptions-r1/source-private.json',timeout=15);receipt.write_bytes(q.stdout)
result=json.loads(receipt.read_text());assert result['unmounted'] and result['readonly_noload_noexec']
for row in result['files']:
 name=row['name'];dest=P/(name+'-description-private.bin')
 command="from pathlib import Path;import sys;sys.stdout.buffer.write(Path(%r).read_bytes())"%('/var/lib/samurai/k326-oem-descriptions-r1/'+name+'-description-private.bin.gz')
 q=host.raw_ssh('python3 -c '+shlex.quote(command),timeout=20);assert len(q.stdout)==row['packed_bytes'] and hashlib.sha256(q.stdout).hexdigest()==row['packed_sha256']
 raw=gzip.decompress(q.stdout);assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'];dest.write_bytes(raw)
 sources[name]=dict(local_path=str(dest),cache_matches_current_factory=False,**expected[name])
(P/'descriptor-sources-private.json').write_text(json.dumps(sources,indent=2)+'\n')
report=dict(stage=326,sources=[dict(module=n,bytes=s['bytes'],sha256=s['sha256'],reused_existing_cache=s['cache_matches_current_factory']) for n,s in sources.items()],
 readonly_noload_noexec=True,unmounted=True,no_vendor_code_executed=True,no_eeprom_operations=True,passed=True)
(HERE/'descriptor-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
