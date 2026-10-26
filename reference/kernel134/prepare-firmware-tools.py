from pathlib import Path
import shutil
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
prior = r / 'reference/kernel132'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
for name in ['dtb-before', 'boot-before.img']:
    assert not (out / name).exists()
    shutil.copy2(out.parent / 'kernel115' / name, out / name)
for name in ['build-canonical-firmware.sh', 'verify-original-restore.py', 'audit-firmware.py']:
    text = (prior / name).read_text()
    text = text.replace('kernel132', 'kernel134').replace('k132', 'k134')
    text = text.replace('boot-k134-charger.img', 'boot-k134-usb-input.img')
    if name == 'audit-firmware.py':
        text = text.replace("prior=base_out.parent/'kernel126/canonical-firmware'", "prior=base_out.parent/'kernel132/canonical-firmware'")
        text = text.replace("prior/'boot-k126-internal-tpg.img'", "prior/'boot-k132-charger.img'")
        text = text.replace('actual_device_boot_129_executables_preserved', 'actual_device_boot_132_executables_preserved')
    assert not (ref / name).exists()
    (ref / name).write_text(text)
print('K134_CANONICAL_FIRMWARE_DTB_ONLY_REBUILD_AND_BASELINE_RESTORE_TOOLS_READY', flush=True)
