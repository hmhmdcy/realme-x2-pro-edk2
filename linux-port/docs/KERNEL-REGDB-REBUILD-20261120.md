# Rebuilding the 7.3.1 kernel with regulatory.db embedded (2026-11-20)

Purpose: `cfg80211` requests `regulatory.db` at ~0.50 s, before the F2FS
rootfs (which holds `/lib/firmware`) is mounted at ~1.77 s.  The only place
that can satisfy that request is the kernel-embedded initramfs, so the whole
kernel has to be rebuilt and its `Image` flashed into the `logdump` FAT.

This is the reproducible recipe, including the two traps that made the first
attempt unbootable-by-size.

## Prerequisites

| Item | Value |
| --- | --- |
| source | `linux-7.3.1.tar.gz` (not `-rc6`; `kernel.release` must match) |
| patches | `linux-port/patches/v7.3.1/` (17 patches, 4 skipped as superseded) |
| config | the *running* kernel's `/proc/config.gz`, not a stale snapshot |
| initramfs | original board tree **plus** `regulatory.db` / `.p7s` |
| cross tools | `aarch64-linux-gnu-gcc`, `ld.lld` (see below), make/bison/flex/bc |

`ld.lld` is required.  Ubuntu 24.04 ships binutils 2.42, which does not
implement `-z pack-relative-relocs`; Kconfig's `TOOLS_SUPPORT_RELR` probe
gets "ignored" back and `olddefconfig` silently clears `CONFIG_RELR`.
Without RELR the `.rela.dyn` section stays at ~7.7 MB and the Arm64
`Image` no longer fits the 64 MiB `logdump` partition.

## Steps

```sh
# 1. tree
linux-port/scripts/_wsl-samurai/prepare-kernel-tree.sh --force

# 2. running config + regdb initramfs
cp <running-config> /home/cy122/x2pro-linux/linux/.config
python3 linux-port/scripts/_wsl-samurai/add-regdb-to-initramfs.py \
    <base-initramfs.gz> /root/regdb-device/regulatory.db \
    /root/regdb-device/regulatory.db.p7s \
    /home/cy122/x2pro-linux/initramfs-regdb.cpio.gz

# 3. point at the .cpio.GZ, never the plain .cpio
./scripts/config --set-str INITRAMFS_SOURCE /home/cy122/x2pro-linux/initramfs-regdb.cpio.gz
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig

# 4. build, appending the flavour to CONFIG_LOCALVERSION
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
     LOCALVERSION=-usbwake-otg LD=ld.lld Image modules
```

`CONFIG_LOCALVERSION="-rmx1931-samurai-v731"` already lives in the config.
Passing `LOCALVERSION=-usbwake-otg` on the command line **appends**, giving
`7.3.1-rmx1931-samurai-v731-usbwake-otg` — the release all 772 installed
modules were built against.  Do not set `CONFIG_LOCALVERSION` to the flavour
alone: that drops the board part and every module fails vermagic.

## Verification before flashing

```sh
cat include/config/kernel.release                  # must match uname -r
python3 check-image-regdb.py arch/arm64/boot/Image # regdb + 398 members
python3 - <<'PY'                                   # must be < 64 MiB
import struct
d = open("arch/arm64/boot/Image", "rb").read(64)
print(hex(struct.unpack("<Q", d[16:24])[0]))
PY
```

Measured 2026-11-20:

```text
Image            58,673,664 bytes   (image_size 0x3980000)
initramfs gz     15,068,393 bytes   398 members
.rela.dyn                0x60
.relr.dyn           0x214b8
kernel.release   7.3.1-rmx1931-samurai-v731-usbwake-otg
```

## Flashing into the 64 MiB `logdump` FAT

The partition is FAT32 in a 4 Knative-sector slot, so the kernel cannot mount
it and `mcopy`-ing a single file is not an option on-device.  Instead modify
the partition image locally and write it back whole:

```sh
# take a byte-exact copy of the live partition (device, as root)
dd if=/dev/sde32 of=/tmp/logdump.img bs=1M

# locally (mtools installed via apt)
MTOOLS_SKIP_CHECK=1 mcopy -o -i logdump.img arch/arm64/boot/Image ::/Image
MTOOLS_SKIP_CHECK=1 mdir -i logdump.img ::          # check free space
fsck.fat -n logdump.img

# write back and prove the read-back matches
dd if=logdump.img of=/dev/sde32 bs=1M conv=fsync
sync && sha256sum /dev/sde32 logdump.img
```

Only the partition **contents** change.  GRUB locates the volume with
`search_fs_file /Image`, so the label and the GUID stay untouched and UEFI
needs no rebuild.  Keep the pre-change partition image on the host
(`1254361…`, 64 MiB) as the rollback payload.

## Result

On the first boot with the new Image:

```text
$ iw phy phy0 reg get
phy#0
country US: DFS-FCC          # was: country 99 / PASSIVE-SCAN
```

`regdb` is now loaded; 5 GHz channels carry real transmit rules.  See
`WIFI-BAND-LATENCY-20261120.md` §10 for the measurements and for the two
`dsi0_phy_pll_out_dsiclk` WARNs that this build introduced (`taint=512`).
