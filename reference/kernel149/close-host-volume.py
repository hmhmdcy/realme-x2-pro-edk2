"""Release only the diagnostic loop mount backed by the recorded image."""
from pathlib import Path
import json,subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel149')
mount=Path('/home/cy122/pmos-samurai-kernel118')
image=Path('/mnt/e/edk2-samurai-out/kernel118/build-volume.ext4')
active=mount.is_mount();released=False
if active:
    source=subprocess.check_output(['findmnt','-n','-o','SOURCE','--mountpoint',str(mount)],text=True).strip()
    assert source.startswith('/dev/loop') and '\n' not in source
    backing=subprocess.check_output(['losetup','--noheadings','--output','BACK-FILE',source],text=True).strip()
    assert Path(backing).resolve()==image.resolve()
    subprocess.run(['umount',str(mount)],check=True)
    subprocess.run(['losetup','-d',source],check=True);released=True
assert not mount.is_mount() and image.is_file()
report=dict(diagnostic_mount_active_before=active,diagnostic_mount_closed=True,
            matching_loop_released=released,diagnostic_image_preserved=True)
(ref/'host-volume-closeout.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
