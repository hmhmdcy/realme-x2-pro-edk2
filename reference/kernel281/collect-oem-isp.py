"""Privately copy the factory HAL for static interoperability research, never execution."""
from pathlib import Path
import gzip
import hashlib
import json
import shlex
import host

ROOT = Path(__file__).resolve().parent
code = r'''
from pathlib import Path
import gzip,hashlib,json,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
root=Path('/var/lib/samurai/k281-oem-isp-static')
receipt=root/'collection-private.json'
if receipt.exists():
 print(receipt.read_text())
else:
 assert not root.exists(), 'Inspect unfinished collection before reuse'
 block=Path('/dev/disk/by-partlabel/vendor').resolve()
 assert block.name=='sda9'
 assert 'PARTNAME=vendor' in Path('/sys/class/block/sda9/uevent').read_text().splitlines()
 assert Path('/sys/class/block/sda9/size').read_text().strip()=='3342336'
 device=Path('/sys/class/block/sda9/dev').read_text().strip()
 assert not any(line.split()[2]==device for line in Path('/proc/self/mountinfo').read_text().splitlines())
 mount=Path('/run/k281-vendor-isp-static-ro');assert not mount.exists()
 root.mkdir(mode=0o700);mount.mkdir(mode=0o700);owned=False
 try:
  subprocess.run(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec',str(block),str(mount)],capture_output=True,check=True);owned=True
  line=next(l for l in Path('/proc/mounts').read_text().splitlines() if l.split()[1]==str(mount))
  options=set(line.split()[3].split(','))
  assert {'ro','nosuid','nodev','noexec'}<=options and 'rw' not in options and ('norecovery' in options or 'noload' in options)
  source=mount/'lib64/hw/camera.qcom.so';assert not source.is_symlink()
  data=source.read_bytes();assert len(data)==6087920 and data[:4]==b'\x7fELF'
  packed=gzip.compress(data,mtime=0)
  target=root/'camera.qcom.so-private.gz';target.write_bytes(packed);target.chmod(0o600)
  report=dict(source='vendor:lib64/hw/camera.qcom.so',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
   packed_bytes=len(packed),packed_sha256=hashlib.sha256(packed).hexdigest(),readonly_noload_noexec=True,no_oem_code_executed=True)
 finally:
  if owned:subprocess.run(['umount',str(mount)],capture_output=True,check=True)
 assert not any(line.split()[2]==device for line in Path('/proc/self/mountinfo').read_text().splitlines())
 mount.rmdir();report['unmounted']=True
 receipt.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
run = host.ssh('python3 -', input=code.encode(), timeout=35)
report = json.loads(run.stdout)
(host.PRIVATE / 'oem-collection-private.json').write_bytes(run.stdout)
target = host.PRIVATE / 'camera.qcom.so-private.gz'
parts = host.PRIVATE / 'hal-parts-private'
parts.mkdir(mode=0o700, exist_ok=True)
for offset in range(0, report['packed_bytes'], 131072):
    part = parts / str(offset)
    if part.exists():
        continue
    count = min(131072, report['packed_bytes'] - offset)
    fetch = "from pathlib import Path;import sys;b=Path('/var/lib/samurai/k281-oem-isp-static/camera.qcom.so-private.gz').read_bytes();sys.stdout.buffer.write(b[%d:%d])" % (offset, offset + count)
    run = host.ssh('python3 -c ' + shlex.quote(fetch), timeout=20)
    assert len(run.stdout) == count
    part.write_bytes(run.stdout)
target.write_bytes(b''.join((parts / str(offset)).read_bytes() for offset in range(0, report['packed_bytes'], 131072)))
assert hashlib.sha256(target.read_bytes()).hexdigest() == report['packed_sha256']
data = gzip.decompress(target.read_bytes())
assert hashlib.sha256(data).hexdigest() == report['sha256']
binary = host.PRIVATE / 'camera.qcom.so-private'
binary.write_bytes(data)
binary.chmod(0o600)
(ROOT / 'oem-hal-source-validation.json').write_text(json.dumps(dict(stage=281, **report,
    private_binary_not_published=True, static_analysis_only=True), indent=2) + '\n')
print(json.dumps(report, indent=2))
