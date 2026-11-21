#!/usr/bin/env bash
set -euo pipefail

src="/mnt/e/RealmeX2Pro edk2/reference/charging-management-20261023/integration-20261026/trial-516"
dst="/tmp/charging-trial-516-upload-r2"
archive="/mnt/e/edk2-samurai-out/charging-management-20261023/charging-integration-trial-20261026-06-r2.upload.tar.gz"
mirror="/mnt/e/edk2-samurai-out/charging-management-20261023/charging-integration-trial-20261026-06-r2"

for path in "$dst" "$archive" "$mirror"; do
    if [[ -e "$path" ]]; then
        echo "refusing to overwrite $path" >&2
        exit 1
    fi
done

mkdir -m 0700 "$dst"
cp -a "$src/." "$dst/"
find "$dst" -type d -exec chmod 0755 {} +
find "$dst" -type f -exec chmod 0644 {} +
chmod 0755 \
    "$dst/acknowledge_trial.py" \
    "$dst/postboot_audit.py" \
    "$dst/trial_guard.py" \
    "$dst/trial_stage.py" \
    "$dst/service/samurai-charging" \
    "$dst/tests/run_tests.py"

(
    cd "$dst"
    sha256sum -c SHA256SUMS
)

tar -C "$dst" --owner=0 --group=0 --numeric-owner -czf "$archive" .
cp -a "$dst" "$mirror"
(
    cd "$mirror"
    sha256sum -c SHA256SUMS
)

sha256sum "$archive"
stat -c '%a %U:%G %s %n' \
    "$dst/trial_common.py" \
    "$dst/trial_guard.py" \
    "$dst/service/samurai-charging" \
    "$archive"
