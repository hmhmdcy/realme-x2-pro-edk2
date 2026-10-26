from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'flash-validation.json').read_text())['boot_flash_success']
package=json.loads((HERE.parent/'kernel365/boot-package-validation.json').read_text());dt=json.loads((HERE.parent/'kernel365/dt-build-validation.json').read_text());package['firmware_boot_preserved_sha256']=json.loads((HERE/'build-package-validation.json').read_text())['boot_sha256']
code=r'''
from pathlib import Path
import hashlib,json,os
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot!=(root/'k366-deployment/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#363 ') and os.uname().release==meta['release']
assert b'realme,samurai\0' in Path('/sys/firmware/devicetree/base/compatible').read_bytes()
assert b'ROOTFS_ID=samurai-f2fs-rootfs01' in Path('/etc/samurai-rootfs-release').read_bytes()
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
for name,key in [('boot','firmware_boot_preserved_sha256'),('logdump','logdump_sha256')]:assert sha(Path('/dev/disk/by-partlabel')/name)==meta[key]
base=Path('/sys/firmware/devicetree/base');icp=base/'soc@0/icp@ac10000';memory=base/'reserved-memory/memory@9ab00000'
effective=icp.exists();assert effective
if effective:
 assert (icp/'status').read_bytes()==b'disabled\0'
 assert (icp/'memory-region').read_bytes()==(memory/'phandle').read_bytes()==dt['firmware_phandle'].to_bytes(4,'big')
assert (memory/'no-map').exists() and (memory/'reg').read_bytes()==bytes.fromhex('000000009ab000000000000000500000')
assert not Path('/sys/bus/platform/devices/ac10000.icp').exists()
assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')=='1e78064da626b1dd91fc82c183abd96b5fb98f95e11a8eb7b760b9a138095dae'
directory=root/'k366-work';assert not directory.exists();directory.mkdir(mode=0o700);guard=directory/'boot-id-private.txt';guard.write_bytes(boot)
pstore={p.name:p.read_text(errors='replace') for p in Path('/sys/fs/pstore').glob('*') if p.is_file()};(directory/'pstore-at-adoption-private.json').write_text(json.dumps(pstore))
print(json.dumps(dict(stage=366,guard_path=str(guard),release=os.uname().release,new_boot_verified=True,logdump_readback_exact=True,firmware_update_readback_exact=True,firmware_boot_stage=366,
    kernel_image_stage=363,logdump_dt_stage=365,effective_dt_stage=365 if effective else 276,existing_camss_module_verified=True,
    static_icp_present=effective,static_icp_disabled=True,firmware_reference_matches_live_board=effective,dt_only_update_effective=effective,
    pstore_files=len(pstore),taint=int(Path('/proc/sys/kernel/tainted').read_text()))))
'''
q=host.raw_ssh('python3 -c '+shlex.quote('meta='+repr(package)+'\ndt='+repr(dt)+'\n'+code),timeout=45)
(P/'postboot-adoption-private.json').write_bytes(q.stdout);d=json.loads(q.stdout);d.pop('guard_path');(HERE/'postboot-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
