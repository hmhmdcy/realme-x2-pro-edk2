from pathlib import Path
import base64,hashlib,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel248');spec=importlib.util.spec_from_file_location('rescue',R/'rescue-host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host);marker=base64.b64decode(json.loads((P/'root-marker-before-rescue-private.json').read_text())['marker_base64']);digest=hashlib.sha256(marker).hexdigest();archive=json.loads((R/'rescue-tool-build-validation.json').read_text())['archive_sha256']
script=r'''
set -eu
cmp /proc/sys/kernel/random/boot_id /run/k248-rescue-boot-id-private.txt
test ! -e /run/rescue-tools
mkdir -p /mnt/linux
mount -t f2fs -o rw,noatime /dev/sda16 /mnt/linux
test ! -e /mnt/linux/etc/samurai-rootfs-release
test -f /mnt/linux/etc/samurai-rootfs-release.k248-before-rescue
test "$(sha256sum /mnt/linux/etc/samurai-rootfs-release.k248-before-rescue | cut -d' ' -f1)" = 'MARKER'
mv /mnt/linux/etc/samurai-rootfs-release.k248-before-rescue /mnt/linux/etc/samurai-rootfs-release
test "$(sha256sum /mnt/linux/var/lib/samurai/k248-tools/rescue-tools-private.tar.gz | cut -d' ' -f1)" = 'ARCHIVE'
mkdir /run/rescue-tools
tar -xzf /mnt/linux/var/lib/samurai/k248-tools/rescue-tools-private.tar.gz -C /run/rescue-tools
sync
umount /mnt/linux
mkdir -p /run/rescue-tools/dev /run/rescue-tools/proc /run/rescue-tools/sys /run/rescue-tools/run
mount --bind /dev /run/rescue-tools/dev
mount --bind /proc /run/rescue-tools/proc
mount --bind /sys /run/rescue-tools/sys
mount --bind /run /run/rescue-tools/run
/bin/busybox blockdev --setro /dev/sda16
test "$(cat /sys/class/block/sda16/ro)" = 1
chroot /run/rescue-tools /usr/bin/python3 --version
chroot /run/rescue-tools /usr/sbin/partclone.f2fs --version
printf 'RAM_TOOLS_READY_MARKER_RESTORED_USERDATA_RO
'
'''.replace('MARKER',digest).replace('ARCHIVE',archive)
x=host.ssh('sh -s',input=script.encode(),timeout=50);(P/'ram-backup-setup-private.log').write_bytes(x.stdout+x.stderr);assert b'RAM_TOOLS_READY_' in x.stdout
report=dict(stage=248,linux_root_marker_restored_before_backup=True,rescue_tools_archive_sha256_verified=True,tools_running_entirely_in_ram=True,userdata_unmounted=True,userdata_block_device_read_only=True,no_android_flash_or_userdata_format=True);(R/'ram-backup-setup-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
