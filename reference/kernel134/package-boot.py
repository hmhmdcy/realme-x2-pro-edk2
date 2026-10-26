from pathlib import Path
import hashlib
import json
import shutil
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
build = json.loads((ref / 'kernel-build-validation.json').read_text())
audit = json.loads((out / 'canonical-firmware/firmware-validation.json').read_text())
restore = json.loads((out / 'original-firmware-restore-validation.json').read_text())
preflash = json.loads((ref / 'preflash-validation.json').read_text())
assert build['full_image_modules_dtb_build_pass'] and audit['only_embedded_dtb_changed']
assert audit['actual_device_boot_132_executables_preserved'] and restore['original_boot_byte_exact_restored']
assert preflash['preflash_audit_pass']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = out / 'boot-partition-before-private.img'
fat = out / 'logdump-before-private.img'
target = out / 'logdump-k134-usb-input.img'
boot = out / 'boot-partition-k134-usb-input.img'
assert not target.exists() and not boot.exists()
assert sha(before) == preflash['before_boot_sha256'] and before.stat().st_size == 100663296
assert sha(fat) == preflash['before_logdump_sha256'] and fat.stat().st_size == 67108864
raw = (out / 'canonical-firmware/boot-k134-usb-input.img').read_bytes()
assert len(raw) == audit['boot_bytes'] and hashlib.sha256(raw).hexdigest() == audit['boot_sha256']
baseline = before.read_bytes()
boot.write_bytes(raw + baseline[len(raw):])
assert boot.read_bytes()[len(raw):] == baseline[len(raw):] and boot.stat().st_size == len(baseline)
shutil.copyfile(fat, target)
for role, dest in [('Image', 'Image'), ('DTB', 'samurai.dtb')]:
    source = out / (role + '-k134-private')
    assert sha(source) == next(x['sha256'] for x in build['artifacts'] if x['role'] == role)
    subprocess.run(['mcopy', '-o', '-i', str(target), str(source), '::/' + dest], check=True)
    assert subprocess.check_output(['mcopy', '-i', str(target), '::/' + dest, '-']) == source.read_bytes()
assert set(subprocess.check_output(['mdir', '-b', '-s', '-i', str(target), '::'], text=True).splitlines()) == {'::/Image', '::/samurai.dtb'}
check = subprocess.run(['fsck.fat', '-n', str(target)], capture_output=True)
assert check.returncode == 0
(out / 'fat-check-private.txt').write_bytes(check.stdout + check.stderr)
report = dict(candidate=134, release=build['release'], boot_sha256=sha(boot), boot_bytes=boot.stat().st_size,
              logdump_sha256=sha(target), logdump_bytes=target.stat().st_size,
              boot_tail_after_payload_byte_preserved=True, only_embedded_dtb_changed=True,
              other_uefi_executable_bytes_unchanged=True, canonical_source_and_original_build_restored=True,
              fat_readback_exact=True, fat_readonly_check_pass=True, fat_only_image_and_dtb=True,
              fat_and_embedded_dtb_exactly_match_candidate=True, dtb_sha256=audit['dtb_sha256'],
              flash_partitions=['boot', 'logdump'], not_deployed=True, charging_control_accepted=False,
              userdata_bulk_flash_or_erase=False, goal_complete=False)
for folder in [ref, out]:
    (folder / 'boot-package-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
