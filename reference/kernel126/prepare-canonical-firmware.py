from pathlib import Path
import shutil
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126');old=out.parent/'kernel115'
for name in ['dtb-before','boot-before.img']:
 assert not (out/name).exists();shutil.copy2(old/name,out/name)
s=(r/'reference/kernel115/build-canonical-firmware.sh').read_text().replace('kernel115','kernel126').replace('dtb-ipa-zram','DTB-k126-private').replace('boot-k115-ipa-zram.img','boot-k126-internal-tpg.img')
(ref/'build-canonical-firmware.sh').write_text(s)
s=(r/'reference/kernel115/verify-original-restore.py').read_text().replace('kernel115','kernel126');(ref/'verify-original-restore.py').write_text(s)
s=(r/'reference/kernel115/audit-firmware.py').read_text().replace('kernel115','kernel126').replace('boot-k115-ipa-zram.img','boot-k126-internal-tpg.img').replace('dtb-ipa-zram','DTB-k126-private').replace("base_out/'boot-partition-before.img'","base_out/'boot-partition-before-private.img'")
s=s.replace("prior=base_out.parent/'kernel113/canonical-firmware'","prior=base_out.parent/'kernel115/canonical-firmware'").replace("prior/'boot-k113-sensors.img'","prior/'boot-k115-ipa-zram.img'").replace('actual_device_boot_113_executables_preserved','actual_device_boot_115_executables_preserved')
(ref/'audit-firmware.py').write_text(s)
print('K126_CANONICAL_FIRMWARE_TOOLS_READY_BASELINE_RESTORE_GUARDED')
