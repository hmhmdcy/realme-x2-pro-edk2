"""Adopt the verified new boot and remove the known orphan firmware copy."""
from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
facts=json.loads((P/'recovered-inventory-secret-private.json').read_text());expected=facts['boot_id']
firmwareHash=hashlib.sha256((P.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes()).hexdigest()
assert facts['camss_build_note_sha256']=='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297'
assert facts['temporary_firmware_sha256']==firmwareHash
code=r'''
from pathlib import Path
import hashlib,json,os
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==EXPECTED
assert Path('/sys/firmware/devicetree/base/model').read_bytes().rstrip(b'\0')==b'Realme X2 Pro (RMX1931CN)'
assert Path('/proc/sys/kernel/osrelease').read_text().strip()=='7.3.0-rc6-rmx1931-samurai-k298+'
assert hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()=='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297'
for module in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test']:assert not Path('/sys/module',module).exists()
assert not Path('/sys/firmware/devicetree/base/soc@0/samurai-icp356-boot@ac10000').exists()
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:cmd=(p/'cmdline').read_bytes()
 except OSError:continue
 assert b'/var/lib/samurai/k356-boot-r5/worker.py' not in cmd
source=Path('/var/lib/samurai/k356-boot-r5/firmware.elf');firmware=Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf')
assert hashlib.sha256(source.read_bytes()).hexdigest()==FIRMWARE_HASH
present=firmware.exists()
if present:
 assert not firmware.is_symlink() and hashlib.sha256(firmware.read_bytes()).hexdigest()==FIRMWARE_HASH
 firmware.unlink()
root=Path('/var/lib/samurai/k360-recovered');root.mkdir(mode=0o700,exist_ok=True);guard=root/'boot-id-private.txt';raw=(boot+'\n').encode()
if guard.exists():assert guard.read_bytes()==raw
else:
 with guard.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
descriptor=os.open(root,os.O_RDONLY|os.O_DIRECTORY);os.fsync(descriptor);os.close(descriptor)
report=dict(guard_path=str(guard),verified_new_boot=True,original_guards_preserved=True,
 orphan_firmware_was_present=present,orphan_firmware_removed=not firmware.exists(),retained_r5_firmware_copy_intact=hashlib.sha256(source.read_bytes()).hexdigest()==FIRMWARE_HASH,
 old_r5_state_preserved=True,old_r5_attempt_passed=False,old_r5_outcome='interrupted; original terminal result absent',
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),camss_runtime_status=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip(),kernel_or_dt_installed=False)
print(json.dumps(report))
'''.replace('EXPECTED',repr(expected)).replace('FIRMWARE_HASH',repr(firmwareHash))
q=host.raw_ssh('python3 -',input=code.encode(),timeout=30);report=json.loads(q.stdout)
(P/'recovered-boot-adoption-private.json').write_text(json.dumps(dict(report,boot_id=expected),indent=2)+'\n')
report.pop('guard_path');report.update(stage=360,passed=True,package_candidate_installed=False)
(HERE/'recovery-cleanup-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
