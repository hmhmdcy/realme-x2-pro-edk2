"""Move an inherited hardcoded identity into the existing private artifact store."""
from pathlib import Path
import re

root = Path('/mnt/e/RealmeX2Pro edk2')
init = Path('/home/cy122/pmos-samurai-kernel112/initramfs/usr/sbin/samurai-rootfs').read_text()
uuid = re.search(r'^\s*expected_fs_uuid=([^\s]+)', init, re.M).group(1)
private = Path('/mnt/e/edk2-samurai-out/kernel109/rootfs-uuid-private.txt')
if private.exists(): assert private.read_text().strip() == uuid
else: private.write_text(uuid + '\n'); private.chmod(0o600)
path = root / 'reference/kernel109/pack-rootfs.sh'
text = path.read_text()
if uuid in text:
    assert text.count(uuid) == 1
    text = text.replace('root="$stage/rootfs"', '''root="$stage/rootfs"
rootfs_uuid=$(cat "$out/rootfs-uuid-private.txt")
[[ "$rootfs_uuid" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]''')
    text = text.replace(uuid, '"$rootfs_uuid"')
    path.write_text(text)
partuuid = re.search(r'^\s*expected_partuuid=([^\s]+)', init, re.M).group(1)
private_part = private.with_name('userdata-partuuid-private.txt')
if private_part.exists(): assert private_part.read_text().strip() == partuuid
else: private_part.write_text(partuuid + '\n'); private_part.chmod(0o600)
path = root / 'reference/kernel109/prepare-stage.py'
text = path.read_text()
if partuuid in text:
    assert text.count(partuuid) == 1
    text = text.replace(repr(partuuid), "(out/'userdata-partuuid-private.txt').read_text().strip()")
    path.write_text(text)
print('Inherited rootfs identity externalized; pack behavior unchanged')
