"""Build a diagnostic initramfs candidate without mounting userdata."""
from pathlib import Path
import hashlib, json, shutil, subprocess
base=Path('/home/cy122/pmos-samurai-kernel109')
stage=Path('/home/cy122/pmos-samurai-kernel110')
out=Path('/mnt/e/edk2-samurai-out/kernel110')
assert not stage.exists() and not out.exists()
stage.mkdir(); out.mkdir()
shutil.copytree(base/'kernel', stage/'kernel', symlinks=True)
shutil.copytree(base/'initramfs', stage/'initramfs', symlinks=True)
init=stage/'initramfs/init'
text=init.read_text()
old='. /usr/sbin/samurai-rootfs || echo "[rootfs] retaining diagnostic initramfs"'
assert text.count(old)==1
text=text.replace(old,'echo "[rescue110] retaining diagnostic initramfs; userdata not mounted"')
begin=text.index('# Wi-Fi firmware/NV copies and services remain in RAM;')
end=text.index('echo\necho "=============================================="',begin)
text=text[:begin]+'# Rescue starts no radio services; userdata and NV are untouched.\n\n'+text[end:]
init.write_text(text)
subprocess.run([str(stage/'kernel/scripts/config'),'--file',str(stage/'kernel/.config'),
    '--set-str','INITRAMFS_SOURCE',str(stage/'initramfs')],check=True)
summary=dict(stage=110,role='diagnostic-rescue',base_kernel_build=109,
    userdata_handoff_disabled=True,automatic_wifi_and_bluetooth_disabled=True,
    flash_candidate_only=True,partitions_flashed=[],dtb_change=False)
(out/'rescue-preparation.json').write_text(json.dumps(summary,indent=2)+'\n')
print('RESCUE110_STAGE_PREPARED_USERDATA_NOT_MOUNTED')
