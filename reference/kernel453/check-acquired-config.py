"""Validate the privately retained, read-only r6 stock AF configuration sources."""
from pathlib import Path
import hashlib,json,struct
HERE=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel453/af-config-source')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
lib=private/'libhwconfigurationutil-r6.so';config=private/'CameraHWConfiguration-r6.config'
source=json.loads((private/'source-private.json').read_text())
settings=json.loads((private/'settings-source-private.json').read_text())
metadata=json.loads((private.parent/'af-vendor-metadata-private.json').read_text())
extra=json.loads((private.parents[1]/'kernel457/trace-extra-private.json').read_text())
assert source['hal_matched'] and source['hal_sha256']=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
assert metadata['mountinfo']==[] and 'TYPE=ext4' in metadata['blkid'].splitlines()
assert extra['odm']['mountinfo']==[] and 'TYPE=ext4' in extra['odm']['blkid'].splitlines()
assert source['partition']=='odm' and source['relative_path']=='lib64/libhwconfigurationutil.so'
assert source['size']==lib.stat().st_size==109784
assert source['sha256']==settings['library_sha256']==sha(lib)=='9b317c9e3154929964aef1cca37b79fda00f7201c119d5f4cf9656f5c1917548'
raw=lib.read_bytes();assert raw[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',raw,18)[0]==183
assert b'/odm/etc/camera/CameraHWConfiguration.config\x00' in raw
assert settings['path']=='/odm/etc/camera/CameraHWConfiguration.config'
assert settings['size']==config.stat().st_size==1121
assert settings['sha256']==sha(config)=='4d73f1ad3216bc9338e9113cd23d2b1ea68403cee3ab0b3c9fe718aa3f4e37f0'
assert b'[OemCamActuatorSettingMap]' in config.read_bytes()
for receipt in [source,settings]:
 assert receipt['readonly_debugfs'] and not receipt['phone_files_written'] and receipt['charging_unchanged']
assert source['mounted_before'] is False and source['mounted_after'] is False
report=dict(stage=453,hal_match_passed=True,source_partition='odm',library_size=109784,
 library_sha256=sha(lib),configuration_size=1121,configuration_sha256=sha(config),
 library_elf64_aarch64=True,configuration_path_from_actual_library=True,
 target_files_regular=True,readonly_debugfs=True,phone_mounts_created=False,phone_files_written=False,
 oem_elf_executed_on_phone=False,existing_eeprom_reused=True,
 loader_and_override_semantics_covered_by_this_integrity_checker=False,individual_af_deployable=False,
 source_receipt_sha256=sha(private/'source-private.json'),settings_receipt_sha256=sha(private/'settings-source-private.json'),
 passed=True)
(HERE/'acquired-config-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
