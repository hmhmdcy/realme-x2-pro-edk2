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
PKG_SRC=/mnt/e/RealmeX2Pro\ edk2/linux-port/packages/samurai-desktop
DESKTOP_VERSION=$(sed -n 's/^pkgver=//p' "$PKG_SRC/APKBUILD")-r$(sed -n 's/^pkgrel=//p' "$PKG_SRC/APKBUILD")

# The six official recommends are signed by the Alpine release key, not by
# the postmarketOS build key, so the image needs that public key as well.
ALPINE_KEY=/root/akeys/alpine-devel@lists.alpinelinux.org-616ae350.rsa.pub
SIGN_KEY=/mnt/e/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/signing-key-private.rsa

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

# The board repository must be built from the recipes, never hand-carried.
# Before this step existed the image shipped samurai-platform 6-r22 while the
# recipe was at 6-r25, so `apk upgrade` never saw the newer files.  Rebuild
# every package whose recipe revision differs from the staged repository and
# fail if a recipe cannot be built.
echo '=== 2a0. board recipes -> APKs (no drift allowed) ==='
REPO_SRC="$REPO_SRC" SIGN_KEY="$SIGN_KEY" \
    bash "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/_wsl-samurai/boardrepo-sync.sh" >&2

# The base image predates the camera flash fix, so its runtime modules tree
# still contains the stub build of leds-qcom-flash.ko (18 KB, no v4l2_flash
# symbols) and no v4l2-flash-led-class.ko at all.  Those three .ko files were
# rebuilt and verified against the running kernel's vermagic; re-install them
# so this image keeps the camera fix instead of silently reverting it.
FLASH_MOD=/root/camflash-modules
if [ ! -d "$FLASH_MOD" ]; then
    mkdir -p "$FLASH_MOD"
    K=/home/cy122/x2pro-linux/linux
    for f in \
        drivers/leds/flash/leds-qcom-flash.ko \
        drivers/leds/led-class-flash.ko \
        drivers/media/v4l2-core/v4l2-flash-led-class.ko; do
        [ -f "$K/$f" ] || { echo "FATAL: missing built module $K/$f" >&2; exit 1; }
        install -Dm644 "$K/$f" "$FLASH_MOD/$(basename "$f")"
    done
fi
if [ -d "$FLASH_MOD" ]; then
    echo '=== 2a0b. re-embed the camera flash modules ==='
    for rel in "$WORK/root"/lib/modules/*; do
        [ -d "$rel" ] || continue
        case "$rel" in
        *-usbwake-otg) ;;
        *) continue ;;
        esac
        for pair in \
            kernel/drivers/leds/flash/leds-qcom-flash.ko \
            kernel/drivers/leds/led-class-flash.ko \
            kernel/drivers/media/v4l2-core/v4l2-flash-led-class.ko; do
            src="$FLASH_MOD/$(basename "$pair")"
            [ -f "$src" ] || { echo "  FATAL: missing $src" >&2; exit 1; }
            install -Dm644 "$src" "$rel/$pair"
            echo "  $(basename "$pair"): $(stat -c %s "$src") bytes"
        done
    done
else
    echo '  WARNING: /root/camflash-modules missing; camera fix not embedded'
fi

cp "$REPO_SRC"/*.apk "$REPO_SRC"/APKINDEX.tar.gz \
    "$WORK/root/usr/share/samurai/packages/aarch64/"

# The board repository is signed by this port's own key.  Without it every
# board APK verifies as UNTRUSTED, so `apk upgrade` can never resolve them:
# the packages are on disk, in the index, and correctly signed, but the
# trust anchor is missing.  The delivery image built on 2026-11-20 shipped
# with only the Alpine keys plus build.postmarketos.org, and 22/22 board
# APKs failed verification against that key set while all 22 passed against
# the full local key set.  Copy every non-Alpine key so this cannot recur.
install -d -m 0755 "$WORK/root/etc/apk/keys"
for key in /root/installed_keys/*.rsa.pub; do
    case "$(basename "$key")" in
    alpine-devel@*) continue ;;
    esac
    install -Dm644 "$key" "$WORK/root/etc/apk/keys/$(basename "$key")"
done
BOARD_KEY="$WORK/root/etc/apk/keys/pmos@local-6aeaf066.rsa.pub"
[ -f "$BOARD_KEY" ] ||
    { echo "FATAL: board signing key was not copied" >&2; exit 1; }
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

# The base image still records the board packages from an older build
# (samurai-platform 6-r22, samurai-ssc 1-r2, samurai-systemd 1-r4).  Copying
# files by hand fixed the content but never the database, so `apk upgrade`
# had nothing to offer and the recipes stayed invisible.  Upgrade the real
# packages from the freshly built board repository before anything else
# touches those paths.
echo '=== 2a2. upgrade installed board packages to the recipe versions ==='
targets=''

# The base image pinned the old board revisions in /etc/apk/world
# (samurai-platform=6-r22 etc).  apk refuses to move past an explicit pin,
# which is exactly why the recipes never reached the image.  Drop the pin
# only for these three packages; every other world entry keeps its spec.
WORLD="$WORK/root/etc/apk/world"
if [ -f "$WORLD" ]; then
    cp "$WORLD" "$WORK/world.pre-upgrade"
    for recipe in samurai-platform samurai-ssc samurai-systemd; do
        sed -i "s/^$recipe=[^<>~]*$/$recipe/" "$WORLD"
    done
    echo "  world pins removed: $(diff "$WORK/world.pre-upgrade" "$WORLD" | grep -c '^>' || true)"
fi

for recipe in samurai-platform samurai-ssc samurai-systemd; do
    dir="/mnt/e/RealmeX2Pro edk2/linux-port/packages/$recipe"
    want=$(sed -n 's/^pkgver=//p' "$dir/APKBUILD" | head -1)-r$(sed -n 's/^pkgrel=//p' "$dir/APKBUILD" | head -1)
    targets="$targets $REPO_SRC/$recipe-$want.apk"
    # Subpackages share the revision and must move together.
    for sub in "$REPO_SRC/$recipe"-*"-r${want##*-r}".apk; do
        [ -e "$sub" ] || continue
        [ "$sub" = "$REPO_SRC/$recipe-$want.apk" ] && continue
        targets="$targets $sub"
    done
done
# Install by path rather than by name: with --root, apk resolves a repository
# entry to a *host* path, so a board package inside the root tree is reported
# as "mentioned in index not found".  An explicit file needs no index lookup.
# Only these board packages are replaced; a blanket upgrade would also try to
# fetch upstream blobs that are not cached.
"$APK" --root "$WORK/root" --arch aarch64 --scripts=no \
    --keys-dir "$WORK/root/etc/apk/keys" --no-network \
    add $targets 2>&1 | tail -8
for recipe in samurai-platform samurai-ssc samurai-systemd; do
    dir="/mnt/e/RealmeX2Pro edk2/linux-port/packages/$recipe"
    want=$(sed -n 's/^pkgver=//p' "$dir/APKBUILD" | head -1)-r$(sed -n 's/^pkgrel=//p' "$dir/APKBUILD" | head -1)
    got=$(awk -v want="$recipe" '/^P:/{n=substr($0,3)} /^V:/{if(n==want){print substr($0,3);exit}}' \
        "$WORK/root/lib/apk/db/installed")
    [ "$got" = "$want" ] ||
        { echo "  FATAL: $recipe installed ${got:-missing}, recipe $want" >&2; exit 1; }
    echo "  ok: $recipe $got"
done

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

# Alpine published three patch revisions after the delivery image's indices
# were cached: gnutls 3.8.13-r0 -> 3.8.14-r0, libssl3/libcrypto3 3.5.9-r0
# -> 3.5.9-r1.  They are routine upstream security/bugfix revisions, all
# Alpine-signed, and no local package pins them exactly.  Install them here
# so the shipped image matches the current stable channel, and also refresh
# the four cached indices so `apk upgrade` on the device sees anything newer
# without a network round trip.
OFFICIAL=/root/official-bump
if [ -d "$OFFICIAL" ]; then
    echo '=== 2c. official patch revisions + refreshed index cache ==='
    for apk in gnutls-3.8.14-r0 libssl3-3.5.9-r1 libcrypto3-3.5.9-r1; do
        [ -s "$OFFICIAL/$apk.apk" ] ||
            { echo "  FATAL: missing $OFFICIAL/$apk.apk" >&2; exit 1; }
    done
    "$APK" --root "$WORK/root" --arch aarch64 --scripts=no \
        --keys-dir "$WORK/root/etc/apk/keys" --no-network \
        add "$OFFICIAL/gnutls-3.8.14-r0.apk" \
            "$OFFICIAL/libssl3-3.5.9-r1.apk" \
            "$OFFICIAL/libcrypto3-3.5.9-r1.apk" ||
        { echo '  FATAL: official patch install failed' >&2; exit 1; }

    # The cache file names are the ones apk itself already created for
    # these four repositories (they are not a plain hash of the URL), so
    # keep those names and only swap the contents.
    install -d -m 0755 "$WORK/root/var/cache/apk"
    cache_copy() {
        src=$1
        [ -s "$src" ] || { echo "  FATAL: missing $src" >&2; exit 1; }
        for name in $2; do
            install -Dm644 "$src" "$WORK/root/var/cache/apk/$name"
        done
    }
    cache_copy "$OFFICIAL/systemd.tar.gz" \
        "APKINDEX.4aa4fd32.tar.gz"
    cache_copy "$OFFICIAL/pmos.tar.gz" \
        "APKINDEX.6015956e.tar.gz"
    cache_copy "$OFFICIAL/main.tar.gz" \
        "APKINDEX.5773bea6.tar.gz"
    cache_copy "$OFFICIAL/community.tar.gz" \
        "APKINDEX.3cace40b.tar.gz"
fi

echo '=== 3. checks ==='
"$APK" --root "$WORK/root" version >/dev/null 2>&1 || true

# Board-wide KDE default: never auto-suspend.  s2idle on this kernel drops
# both the USB/NCM link and the Wi-Fi link, i.e. the only remote access
# paths, so an unattended suspend makes the device unreachable.  The file
# pins both values the KDE power frontends write for "Never" (desktop KCM:
# AutoSuspendAction=0, Plasma Mobile KCM: AutoSuspendIdleTimeoutSec=0), and
# it is placed in /etc/xdg so a user's own ~/.config/powerdevilrc still wins.
#
# Do NOT copy the file directly: the first delivery image did exactly that,
# which left /etc/xdg/powerdevilrc with no owner in lib/apk/db/installed and
# made `apk upgrade` unable to replace it.  Install the real package instead
# so apk records the owner (verify with `apk info -W /etc/xdg/powerdevilrc`).
# A missing or rejected package must abort the build.  Skipping it silently
# produced a bootable image with no auto-suspend default, which only
# surfaces after the first unattended s2idle.  `apk add` also validates the
# signature, so the `-f` test alone is not enough.
DESKTOP_APK="$REPO_SRC/samurai-desktop-$DESKTOP_VERSION.apk"
[ -f "$DESKTOP_APK" ] ||
    { echo "FATAL: missing $DESKTOP_APK; run build-desktop-r17.sh + rebuild-board-index.sh" >&2; exit 1; }
"$APK" --root "$WORK/root" --arch aarch64 --scripts=no \
    --keys-dir "$WORK/root/etc/apk/keys" --no-network \
    add "$DESKTOP_APK" ||
    { echo "FATAL: samurai-desktop $DESKTOP_VERSION install failed" >&2; exit 1; }

# `apk add /path/to/file.apk` writes the package into /etc/apk/world with a
# "<Q1...=" checksum pin.  Measured here: with the pin present, `apk upgrade`
# keeps samurai-desktop at 4-r19 even after the board repository publishes
# 4-r20; with the pin stripped it upgrades normally.  The pin comes from
# installing by path during an offline build, not from upstream pmOS/Alpine,
# so strip it.  gnutls/libssl3/libcrypto3 only entered world for the same
# reason -- they are dependencies, not user choices.
#
# This must run after every `apk add` above, because each of them re-adds a
# pin for the package it installs.
echo '=== 3b. normalize /etc/apk/world ==='
WORLD="$WORK/root/etc/apk/world"
pins_before=$(grep -c '<Q' "$WORLD" || true)
sed -i 's/><Q[0-9A-Za-z+/=]*//g' "$WORLD"
for lib in gnutls libssl3 libcrypto3; do
    sed -i "\|^$lib\$|d" "$WORLD"
done
pins_after=$(grep -c '<Q' "$WORLD" || true)
echo "  checksum pins: ${pins_before:-0} -> ${pins_after:-0}"
[ "${pins_after:-0}" -eq 0 ] ||
    { echo '  FAIL: world still carries checksum pins' >&2; exit 1; }

# A distribution image must not ship this household's Wi-Fi PSK.  The
# profile was written straight into the rootfs during development so the
# phone would auto-connect after a flash; that also hands anyone holding the
# image the network password.  Delete it and let the user join a network in
# the Plasma UI, which writes an apk-invisible but correctly owned
# connection at first use.
echo '=== 3c. strip private network credentials ==='
CONN="$WORK/root/etc/NetworkManager/system-connections"
if [ -d "$CONN" ]; then
    removed=0
    for f in "$CONN"/*; do
        [ -f "$f" ] || continue
        if grep -qE '^[[:space:]]*(psk|password|private-key)[[:space:]]*=' "$f"; then
            echo "  removing credentialed profile: $(basename "$f")"
            rm -f "$f"
            removed=$((removed + 1))
        fi
    done
    echo "  removed: $removed"
fi

# A distribution image must not carry a previous session's package stash.
# /home/user/plasma-apps-20261117 is 180 .apk files (242 MiB) copied in by hand
# while bringing Plasma apps up; it is not owned by any package, so apk can
# never update or remove it.  Everything it contains is already installed from
# the official repositories.
echo '=== 3c2. drop board-private package stashes ==='
STASH="$WORK/root/home/user/plasma-apps-20261117"
if [ -e "$STASH" ]; then
    bytes=$(du -sb "$STASH" | cut -f1)
    count=$(find "$STASH" -name '*.apk' | wc -l)
    echo "  removing $STASH (${count} apk, ${bytes} bytes)"
    rm -rf "$STASH"
fi
for d in "$WORK/root/tmp" "$WORK/root/root"; do
    [ -d "$d" ] || continue
    n=$(find "$d" -name '*.apk' 2>/dev/null | wc -l)
    [ "$n" -eq 0 ] || { echo "  FAIL: $n apk left in $d" >&2; exit 1; }
done

# No board-private sshd drop-in.  50-postmarketos-ui-policy.conf already sets
# UsePAM yes, and openssh defaults are PasswordAuthentication yes /
# KbdInteractiveAuthentication yes; `sshd -T` inside a chroot of this image
# was byte-identical with and without the extra file.  It was unowned, so
# `apk upgrade` could never replace it.
STRAY_SSHD="$WORK/root/etc/ssh/sshd_config.d/99-samurai.conf"
if [ -f "$STRAY_SSHD" ]; then
    echo '  removing unowned /etc/ssh/sshd_config.d/99-samurai.conf'
    rm -f "$STRAY_SSHD"
fi

echo '=== 3d. SSH must be reachable on Wi-Fi and NCM ==='
if python3 /mnt/e/RealmeX2Pro\ edk2/linux-port/scripts/_wsl-samurai/check-ssh-image.py \
    --root "$WORK/root" 2>&1 | tail -16; then
    :
else
    echo '  FAIL: SSH would not be reachable on a fresh boot' >&2
    exit 1
fi
if python3 /mnt/e/RealmeX2Pro\ edk2/linux-port/scripts/_wsl-samurai/check-ssh-image.py \
    --root "$WORK/root" >/dev/null 2>&1; then
    echo '  ok: sshd enabled, listening on 0.0.0.0:22, login account usable'
else
    echo '  FAIL: SSH would not be reachable on a fresh boot' >&2
    exit 1
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
    { echo '  MISSING: /etc/xdg/powerdevilrc' >&2; exit 1; }
count=$(grep -c '^AutoSuspendIdleTimeoutSec=0$' "$WORK/vfy/etc/xdg/powerdevilrc" 2>/dev/null || true)
echo "  AutoSuspendIdleTimeoutSec=0 count=$count"
[ "${count:-0}" -eq 3 ] ||
    { echo '  FAIL: auto-suspend not disabled on all three profiles' >&2; exit 1; }
count_action=$(grep -c '^AutoSuspendAction=0$' "$WORK/vfy/etc/xdg/powerdevilrc" 2>/dev/null || true)
echo "  AutoSuspendAction=0 count=$count_action"
[ "${count_action:-0}" -eq 3 ] ||
    { echo '  FAIL: NoAction not set on all three profiles' >&2; exit 1; }
if grep -E '^AutoSuspendAction=' "$WORK/vfy/etc/xdg/powerdevilrc" 2>/dev/null |
    grep -vqx '^AutoSuspendAction=0$'; then
    echo '  FAIL: non-NoAction AutoSuspendAction present' >&2
    exit 1
fi
echo '  ok: NoAction + never auto-suspend on all three profiles'

# The image must actually carry the board packages the recipes describe.
# The delivery image shipped `samurai-platform 6-r22` while the recipe was
# already at 6-r24, so the fixed samurai-wifi (regdb copy) and
# wifi.powersave=2 never reached the device -- cfg80211 kept falling back to
# "country 99" and 5 GHz stayed PASSIVE-SCAN.  Compare every board recipe
# version against the APK database instead of trusting the build log.
echo '=== board package versions must match the recipes ==='
for recipe in samurai-platform samurai-desktop samurai-gnss-assist \
              samurai-camera-config samurai-camera-stack samurai-systemd \
              samurai-ssc samurai-libssc samurai-hexagonrpcd \
              samurai-radio-tools unudhcpd usb-signaller; do
    d="/mnt/e/RealmeX2Pro edk2/linux-port/packages/$recipe"
    [ -f "$d/APKBUILD" ] || continue
    want=$(sed -n 's/^pkgver=//p' "$d/APKBUILD")-r$(sed -n 's/^pkgrel=//p' "$d/APKBUILD")
    # Read the version straight out of the installed database.  `apk info -v`
    # on this apk-tools build prints the description for some packages, which
    # made this gate compare a sentence against a version number.
    got=$(awk -v want="$recipe" '
        /^P:/ { name = substr($0, 3) }
        /^V:/ { if (name == want) { print substr($0, 3); exit } }
        ' "$WORK/vfy/lib/apk/db/installed")
    if [ -z "$got" ]; then
        echo "  missing: $recipe (want $want)" >&2
        exit 1
    fi
    [ "$got" = "$want" ] || {
        echo "  FAIL: $recipe installed $got, recipe $want" >&2
        exit 1
    }
    echo "  ok: $recipe $got"
done

# apk needs the target root but not binfmt: -W only reads the DB.  chroot
# would need qemu-aarch64 registered, which this WSL distro does not have.
owner=$(awk '
    /^P:/ { name = substr($0, 3); next }
    /^F:/ { dir = substr($0, 3); next }
    /^R:/ {
        if (dir == "etc/xdg" && substr($0, 3) == "powerdevilrc") { print name; exit }
    }
    ' "$WORK/vfy/lib/apk/db/installed")
case "$owner" in
samurai-desktop)
    echo "  ok: /etc/xdg/powerdevilrc owned by samurai-desktop" ;;
*)
    echo "  FAIL: /etc/xdg/powerdevilrc has no package owner (${owner:-none})" >&2
    exit 1 ;;
esac

echo '=== board trust anchor (must verify every board APK) ==='
board_keys=$(ls "$WORK/vfy/etc/apk/keys" | grep -v 'alpine-devel@' || true)
if [ -z "$board_keys" ]; then
    echo '  FAIL: no non-Alpine key in /etc/apk/keys' >&2
    exit 1
fi
ls "$WORK/vfy/etc/apk/keys" | grep -v 'alpine-devel@' | sed 's/^/  key: /'
untrusted=0
for f in "$WORK/vfy"/usr/share/samurai/packages/aarch64/*.apk; do
    [ -e "$f" ] || continue
    if ! "$APK" --keys-dir "$WORK/vfy/etc/apk/keys" verify "$f" >/dev/null 2>&1; then
        echo "  UNTRUSTED $(basename "$f")" >&2
        untrusted=$((untrusted + 1))
    fi
done
if [ "$untrusted" -ne 0 ]; then
    echo "  FAIL: $untrusted board APK(s) not trusted by the image key set" >&2
    exit 1
fi
echo '  ok: every board APK verifies against the image key set'
echo '=== upstream patch revisions (must match the current stable channel) ==='
for p in gnutls libssl3 libcrypto3; do
    v=$(awk -v want="$p" '
        /^P:/ { name = substr($0, 3); next }
        /^V:/ { if (name == want) { print substr($0, 3); exit } }
        ' "$WORK/vfy/lib/apk/db/installed")
    echo "  $p=$v"
done
echo '=== cached index files ==='
for f in "$WORK/vfy"/var/cache/apk/APKINDEX.*.tar.gz; do
    [ -f "$f" ] || continue
    printf '  %-28s %s bytes\n' "$(basename "$f")" "$(stat -c %s "$f")"
done
echo '=== world must not carry build-time checksum pins ==='
world_pins=$(grep -c '<Q' "$WORK/vfy/etc/apk/world" || true)
echo "  checksum pins: ${world_pins:-0}"
[ "${world_pins:-0}" -eq 0 ] ||
    { echo '  FAIL: world carries <Q...= pins; upgrades would be frozen' >&2; exit 1; }

# No package stash may survive in the packed image.  Anything under /home or
# /tmp that apk did not install cannot be upgraded or removed later, and it
# silently inflates the delivery image.
echo '=== no unowned .apk stashes in the packed image ==='
stray=$(find "$WORK/vfy/home" "$WORK/vfy/tmp" "$WORK/vfy/root" \
    -name '*.apk' 2>/dev/null | wc -l)
echo "  stray apk files: ${stray:-0}"
if [ "${stray:-0}" -ne 0 ]; then
    find "$WORK/vfy/home" "$WORK/vfy/tmp" "$WORK/vfy/root" -name '*.apk' 2>/dev/null |
        sed 's/^/  /' >&2
    echo '  FAIL: unowned .apk files would ship in the delivery image' >&2
    exit 1
fi

echo '=== offline upgrade must resolve ==='
"$APK" --root "$WORK/vfy" --arch aarch64 --keys-dir "$WORK/vfy/etc/apk/keys" \
    --no-network upgrade --simulate > "$WORK/upgrade.txt" 2>&1
rc=$?
tail -2 "$WORK/upgrade.txt" | sed 's/^/  /'
[ "$rc" -eq 0 ] ||
    { echo '  FAIL: apk upgrade --simulate failed' >&2; exit 1; }
echo '  ok: apk upgrade --simulate rc=0'

echo '=== runtime flash modules must not be the stub build ==='
python3 - "$WORK/vfy" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
rows = []
for release in sorted((root / 'lib/modules').glob('*')):
    if not release.is_dir() or not release.name.endswith('-usbwake-otg'):
        continue
    qcom = release / 'kernel/drivers/leds/flash/leds-qcom-flash.ko'
    v4l2 = release / 'kernel/drivers/media/v4l2-core/v4l2-flash-led-class.ko'
    refs = qcom.is_file() and b'v4l2_flash_init' in qcom.read_bytes()
    rows.append((release.name, qcom.is_file(), v4l2.is_file(), refs))

if not rows:
    raise SystemExit('no -usbwake-otg modules tree in the image')
for name, qcom, v4l2, refs in rows:
    print(f'  {name} qcom={qcom} v4l2={v4l2} refs={refs}')
bad = [r for r in rows if not (r[1] and r[2] and r[3])]
if bad:
    raise SystemExit('FAIL: camera flash modules are the stub build: '
                     + ', '.join(r[0] for r in bad))
print('  ok: camera flash modules take the real v4l2 path')
PY

echo '=== no private credentials in the delivery image ==='
if python3 /mnt/e/RealmeX2Pro\ edk2/linux-port/scripts/_wsl-samurai/check-secrets.py \
    --root "$WORK/vfy" 2>&1 | tail -5; then :; fi
python3 /mnt/e/RealmeX2Pro\ edk2/linux-port/scripts/_wsl-samurai/check-secrets.py \
    --root "$WORK/vfy" >/dev/null 2>&1 ||
    { echo '  FAIL: image carries a private credential' >&2; exit 1; }
echo '  ok: no household Wi-Fi PSK or private key in the image'

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
