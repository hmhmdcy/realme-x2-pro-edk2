from pathlib import Path
import hashlib,json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
inventory=json.loads((P/'recovered-inventory-private.json').read_text());assert not inventory['worker_pids'] and inventory['taint']=='0'
assert not inventory['modules']['qcom_camss_icp_a5_core'] and not inventory['modules']['camss_icp_a5_boot_test']
assert not inventory['temporary_dt_nodes'] and not any(inventory['icp_bps_ipe_clock_refs'].values())
expected=inventory['boot_id'];firmware_sha=hashlib.sha256((P.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes()).hexdigest()
package=json.loads((HERE.parent/'kernel366/build-package-validation.json').read_text());fat=json.loads((HERE.parent/'kernel365/boot-package-validation.json').read_text())
code=r'''
from pathlib import Path
import hashlib,json,os
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==expected
assert boot!=Path('/var/lib/samurai/k377-recovered/boot-id-private.txt').read_text().strip()
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+'
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
assert sha('/dev/disk/by-partlabel/boot')==package['boot_sha256'] and sha('/dev/disk/by-partlabel/logdump')==fat['logdump_sha256']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for name in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test']:assert not Path('/sys/module',name).exists()
firmware=Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf');retained=Path('/var/lib/samurai/k378-boot-r1/firmware.elf')
assert sha(firmware)==sha(retained)==firmware_sha
directory=Path('/var/lib/samurai/k378-recovered');assert not directory.exists();directory.mkdir(mode=0o700)
guard=directory/'boot-id-private.txt';guard.write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes());firmware.unlink()
print(json.dumps(dict(stage=378,guard_path=str(guard),new_boot_verified=True,boot_readback_exact=True,logdump_readback_exact=True,
 old_worker_absent=True,old_transaction_preserved=True,temporary_firmware_removed_after_hash_check=True,
 original_elf_and_transaction_copy_preserved=True,icp_modules_absent=True,taint=0,firmware_handshake_passed=False)))
'''
q=host.raw_ssh('python3 -c '+shlex.quote('expected='+repr(expected)+'\nfirmware_sha='+repr(firmware_sha)+'\npackage='+repr(package)+'\nfat='+repr(fat)+'\n'+code),timeout=35)
(P/'recovered-boot-adoption-private.json').write_bytes(q.stdout);d=json.loads(q.stdout);d.pop('guard_path');(HERE/'recovery-cleanup-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
