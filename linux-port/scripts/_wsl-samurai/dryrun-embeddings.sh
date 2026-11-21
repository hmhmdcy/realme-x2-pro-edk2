#!/bin/bash
# Dry run of repack-embeddings.sh step 2/2b: expand the source image,
# mount it, and *simulate* the apk operations so option semantics and
# dependency resolution are proven before committing a 30-minute rebuild.
set -eu

SRC=/mnt/e/edk2-samurai-out/standard-arm64-v731/rootfs-stable-20261119-apps2/samurai-stable-f2fs-partuuid.simg
WORK=/root/dryrun
APK=/root/apkstatic/sbin/apk.static
REPO_SRC=/root/boardrepo-r17
EXTRA=/root/recommends-repo

rm -rf "$WORK"
mkdir -p "$WORK/root"

echo '=== expand ==='
simg2img "$SRC" "$WORK/full.img"

losetup -D 2>/dev/null || true
L=$(losetup -f --show "$WORK/full.img")
mount -t f2fs "$L" "$WORK/root"
cleanup() {
    umount "$WORK/root" 2>/dev/null || true
    losetup -D 2>/dev/null || true
}
trap cleanup EXIT

echo '=== current state ==='
grep -c '^P:' "$WORK/root/lib/apk/db/installed"
"$APK" --root "$WORK/root" info -W /etc/xdg/powerdevilrc 2>&1 ||
    true

echo '=== stage keys the image would ship (board + Alpine release) ==='
install -d -m 0755 "$WORK/root/etc/apk/keys"
cp /root/installed_keys/pmos@local-6aeaf066.rsa.pub \
    "$WORK/root/etc/apk/keys/"
cp /root/akeys/alpine-devel@lists.alpinelinux.org-616ae350.rsa.pub \
    "$WORK/root/etc/apk/keys/"

echo '=== simulate: install samurai-desktop 4-r17 ==='
"$APK" --root "$WORK/root" --arch aarch64 --scripts=no \
    --keys-dir etc/apk/keys --repositories-file /dev/null --no-network \
    add --simulate "$REPO_SRC/samurai-desktop-4-r17.apk" 2>&1 | tail -6

echo '=== simulate: install the six official recommends ==='
"$APK" --root "$WORK/root" --arch aarch64 --scripts=no \
    --keys-dir etc/apk/keys --repositories-file /dev/null --no-network \
    add --simulate \
    "$EXTRA"/gst-libav-*.apk "$EXTRA"/gst-plugins-ugly-*.apk \
    "$EXTRA"/hkdm-*.apk "$EXTRA"/plasma-mobile-sounds-*.apk \
    "$EXTRA"/vvmd-*.apk "$EXTRA"/vvmplayer-*.apk 2>&1 | tail -8

echo '=== install the seven recommends by file (real, not simulated) ==='
for f in "$EXTRA"/*.apk; do
    printf '  %-34s ' "$(basename "$f")"
    "$APK" --root "$WORK/root" --arch aarch64 --scripts=no \
        --keys-dir etc/apk/keys --no-network add "$f" 2>&1 | tail -1
done
echo '=== package count after ==='
grep -c '^P:' "$WORK/root/lib/apk/db/installed"
echo '=== /etc/xdg/powerdevilrc owner in the rebuilt image ==='
"$APK" --root "$WORK/root" info -W /etc/xdg/powerdevilrc 2>&1

echo '=== dry run finished ==='
