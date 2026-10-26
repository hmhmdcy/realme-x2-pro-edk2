"""Collect the stock camera HAL for offline integrity-code analysis only."""
from pathlib import Path
import json,shlex,tarfile
import host
code='''
from pathlib import Path
import hashlib,json,os,subprocess,tarfile
root=Path('/var/lib/samurai/k316-oem-hal-source');manifest=root/'source.json'
if manifest.exists():print(manifest.read_text());raise SystemExit(0)
if root.exists():raise RuntimeError('Existing incomplete source collection; inspect before continuing')
if Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes():raise RuntimeError('Device restarted')
block=Path('/dev/disk/by-partlabel/vendor').resolve()
if 'PARTNAME=vendor' not in Path('/sys/class/block',block.name,'uevent').read_text().splitlines():raise RuntimeError('Different partition')
device=Path('/sys/class/block',block.name,'dev').read_text().strip()
if any(line.split()[2]==device for line in Path('/proc/self/mountinfo').read_text().splitlines()):raise RuntimeError('Vendor already mounted; inspect existing mount')
root.mkdir(mode=0o700);mount=Path('/run/k316-oem-hal-ro');mount.mkdir(mode=0o700)
owned=False;rows=[]
try:
 subprocess.run(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec',str(block),str(mount)],check=True,capture_output=True);owned=True
 fields=next(line.split() for line in Path('/proc/mounts').read_text().splitlines() if line.split()[1]==str(mount));options=set(fields[3].split(','))
 if not {'ro','nosuid','nodev','noexec'}<=options or not {'norecovery','noload'}&options:raise RuntimeError('Unexpected mount options')
 candidates=[mount/'lib64/hw/camera.qcom.so',*sorted((mount/'lib64').glob('libcamx*.so'))]
 for source in candidates:
  if not source.is_file() or source.is_symlink():continue
  if not source.resolve().is_relative_to(mount) or source.stat().st_size>64*1024*1024:raise RuntimeError('Unexpected source')
  raw=source.read_bytes()
  if not raw.startswith(b'\\x7fELF'):continue
  target=root/source.name;target.write_bytes(raw);target.chmod(0o600)
  rows.append({'path':source.relative_to(mount).as_posix(),'file':source.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
finally:
 if owned:subprocess.run(['umount',str(mount)],check=True,capture_output=True)
 mount.rmdir()
archive=root/'hal-source.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for row in rows:tar.add(root/row['file'],arcname=row['file'],recursive=False)
report={'files':rows,'read_only_noload_noexec':True,'unmounted':True,'oem_code_executed':False,'unit_data_accessed':False,'archive_bytes':archive.stat().st_size}
manifest.write_text(json.dumps(report)+'\\n');print(json.dumps(report))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=45)
d=json.loads(q.stdout);(host.PRIVATE/'oem-hal-source.json').write_bytes(q.stdout)
q=host.raw_ssh('cat /var/lib/samurai/k316-oem-hal-source/hal-source.tar.gz',timeout=45)
p=host.PRIVATE/'hal-source.tar.gz';p.write_bytes(q.stdout)
out=host.PRIVATE/'hal-source';out.mkdir(exist_ok=True)
with tarfile.open(p,'r:gz') as tar:tar.extractall(out,filter='data')
print(json.dumps(d,indent=2))
