#!/bin/bash
# Configure and build the kernel with the regdb-carrying initramfs.
# Uses the v7.3.1 board config and the treestate produced by
# prepare-kernel-tree.sh.
set -eu
LK=/home/cy122/x2pro-linux/linux
CFG="/mnt/e/RealmeX2Pro edk2/linux-port/configs/v7.3.1/samurai.config"
BASE_GZ=/mnt/e/edk2-samurai-out/kernel456/candidate-embedded-initramfs-private.gz
REGDB=/root/regdb-device
IRFS=/home/cy122/x2pro-linux/initramfs-regdb.cpio
IRFS_GZ=$IRFS.gz
LOG=/home/cy122/x2pro-linux
# The deployed Image is the -usbwake-otg flavour.  make's LOCALVERSION is
# *appended* to CONFIG_LOCALVERSION, so passing it here yields
#   7.3.1-rmx1931-samurai-v731-usbwake-otg
# which is exactly the release the 772 installed modules use.  Do NOT set
# CONFIG_LOCALVERSION to just "-usbwake-otg": that would drop the
# "-rmx1931-samurai-v731" part and every module would fail vermagic.
FLAVOR=-usbwake-otg
# The running Image was linked with binutils 2.46, so CONFIG_RELR (which
# packs .rela.dyn into the much smaller .relr.dyn) is on.  Ubuntu 24.04's
# binutils 2.42 cannot do that: TOOLS_SUPPORT_RELR probes `ld -z
# pack-relative-relocs`, gets "ignored", and olddefconfig silently turns
# CONFIG_RELR off.  That alone leaves a ~7.7 MB .rela.dyn in the Image and
# pushes it past the 64 MiB `logdump` FAT, so link with ld.lld instead.
LD_OVERRIDE=ld.lld

cd "$LK"
echo '=== config ==='
[ -f "$BASE_GZ" ] || { echo "base initramfs missing"; exit 1; }
[ -f "$REGDB/regulatory.db" ] || { echo "regdb missing"; exit 1; }

# One *uncompressed* .cpio carrying the original tree plus regdb.  Passing a
# .gz or extra file list here is fragile (gen_initramfs.sh treats those as
# gen_init_cpio text), so keep a single, self-contained archive.
python3 "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/_wsl-samurai/add-regdb-to-initramfs.py" \
	"$BASE_GZ" "$REGDB/regulatory.db" "$REGDB/regulatory.db.p7s" \
	"$IRFS_GZ"
ls -l "$IRFS_GZ"

cp -f "$CFG" .config
# scripts/config must run before olddefconfig; olddefconfig silently blanks
# INITRAMFS_SOURCE when the path it sees cannot be resolved.
#
# Point at the .cpio.gz, not the raw .cpio.  usr/Makefile treats a single
# ".cpio.*" source as already compressed ("compress-y := copy"), so the
# gzip stream is embedded as-is (~15 MB).  A bare ".cpio" is embedded
# **uncompressed** (~30 MB), which pushes the Arm64 Image past the 64 MiB
# `logdump` FAT partition and makes it unflashable.
./scripts/config --set-str INITRAMFS_SOURCE "$IRFS_GZ"
./scripts/config --enable BLK_DEV_INITRD
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig >/dev/null

if ! grep -q "^CONFIG_INITRAMFS_SOURCE=\"$IRFS_GZ\"\$" .config; then
	echo 'INITRAMFS_SOURCE was rejected; aborting to avoid a kernel without regdb'
	grep -n INITRAMFS .config
	exit 1
fi
echo '  base tree + regdb are embedded'

echo '=== Image must fit the 64 MiB logdump FAT partition ==='
echo '  (GRUB loads /Image from that partition; there is no room for a'
echo '   larger file, so a size regression here is a deployment blocker)'

echo '=== verify the important settings survived ==='
grep -E '^CONFIG_(INITRAMFS_SOURCE|LOCALVERSION|EFI_STUB|CMDLINE=)' .config

# olddefconfig answers every symbol it does not find a value for, and a
# config that lost a dependency silently drops the dependent.  The camera
# media graph depends on the v4l2 flash class: without it leds-qcom-flash
# compiles the stub qcom_flash_v4l2_init(), never registers the flash
# sub-device, and every sensor keeps links=0 because the async connection
# built from "flash-leds" can never be matched.  Assert the whole chain.
for sym in V4L2_FLASH_LED_CLASS LEDS_CLASS_FLASH LEDS_QCOM_FLASH MFD_SPMI_PMIC ARCH_QCOM; do
	case "$(grep -E "^CONFIG_${sym}=" .config)" in
	CONFIG_"$sym"=m|CONFIG_"$sym"=y) ;;
	*)
		echo "camera flash chain broken: CONFIG_${sym} is not enabled" >&2
		grep -E "^#? ?CONFIG_${sym}" .config >&2 || true
		exit 1
		;;
	esac
done
echo '  camera flash chain intact (V4L2_FLASH_LED_CLASS -> LEDS_QCOM_FLASH)'

echo "expected release: $(cat include/config/kernel.release 2>/dev/null || echo unknown)"

echo '=== build (this can take a while) ==='
# A previously built initramfs_data.o is cached in usr/ and the link step
# happily reuses it, which silently ships the OLD initramfs (no regdb).
# Remove it plus the incremental deps, then force the stub to regenerate.
rm -f usr/initramfs_data.o usr/initramfs_data.cpio \
	usr/.initramfs_data.cpio.d usr/initramfs_inc_data
touch usr/initramfs_data.S
make -j"$(nproc)" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
	LD="$LD_OVERRIDE" Image \
	> "$LOG/build-regdb.log" 2>&1 || {
	tail -30 "$LOG/build-regdb.log"; exit 1; }
ls -l arch/arm64/boot/Image
sha256sum arch/arm64/boot/Image

echo '=== the Image must still fit the 64 MiB logdump FAT ==='
python3 - <<'PY'
import struct
img = "/home/cy122/x2pro-linux/linux/arch/arm64/boot/Image"
d = open(img, "rb").read(64)
size = struct.unpack("<Q", d[16:24])[0]
limit = 64 * 1024 * 1024
print(f"  Image {size} bytes, limit {limit} bytes")
raise SystemExit(0 if size < limit else 1)
PY

echo '=== prove regdb is inside the Image ==='
python3 "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/_wsl-samurai/check-image-regdb.py" \
	arch/arm64/boot/Image
