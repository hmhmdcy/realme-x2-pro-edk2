from pathlib import Path
import hashlib
import json
import shutil
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel135'
out = Path('/mnt/e/edk2-samurai-out/kernel135')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
dt = json.loads((ref / 'dtb-validation.json').read_text())
audit = json.loads((out / 'canonical-firmware/firmware-validation.json').read_text())
restore = json.loads((out / 'original-firmware-restore-validation.json').read_text())
before = json.loads((ref / 'preflash-validation.json').read_text())
assert dt['exactly_one_property_added'] and audit['actual_device_boot_134_executables_preserved']
assert audit['only_embedded_dtb_changed'] and restore['original_boot_byte_exact_restored']
assert before['preflash_audit_pass']
boot = out / 'boot-partition-k135-mdss-reset.img'
fat = out / 'logdump-k135-mdss-reset.img'
assert not boot.exists() and not fat.exists()
baseline = (out / 'boot-partition-before-private.img').read_bytes()
raw = (out / 'canonical-firmware/boot-k135-mdss-reset.img').read_bytes()
assert sha(out / 'boot-partition-before-private.img') == before['before_boot_sha256']
assert len(baseline) == 100663296 and len(raw) == audit['boot_bytes']
assert hashlib.sha256(raw).hexdigest() == audit['boot_sha256']
boot.write_bytes(raw + baseline[len(raw):])
assert boot.read_bytes()[len(raw):] == baseline[len(raw):]
shutil.copyfile(out / 'logdump-before-private.img', fat)
assert fat.stat().st_size == 67108864 and sha(fat) == before['before_logdump_sha256']
for source, name in [(out.parent / 'kernel134/Image-k134-private', 'Image'), (out / 'DTB-k135-private', 'samurai.dtb')]:
    subprocess.run(['mcopy', '-o', '-i', str(fat), str(source), '::/' + name], check=True)
    assert subprocess.check_output(['mcopy', '-i', str(fat), '::/' + name, '-']) == source.read_bytes()
assert set(subprocess.check_output(['mdir', '-b', '-s', '-i', str(fat), '::'], text=True).splitlines()) == {'::/Image', '::/samurai.dtb'}
p = subprocess.run(['fsck.fat', '-n', str(fat)], capture_output=True)
(out / 'fat-check-private.log').write_bytes(p.stdout + p.stderr)
assert p.returncode == 0
report = dict(candidate=135, software_generation=134, release=dt['release'],
    boot_sha256=sha(boot), boot_bytes=boot.stat().st_size,
    logdump_sha256=sha(fat), logdump_bytes=fat.stat().st_size,
    dtb_sha256=sha(out / 'DTB-k135-private'), only_embedded_dtb_changed=True,
    other_uefi_executable_bytes_unchanged=True, original_canonical_baseline_restored=True,
    fat_readback_exact=True, fat_readonly_check_pass=True, fat_only_image_and_dtb=True,
    fat_and_embedded_dtb_exactly_match_candidate=True, boot_tail_after_payload_byte_preserved=True,
    flash_partitions=['boot', 'logdump'], kernel_image_modules_rootfs_reused_from134=True,
    userdata_bulk_flash_or_erase=False, runtime_validation_pending=True, goal_complete=False)
for folder in [ref, out]:
    (folder / 'boot-package-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
