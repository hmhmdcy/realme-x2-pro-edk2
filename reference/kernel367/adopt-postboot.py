from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'restart-validation.json').read_text())['partitions_written']==[]
package=json.loads((HERE.parent/'kernel365/boot-package-validation.json').read_text());package['firmware_boot_preserved_sha256']=json.loads((HERE.parent/'kernel366/build-package-validation.json').read_text())['boot_sha256']
code=r'''
from pathlib import Path
import hashlib,json,os
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot!=(root/'k367-deployment/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#363 ') and os.uname().release==meta['release']
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
for name,key in [('boot','firmware_boot_preserved_sha256'),('logdump','logdump_sha256')]:assert sha(Path('/dev/disk/by-partlabel')/name)==meta[key]
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/firmware/devicetree/base/soc@0/icp@ac10000/status').read_bytes()==b'disabled\0'
for name in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test']:assert not Path('/sys/module',name).exists()
directory=root/'k367-work';assert not directory.exists();directory.mkdir(mode=0o700);guard=directory/'boot-id-private.txt';guard.write_bytes(boot)
print(json.dumps(dict(stage=367,guard_path=str(guard),new_boot_verified=True,logdump_readback_exact=True,boot_readback_exact=True,
 kernel_image_stage=363,firmware_boot_stage=366,dt_stage=365,icp_disabled=True,taint=0,partition_writes=0)))
'''
q=host.raw_ssh('python3 -c '+shlex.quote('meta='+repr(package)+'\n'+code),timeout=40);(P/'postboot-adoption-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);d.pop('guard_path');(HERE/'postboot-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
