#!/bin/bash
# Rebuild the delivery image with this round's verified fixes embedded:
#   * board package public key + signed local board repository
#   * corrected samurai-gnss-assist unit (no ExecStartPre) + its log dir
#   * nftables.service not enabled (the kernel has no NF_TABLES at all)
#
# samurai-ssc is replaced by the repository variant because the installed
# artifact is the pre-fast-path build.  The repository version was boot
# tested (linux-port/ssc/README.md: readiness at 03:49:13/19/21 s,
# default runlevel 42 s -> 26 s), and its firmware directory
# qcom/sm8150/realme/samurai-a11-r187 is byte-identical to the
# samurai-slpi-a11 directory the installed build uses (25 files, same
# hashes), so the path change selects the same firmware.
#
# Runs the whole pipeline in one process because WSL drops loop mounts
# between bash invocations.
set -eu

# apk --root can install aarch64 APKs from this x86_64 host without any
# binfmt/QEMU registration: only file extraction and DB writes happen here,
# and --scripts=no skips the only part that would need to execute target
# code.  (chroot + /sbin/apk fails with "Exec format error" without binfmt.)
APK=/root/apkstatic/sbin/apk.static

SRC=/mnt/e/edk2-samurai-out/standard-arm64-v731/rootfs-stable-20261119-apps2/samurai-stable-f2fs-partuuid.simg
OUTDIR=/mnt/e/edk2-samurai-out/standard-arm64-v731/rootfs-stable-20261119-clean
WORK=/root/repack

REPO_SRC=/root/boardrepo-r17

# The six official recommends are signed by the Alpine release key, not by
# the postmarketOS build key, so the image needs that public key as well.
ALPINE_KEY=/root/akeys/alpine-devel@lists.alpinelinux.org-616ae350.rsa.pub

mkdir -p "$OUTDIR"
rm -rf "$WORK"
mkdir -p "$WORK/root"

echo '=== 1. expand delivery image ==='
simg2img "$SRC" "$WORK/full.img"

echo '=== 2. insert board repository + key + preset + SSC ==='
losetup -D 2>/dev/null || true
L=$(losetup -f --show "$WORK/full.img")
mount -t f2fs "$L" "$WORK/root"

cleanup() {
    umount "$WORK/root" 2>/dev/null || true
    losetup -D 2>/dev/null || true
}
trap cleanup EXIT

install -d -m 0755 "$WORK/root/usr/share/samurai/packages/aarch64"
cp "$REPO_SRC"/*.apk "$REPO_SRC"/APKINDEX.tar.gz \
    "$WORK/root/usr/share/samurai/packages/aarch64/"

install -d -m 0755 "$WORK/root/etc/apk/keys"
cp /root/installed_keys/pmos@local-6aeaf066.rsa.pub \
    "$WORK/root/etc/apk/keys/"
# Must land before any `apk --root add`, or every Alpine-signed package is
# rejected as UNTRUSTED and nothing gets installed.
if [ -f "$ALPINE_KEY" ]; then
    install -Dm644 "$ALPINE_KEY" \
        "$WORK/root/etc/apk/keys/$(basename "$ALPINE_KEY")"
else
    echo '  WARNING: Alpine release key missing; recommends cannot be installed'
fi

install -d -m 0755 "$WORK/root/etc/apk/repositories.d"
printf '%s\n' /usr/share/samurai/packages \
    > "$WORK/root/etc/apk/repositories.d/60-samurai-board.list"

install -d -m 0700 -o root -g root "$WORK/root/var/lib/samurai/gnss-assist"
cp /mnt/e/RealmeX2Pro\ edk2/linux-port/packages/samurai-systemd/samurai-gnss-assist.service \
    "$WORK/root/usr/lib/systemd/system/samurai-gnss-assist.service"
cp /mnt/e/RealmeX2Pro\ edk2/linux-port/packages/samurai-systemd/50-samurai.preset \
    "$WORK/root/usr/lib/systemd/system-preset/50-samurai.preset"

# Alpine's 90-base.preset enables nftables.service and the image build then
# materialised a sysinit.target.wants symlink for it.  This kernel config
# has "# CONFIG_NF_TABLES is not set", so nft aborts with
# "Unable to initialize Netlink socket: Protocol not supported" on every
# boot.  Remove the enabling link (the preset also disables it, so a later
# `systemctl preset-all` will not bring it back).
rm -f "$WORK/root/etc/systemd/system/sysinit.target.wants/nftables.service"

install -m 0755 /mnt/e/RealmeX2Pro\ edk2/linux-port/packages/samurai-ssc/samurai-ssc.py \
    "$WORK/root/usr/sbin/samurai-ssc"

# Three packages from the official Plasma Mobile recommend list were never
# installed by the earlier build: ttyescape, vvmplayer and plasma-mobile-sounds.
# The first two are required by samurai-apps (packages/samurai-apps/APKBUILD).
# Only the copies whose signatures verify against the image's own key set are
# embedded; ttyescape is signed by pmos@local-6a19ae2a, a key the image does
# not carry, so it is left out rather than starting an
# "install but cannot update" package.
EXTRA=/root/recommends-repo
if [ -d "$EXTRA" ]; then
    echo '=== 2b. install the official recommends that were missing ==='
    # Two official _pmb_recommends were never installed by the earlier
    # build (verified against pmaports v26.06): plasma-mobile-sounds and
    # ttyescape.  vvmplayer/vvmd/gst-* come in as their dependencies.
    # ttyescape is board-signed because the official artifact's key
    # (pmos@local-6a19ae2a) is not published in any repository.
    for apk in gst-libav gst-plugins-ugly hkdm plasma-mobile-sounds \
        ttyescape vvmd vvmplayer hkdm-systemd vvmd-systemd; do
        p=$(ls "$EXTRA"/$apk-*.apk 2>/dev/null | head -1)
        [ -n "$p" ] || { echo "  skip $apk (not fetched)"; continue; }
        install -Dm644 "$p" "$WORK/root/tmp/$(basename "$p")"
    done
    # apk --root installs the target packages from the host: no binfmt and
    # no chroot is required, and --scripts=no avoids running target code.
    # --allow-untrusted is never used, so a package whose signer is not in
    # the image key set stays out instead of creating an unupdatable package.
    # Install each APK by path: it needs no index lookup and therefore
    # cannot pick a same-version entry from a remote repository.
    for f in "$WORK/root"/tmp/*.apk; do
        "$APK" --root "$WORK/root" --arch aarch64 --scripts=no \
            --keys-dir "$WORK/root/etc/apk/keys" --no-network \
            add "$f" 2>&1 | tail -1
    done &&
        echo '  installed recommends' || echo '  recommend install FAILED'
    rm -f "$WORK/root"/tmp/*.apk
fi

echo '=== 3. checks ==='
"$APK" --root "$WORK/root" version >/dev/null 2>&1 || true

# Board-wide KDE default: never auto-suspend.  s2idle on this kernel drops
# both the USB/NCM link and the Wi-Fi link, i.e. the only remote access
# paths, so an unattended suspend makes the device unreachable.  This is the
# same value the KDE Energy Saving page writes for "Never"; it is placed in
# /etc/xdg so a user's own ~/.config/powerdevilrc still wins.  The retired
# debug AutoSuspendAction=0 override is intentionally NOT used.
#
# Do NOT copy the file directly: the first delivery image did exactly that,
# which left /etc/xdg/powerdevilrc with no owner in lib/apk/db/installed and
# made `apk upgrade` unable to replace it.  Install the real package instead
# so apk records the owner (verify with `apk info -W /etc/xdg/powerdevilrc`).
if [ -f "$REPO_SRC/samurai-desktop-4-r17.apk" ]; then
    "$APK" --root "$WORK/root" --arch aarch64 --scripts=no \
        --keys-dir "$WORK/root/etc/apk/keys" \
        add "$REPO_SRC/samurai-desktop-4-r17.apk" ||
        echo '  WARNING: samurai-desktop 4-r17 install failed'
fi

echo '=== 4. unmount, fsck, repack ==='
sync
umount "$WORK/root"
losetup -D 2>/dev/null || true
trap - EXIT

fsck.f2fs -f "$WORK/full.img" | tail -3

img2simg "$WORK/full.img" "$WORK/packed.simg"

echo '=== 5. verify packed image ==='
simg2img "$WORK/packed.simg" "$WORK/verify.img"
fixes=$(fsck.f2fs -f "$WORK/verify.img" 2>&1 | grep -Fc '[FIX]' || true)
echo "fix_count=$fixes"
losetup -D 2>/dev/null || true
L2=$(losetup -f --show -r "$WORK/verify.img")
mkdir -p "$WORK/vfy"
mount -t f2fs -o ro,norecovery "$L2" "$WORK/vfy"
grep -E '^PRETTY_NAME|^VERSION_ID' "$WORK/vfy/etc/os-release"
echo "packages: $(grep -c '^P:' "$WORK/vfy/lib/apk/db/installed")"
ls "$WORK/vfy/usr/share/samurai/packages/aarch64" | wc -l
echo '=== powerdevil default (must disable auto-suspend on all three profiles) ==='
[ -f "$WORK/vfy/etc/xdg/powerdevilrc" ] &&
    echo '  present: /etc/xdg/powerdevilrc' ||
    echo '  MISSING: /etc/xdg/powerdevilrc'
grep -c '^AutoSuspendIdleTimeoutSec=0$' "$WORK/vfy/etc/xdg/powerdevilrc" 2>/dev/null |
    sed 's/^/  AutoSuspendIdleTimeoutSec=0 count=/'
grep -E '^AutoSuspendAction=' "$WORK/vfy/etc/xdg/powerdevilrc" 2>/dev/null &&
    echo '  WARNING: debug AutoSuspendAction override present' ||
    echo '  ok: no AutoSuspendAction override'
owner=$(chroot "$WORK/vfy" /sbin/apk info -W /etc/xdg/powerdevilrc 2>/dev/null)
case "$owner" in
*"owned by samurai-desktop"*)
    echo "  ok: $owner" ;;
*)
    echo "  FAIL: /etc/xdg/powerdevilrc has no package owner ($owner)" ;;
esac
echo '  package total:'
grep -c '^P:' "$WORK/vfy/lib/apk/db/installed" | sed 's/^/    /'
echo '  official recommends installed:'
for p in hkdm ttyescape plasma-mobile-sounds vvmd vvmplayer; do
    if grep -q "^P:$p$" "$WORK/vfy/lib/apk/db/installed"; then
        echo "    ok $p"
    else
        echo "    MISSING $p"
    fi
done
umount "$WORK/vfy"
losetup -D 2>/dev/null || true

echo '=== 6. publish ==='
mv "$WORK/packed.simg" "$OUTDIR/samurai-stable-f2fs-partuuid.simg"
sha256sum "$OUTDIR/samurai-stable-f2fs-partuuid.simg"
stat -c '%s bytes' "$OUTDIR/samurai-stable-f2fs-partuuid.simg"
