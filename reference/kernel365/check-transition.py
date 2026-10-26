from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
old=json.loads((HERE.parent/'kernel363/boot-package-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,os
assert os.uname().version.startswith('#363 ') and os.uname().release==meta['release']
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
assert sha('/dev/disk/by-partlabel/boot')==meta['firmware_boot_preserved_sha256']
assert sha('/dev/disk/by-partlabel/logdump')==meta['logdump_sha256']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')=='1e78064da626b1dd91fc82c183abd96b5fb98f95e11a8eb7b760b9a138095dae'
for name in ['acb3000.camss','ac4a000.cci','ac4b000.cci']:assert Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip()=='suspended'
assert not Path('/sys/module/qcom_camss_icp_a5_core').exists() and not Path('/sys/module/camss_icp_a5_boot_test').exists()
assert not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists()
assert json.loads(Path('/var/lib/samurai/k363-deployment/module-install-validation-private.json').read_text())['all778_installed_hashes_verified']
root=Path('/var/lib/samurai/k365-deployment');assert not root.exists();root.mkdir(mode=0o700)
(root/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
print(json.dumps(dict(stage=365,current_kernel_build=363,boot_and_logdump_match_retained_rollback=True,camera_idle=True,icp_resources_clean=True,new_modules_needed=False,dt_only=True)))
'''
q=host.ssh('python3 -c '+shlex.quote('meta='+repr(old)+'\n'+code),timeout=35)
d=json.loads(q.stdout);(HERE/'pre-transition-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
