"""Adopt only the planned, readback-verified boot273; preserve old guards/pstore."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'flash-validation.json').read_text())['boot_flash_success']
expected=json.loads((R/'build-package-validation.json').read_text())['boot_sha256']
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
r=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot!=(r/'k273-work/boot-id-private.txt').read_text().strip()
assert os.uname().version.startswith('#183 ') and os.uname().machine=='aarch64'
assert b'realme,samurai\0' in Path('/sys/firmware/devicetree/base/compatible').read_bytes()
assert Path('/sys/firmware/devicetree/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10/compatible').read_bytes()==b'samsung,s5kgw1\0'
assert Path('/sys/firmware/devicetree/base/soc@0/cci@ac4a000/i2c-bus@0/lens@72/compatible').read_bytes()==b'onnn,lc898219xi\0'
device=subprocess.check_output(['findfs','PARTLABEL=boot'],text=True).strip()
assert subprocess.check_output(['lsblk','-ndo','PARTLABEL',device],text=True).strip()=='boot'
data=Path(device).read_bytes();assert len(data)==100663296 and hashlib.sha256(data).hexdigest()==EXPECTED
assert b'ROOTFS_ID=samurai-f2fs-rootfs01' in Path('/etc/samurai-rootfs-release').read_bytes()
assert json.loads((r/'k275-main-transaction/packages-state-private.json').read_text())['exit_code']==0
p=r/'k275-work';assert not p.exists();os.umask(0o077);p.mkdir(mode=0o700);(p/'boot-id-private.txt').write_text(boot+'\n')
pstore={x.name:x.read_text(errors='replace') for x in Path('/sys/fs/pstore').glob('*') if x.is_file()}
(p/'pstore-at-first-inspection-private.json').write_text(json.dumps(pstore))
print(json.dumps(dict(stage=275,boot_id=boot,current_new_boot_verified=True,boot_partition_sha256=EXPECTED,
 matching_candidate_boot_read_back=True,rootfs_marker_preserved=True,kernel_build=183,
 gw1_static_node_present=True,pstore_files=len(pstore),uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))))
'''.replace('EXPECTED',repr(expected))
q=host.raw_ssh('python3 -',input=code.encode(),timeout=30);(P/'postboot-verified-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);d.pop('boot_id');(R/'postboot-identity-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
