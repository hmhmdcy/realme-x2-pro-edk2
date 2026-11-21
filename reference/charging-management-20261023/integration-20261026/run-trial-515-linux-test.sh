#!/usr/bin/env bash
set -euo pipefail

src="/mnt/e/RealmeX2Pro edk2/reference/charging-management-20261023/integration-20261026/trial-515"
dst="/tmp/charging-trial-515-linux-test-r1"

if [[ -e "$dst" ]]; then
    echo "refusing to overwrite $dst" >&2
    exit 1
fi

cp -a "$src" "$dst"
find "$dst" -type d -exec chmod 0755 {} +
find "$dst" -type f -exec chmod go-w {} +
cd "$dst/tests"
python3 -m unittest \
    test_trial_suite.GuardStageTests.test_guard_restores_through_by_partlabel_symlink \
    -v
