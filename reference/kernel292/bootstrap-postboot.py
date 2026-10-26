"""Adopt only the planned new Image and complete matching module tree."""
from pathlib import Path
import json
import host

ROOT=Path(__file__).resolve().parent
assert json.loads((ROOT/'flash-validation.json').read_text())['logdump_flash_success']
package=json.loads((ROOT/'boot-package-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
r=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot!=(r/'k290-work/boot-id-private.txt').read_text().strip()
assert os.uname().machine=='aarch64' and os.uname().version.startswith('#292 ') and os.uname().release==package['release']
assert b'realme,samurai\0' in Path('/sys/firmware/devicetree/base/compatible').read_bytes()
assert b'ROOTFS_ID=samurai-f2fs-rootfs01' in Path('/etc/samurai-rootfs-release').read_bytes()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
for part,expected in [('boot',package['firmware_boot_preserved_sha256']),('logdump',package['logdump_sha256'])]:
 p=Path('/dev/disk/by-partlabel')/part
 assert sha(p)==expected,part
inventory=json.loads((r/'k292-deployment-r2/module-inventory-private.json').read_text());target=Path('/usr/lib/modules')/package['release']
now={str(p.relative_to(target)):sha(p) for p in target.rglob('*.ko')}
assert len(now)==778 and now==inventory
directory=r/'k292-work';assert not directory.exists();directory.mkdir(mode=0o700)
(directory/'boot-id-private.txt').write_text(boot+'\n')
pstore={p.name:p.read_text(errors='replace') for p in Path('/sys/fs/pstore').glob('*') if p.is_file()}
(directory/'pstore-at-adoption-private.json').write_text(json.dumps(pstore))
report=dict(stage=292,boot_id=boot,new_boot_verified=True,kernel_build=292,release=os.uname().release,
            matching_logdump_read_back=True,firmware_boot_preserved=True,all778_installed_modules_verified=True,
            rootfs_marker_preserved=True,pstore_files=len(pstore),uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
print(json.dumps(report))
'''
q=host.raw_ssh('python3 -',input=('package='+repr(package)+'\n'+code).encode(),timeout=35)
(host.PRIVATE/'postboot-verified-private.json').write_bytes(q.stdout)
report=json.loads(q.stdout);report.pop('boot_id')
(ROOT/'postboot-identity-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
