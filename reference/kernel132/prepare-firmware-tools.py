from pathlib import Path
import shutil
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel132'
oldref = r / 'reference/kernel126'
out = Path('/mnt/e/edk2-samurai-out/kernel132')
for name in ['dtb-before', 'boot-before.img']:
    assert not (out / name).exists()
    shutil.copy2(out.parent / 'kernel115' / name, out / name)
text = (oldref / 'build-canonical-firmware.sh').read_text().replace('kernel126', 'kernel132').replace('DTB-k126-private', 'DTB-k132-private').replace('boot-k126-internal-tpg.img', 'boot-k132-charger.img')
(ref / 'build-canonical-firmware.sh').write_text(text)
text = (oldref / 'verify-original-restore.py').read_text().replace('kernel126', 'kernel132')
(ref / 'verify-original-restore.py').write_text(text)
text = (oldref / 'audit-firmware.py').read_text().replace("base_out=Path('/mnt/e/edk2-samurai-out/kernel126')", "base_out=Path('/mnt/e/edk2-samurai-out/kernel132')")
text = text.replace('boot-k126-internal-tpg.img', 'boot-k132-charger.img').replace('DTB-k126-private', 'DTB-k132-private')
text = text.replace("prior=base_out.parent/'kernel115/canonical-firmware'", "prior=base_out.parent/'kernel126/canonical-firmware'")
text = text.replace("prior/'boot-k115-ipa-zram.img'", "prior/'boot-k126-internal-tpg.img'")
text = text.replace('actual_device_boot_115_executables_preserved', 'actual_device_boot_129_executables_preserved')
(ref / 'audit-firmware.py').write_text(text)
print('K132_CANONICAL_UEFI_REBUILD_RESTORE_AND_ACTIVE129_MODULE_AUDIT_TOOLS_READY')
