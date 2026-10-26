"""Privately extract the current handset factory tuning, never execute it."""
from pathlib import Path
import ast,hashlib,json,shlex,sys
sys.path.insert(0,'/mnt/e/RealmeX2Pro edk2/reference/kernel298')
import host
P=host.PRIVATE
tree=ast.parse((P/'inventory-oem-tuning-private.py').read_text());original=next(n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
code=original.replace('k298-oem-tuning-inventory','k298-oem-tuning-source').replace('k298-oem-tuning-ro','k298-oem-tuning-source-ro')
a=code.index(" for directory in ['lib64/camera'");b=code.index('\nfinally:',a)
code=code[:a]+'''
 import gzip
 p=mount/'lib64/camera/com.qti.tuned.sunny_imx319.bin'
 assert p.is_file() and not p.is_symlink()
 data=p.read_bytes();assert len(data)==EXPECTED['bytes'] and hashlib.sha256(data).hexdigest()==EXPECTED['sha256']
 assert data.startswith(b'QTI Chromatix Header')
 packed=gzip.compress(data,mtime=0);(root/'sunny-imx319-tuning-private.bin.gz').write_bytes(packed)
 rows.append(dict(path=str(p.relative_to(mount)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),packed_bytes=len(packed),packed_sha256=hashlib.sha256(packed).hexdigest()))
'''+code[b:]
code=code.replace("inventory-private.json","source-private.json")
expected=next(r for r in json.loads((P/'oem-tuning-inventory-private.json').read_text())['files'] if r['path']=='lib64/camera/com.qti.tuned.sunny_imx319.bin')
q=host.ssh('python3 -',input=('EXPECTED='+repr(expected)+'\n'+code).encode(),timeout=45)
receipt=json.loads(q.stdout);(P/'imx319-tuning-source-private.json').write_bytes(q.stdout)
row=receipt['files'][0];data=bytearray()
for offset in range(0,row['packed_bytes'],262144):
 end=min(offset+262144,row['packed_bytes'])
 command=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k298-oem-tuning-source/sunny-imx319-tuning-private.bin.gz').read_bytes();assert len(b)=={row['packed_bytes']};sys.stdout.buffer.write(b[{offset}:{end}])"
 q=host.ssh('python3 -c '+shlex.quote(command),timeout=20);assert len(q.stdout)==end-offset;data.extend(q.stdout)
assert hashlib.sha256(data).hexdigest()==row['packed_sha256']
p=P/'sunny-imx319-tuning-private.bin.gz';assert not p.exists();p.write_bytes(data)
import gzip,struct
raw=gzip.decompress(data);assert hashlib.sha256(raw).hexdigest()==row['sha256']
(P/'sunny-imx319-tuning-private.bin').write_bytes(raw)
table,count=struct.unpack_from('<II',raw,0x98);assert table+count*24<=len(raw) and count<=16
sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
out=dict(bytes=len(raw),sha256=row['sha256'],table_offset=table,sections=sections,private_source_transferred_and_verified=True,unmounted=receipt['unmounted'])
(P/'imx319-tuning-container-private.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
