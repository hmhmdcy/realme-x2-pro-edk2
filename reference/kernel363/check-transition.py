"""Check the running deployed combination and exact rollback before switching."""
from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
old=json.loads((HERE.parent/'kernel298/boot-package-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
assert os.uname().version.startswith('#298 ') and os.uname().release=='7.3.0-rc6-rmx1931-samurai-k298+'
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
assert sha('/dev/disk/by-partlabel/boot')==meta['firmware_boot_preserved_sha256']
assert sha('/dev/disk/by-partlabel/logdump')==meta['logdump_sha256']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')=='d8c0f30d189aa8e69e377ba58c891955f3bc795abfb6b8ed6a9562a1d118333a'
for name in ['acb3000.camss','ac4a000.cci','ac4b000.cci']:assert Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip()=='suspended'
assert json.loads(Path('/var/lib/samurai/k363-deployment/module-install-validation-private.json').read_text())['all778_installed_hashes_verified']
print(json.dumps(dict(stage=363,current_kernel_build=298,boot_and_logdump_match_retained_rollback=True,installed362_gamma_module_confirmed=True,camera_idle=True,new_modules_staged=True,no_transition_requested=True)))
'''
q=host.ssh('python3 -c '+shlex.quote('meta='+repr(old)+'\n'+code),timeout=35)
d=json.loads(q.stdout);(HERE/'pre-transition-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
