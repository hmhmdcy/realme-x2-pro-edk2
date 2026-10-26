"""Read-only factory vendor tuning inventory; private metadata only."""
from pathlib import Path
import json,sys
sys.path.insert(0,'/mnt/e/RealmeX2Pro edk2/reference/kernel298')
import host
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k298-work/boot-id-private.txt').read_bytes()
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k298+'
root=r/'k298-oem-tuning-inventory';assert not root.exists();root.mkdir(mode=0o700)
block=Path('/dev/disk/by-partlabel/vendor').resolve();assert block.name=='sda9'
assert 'PARTNAME=vendor' in Path('/sys/class/block/sda9/uevent').read_text().splitlines()
assert Path('/sys/class/block/sda9/size').read_text().strip()=='3342336'
dev=Path('/sys/class/block/sda9/dev').read_text().strip()
assert not any(l.split()[2]==dev for l in Path('/proc/self/mountinfo').read_text().splitlines())
mount=Path('/run/k298-oem-tuning-ro');assert not mount.exists();mount.mkdir(mode=0o700);owned=False
rows=[]
try:
 subprocess.run(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec',str(block),str(mount)],check=True,capture_output=True);owned=True
 line=next(l for l in Path('/proc/mounts').read_text().splitlines() if l.split()[1]==str(mount));opts=set(line.split()[3].split(','))
 assert {'ro','nosuid','nodev','noexec'}<=opts and 'rw' not in opts and bool({'norecovery','noload'}&opts)
 for directory in ['lib64/camera','lib/camera','etc/camera']:
  parent=mount/directory
  if not parent.is_dir():continue
  for p in sorted(parent.rglob('*')):
   if not p.is_file() or p.is_symlink():continue
   assert p.resolve().is_relative_to(mount)
   size=p.stat().st_size;assert size<128*1024*1024
   with p.open('rb') as f:magic=f.read(96)
   row=dict(path=str(p.relative_to(mount)),bytes=size,chromatix_header=magic.startswith(b'QTI Chromatix Header'),elf=magic.startswith(b'\x7fELF'))
   if p.suffix.lower() in ['.bin','.xml']:
    row['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
   rows.append(row)
finally:
 if owned:subprocess.run(['umount',str(mount)],check=True,capture_output=True)
assert not any(l.split()[2]==dev for l in Path('/proc/self/mountinfo').read_text().splitlines());mount.rmdir()
report=dict(stage=298,source_partition='vendor',readonly_noload_noexec=True,unmounted=True,no_oem_code_executed=True,no_calibration_reads_or_writes=True,files=rows)
(root/'inventory-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=45)
p=host.PRIVATE/'oem-tuning-inventory-private.json';assert not p.exists();p.write_bytes(q.stdout)
d=json.loads(q.stdout)
print(json.dumps(dict(files=len(d['files']),chromatix_header_files=sum(v['chromatix_header'] for v in d['files']),matched_names=[dict(path=v['path'],bytes=v['bytes'],chromatix_header=v['chromatix_header']) for v in d['files'] if any(x in v['path'].lower() for x in ['imx319','tuned','chromatix'])],unmounted=d['unmounted']),indent=2))
