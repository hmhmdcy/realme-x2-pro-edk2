#!/bin/sh
# Replay every local patch series against its pristine upstream archive.
# Read-only: works in a scratch directory, never touches the repo.
set -u

ROOT=$(cd "$(dirname "$0")/.." && pwd)
REPO=${REPO:-$ROOT}
OUT=${OUT:-/tmp/samurai-patch-replay}
CACHE=${CACHE:-$HOME/samurai-build/work/cache_distfiles}
if [ ! -d "$CACHE" ]; then
    echo "distfiles cache not found: $CACHE (set CACHE=...)" >&2
    exit 2
fi
rm -rf "$OUT"
mkdir -p "$OUT"

replay() {
    label="$1"; tarball="$2"; patchdir="$3"
    work="$OUT/$label"
    mkdir -p "$work"
    tar -xzf "$CACHE/$tarball" -C "$work"
    top=$(find "$work" -mindepth 1 -maxdepth 1 -type d | head -n1)
    applied=0
    failed=0
    for p in "$patchdir"/*.patch; do
        [ -e "$p" ] || continue
        if ( cd "$top" && patch -p1 --batch --forward --fuzz=0 -i "$p" >/dev/null 2>&1 ); then
            applied=$((applied + 1))
        else
            failed=$((failed + 1))
            echo "  FAILED: $(basename "$p")"
        fi
    done
    printf "%-22s applied=%d failed=%d\n" "$label" "$applied" "$failed"
}

echo "== patch series replay (fuzz=0) =="
replay usb-signaller usb-signaller-0.4.3.tar.gz "$REPO/device/testing/usb-signaller"

# radio-tools patches target two separate upstream trees inside one recipe.
rt="$OUT/radio-tools"
mkdir -p "$rt"
tar -xzf "$CACHE/tqftpserv-128cd6e.tar.gz" -C "$rt"
tar -xzf "$CACHE/rmtfs-b30a3eb.tar.gz" -C "$rt"
for pair in \
    "tqftpserv-128cd6e0a39734fefd0f0bf0aad5e997c29e2445:tqftpserv-work-files.patch" \
    "linux-msm-rmtfs-b30a3eb:rmtfs-cow-handler.patch" \
    "linux-msm-rmtfs-b30a3eb:rmtfs-runtime-root.patch"; do
    dir=${pair%%:*}; p=${pair##*:}
    if ( cd "$rt/$dir" && patch -p1 --batch --forward --fuzz=0 -i "$REPO/device/testing/samurai-radio-tools/$p" >/dev/null 2>&1 ); then
        echo "  ok: $p"
    else
        echo "  FAILED: $p"
    fi
done

replay unudhcpd unudhcpd-0.5.0.tar.gz "$REPO/device/testing/unudhcpd"
replay libssc libssc_0.4.4.orig.tar.gz "$REPO/device/testing/samurai-libssc"
replay hexagonrpcd hexagonrpc-v0.4.0.tar.gz "$REPO/device/testing/samurai-hexagonrpcd"
