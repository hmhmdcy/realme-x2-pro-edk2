"""Read selected actual vendor init files with ro,noload; do not execute them."""
from pathlib import Path
import hashlib,json,os,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
mount=Path('/run/k243-vendor-ro');assert not mount.exists()
assert 'PARTNAME=vendor' in Path('/sys/class/block/sda9/uevent').read_text().splitlines() and Path('/sys/class/block/sda9/size').read_text().strip()=='3342336'
assert not any(x.split()[2]==Path('/sys/class/block/sda9/dev').read_text().strip() for x in Path('/proc/self/mountinfo').read_text().splitlines())
names=['etc/init/hw/init.qcom.rc','etc/init/hw/init.target.rc','etc/init/vendor.qti.rmt_storage.rc','etc/init/android.hardware.gnss@2.1-service-qti.rc','bin/init.qcom.sh','bin/init.qcom.early_boot.sh','bin/init.qcom.class_core.sh','bin/init.class_main.sh','bin/init.qcom.post_boot.sh']
mount.mkdir(mode=0o700);owned=False;files={}
try:
 subprocess.run(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec','/dev/sda9',str(mount)],capture_output=True,check=True);owned=True
 options=next(x.split()[3] for x in Path('/proc/mounts').read_text().splitlines() if x.split()[1]==str(mount));assert 'ro' in options.split(',') and 'rw' not in options.split(',')
 for name in names:
  p=mount/name
  if not p.exists():files[name]=dict(present=False);continue
  assert not p.is_symlink() and p.stat().st_size<1024*1024
  b=p.read_bytes();files[name]=dict(present=True,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),text=b.decode(errors='replace'))
finally:
 if owned:subprocess.run(['umount',str(mount)],capture_output=True,check=True)
assert not any(x.split()[4]==str(mount) for x in Path('/proc/self/mountinfo').read_text().splitlines())
report=dict(stage=243,current_vendor_ro_noload=True,unmounted=True,selected_files=len(files),present=sum(v['present'] for v in files.values()),no_vendor_code_executed=True,no_nv_or_configuration_writes=True)
print(json.dumps(dict(report=report,private=files)))
