from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'flash-validation.json').read_text())['logdump_flash_success']
package=json.loads((HERE/'boot-package-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,os
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot!=(root/'k363-deployment/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#363 ') and os.uname().release==meta['release']
assert b'realme,samurai\0' in Path('/sys/firmware/devicetree/base/compatible').read_bytes()
assert b'ROOTFS_ID=samurai-f2fs-rootfs01' in Path('/etc/samurai-rootfs-release').read_bytes()
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
for name,key in [('boot','firmware_boot_preserved_sha256'),('logdump','logdump_sha256')]:assert sha(Path('/dev/disk/by-partlabel')/name)==meta[key]
inventory=json.loads((root/'k363-deployment/module-inventory-private.json').read_text());modules=Path('/usr/lib/modules')/meta['release']
assert len(inventory)==778 and inventory=={str(p.relative_to(modules)):sha(p) for p in modules.rglob('*.ko')}
directory=root/'k363-work';assert not directory.exists();directory.mkdir(mode=0o700);guard=directory/'boot-id-private.txt';guard.write_bytes(boot)
pstore={p.name:p.read_text(errors='replace') for p in Path('/sys/fs/pstore').glob('*') if p.is_file()};(directory/'pstore-at-adoption-private.json').write_text(json.dumps(pstore))
print(json.dumps(dict(stage=363,guard_path=str(guard),release=os.uname().release,new_boot_verified=True,logdump_readback_exact=True,firmware_preserved=True,all778_installed_modules_verified=True,pstore_files=len(pstore),taint=int(Path('/proc/sys/kernel/tainted').read_text()))))
'''
q=host.raw_ssh('python3 -c '+shlex.quote('meta='+repr(package)+'\n'+code),timeout=45)
(P/'postboot-adoption-private.json').write_bytes(q.stdout);d=json.loads(q.stdout);d.pop('guard_path');(HERE/'postboot-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
