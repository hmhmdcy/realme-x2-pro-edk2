"""Extract three selected factory tuning files read-only; never execute them."""
from pathlib import Path
import gzip,hashlib,json,shlex
import host
HERE=Path(__file__).resolve().parent
inventory=json.loads((host.PRIVATE.parent/'kernel298/oem-tuning-inventory-private.json').read_text())
names=['com.qti.tuned.sunny_s5kgw1.bin','com.qti.tuned.qtech_s5kgw1.bin','com.qti.tuned.sunny_imx471.bin']
expected={name:next(r for r in inventory['files'] if r['path']=='lib64/camera/'+name) for name in names}
code=r'''
from pathlib import Path
import gzip,hashlib,json,subprocess
root=Path('/var/lib/samurai/k309-factory')
root.mkdir(mode=0o700)
block=Path('/dev/disk/by-partlabel/vendor').resolve()
if 'PARTNAME=vendor' not in Path('/sys/class/block',block.name,'uevent').read_text().splitlines():raise RuntimeError('Wrong source partition')
dev=Path('/sys/class/block',block.name,'dev').read_text().strip()
if any(l.split()[2]==dev for l in Path('/proc/self/mountinfo').read_text().splitlines()):raise RuntimeError('Vendor is already mounted')
mount=Path('/run/k309-vendor-ro');mount.mkdir(mode=0o700)
owned=False;rows=[]
try:
    subprocess.run(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec',str(block),str(mount)],check=True,capture_output=True);owned=True
    for name,expected in EXPECTED.items():
        p=mount/'lib64/camera'/name
        raw=p.read_bytes()
        if len(raw)!=expected['bytes'] or hashlib.sha256(raw).hexdigest()!=expected['sha256']:raise RuntimeError('Factory source changed')
        packed=gzip.compress(raw,compresslevel=1,mtime=0)
        (root/(name+'.gz')).write_bytes(packed)
        rows.append({'name':name,'bytes':len(raw),'sha256':expected['sha256'],'packed_bytes':len(packed)})
finally:
    if owned:subprocess.run(['umount',str(mount)],check=True,capture_output=True)
    mount.rmdir()
print(json.dumps({'stage':309,'readonly_noload_noexec':True,'unmounted':True,'files':rows}))
'''
q=host.ssh('python3 -c '+shlex.quote(code.replace('EXPECTED',repr(expected))),timeout=70)
report=json.loads(q.stdout)
(host.PRIVATE/'factory-source.json').write_bytes(q.stdout)
for row in report['files']:
    name=row['name']
    remote="from pathlib import Path;import sys;sys.stdout.buffer.write(Path("+repr('/var/lib/samurai/k309-factory/'+name+'.gz')+").read_bytes())"
    q=host.raw_ssh('python3 -c '+shlex.quote(remote),timeout=40)
    raw=gzip.decompress(q.stdout)
    if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise RuntimeError('Transfer mismatch')
    (host.PRIVATE/name).write_bytes(raw)
(HERE/'factory-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
