from pathlib import Path
import hashlib, shutil

ref = Path('/mnt/e/RealmeX2Pro edk2/reference')
out = Path('/mnt/e/edk2-samurai-out/kernel113')
old = out.parent / 'kernel111'
for name, source in [('dtb-before', old / 'dtb-before'),
                     ('boot-before.img', old / 'canonical-firmware/boot-before.img')]:
    assert not (out / name).exists()
    shutil.copyfile(source, out / name)
for name in ['build-canonical-firmware.sh', 'audit-firmware.py', 'verify-original-restore.py']:
    text = (ref / 'kernel111' / name).read_text()
    text = text.replace('kernel111', 'kernel113').replace('k111', 'k113')
    text = text.replace('dtb-sensors', 'dtb-sensor-power')
    text = text.replace('active_boot_backup_matches', 'canonical_baseline_boot_matches_109')
    assert not (ref / 'kernel113' / name).exists()
    (ref / 'kernel113' / name).write_text(text)
print('Canonical DTB-only firmware tools prepared; original source restoration required')
