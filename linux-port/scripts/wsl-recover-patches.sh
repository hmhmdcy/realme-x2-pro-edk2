#!/usr/bin/env bash
set -euo pipefail

src_root=/mnt/orig-ro/home/cy122
out=/home/cy122/orig-Ubuntu-20261119/repo-patches

mkdir -p "$out"

for repo in samurai-stable-repo linux-samurai-github standard-arm64-v7.3.1 pmaports-samurai-userspace; do
    src="$src_root/$repo"
    dst="$out/$repo"
    echo "===$repo==="
    if ! git -C "$src" -c safe.directory='*' rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "not-git"
        continue
    fi
    git -C "$src" -c safe.directory='*' rev-parse HEAD > "$dst.HEAD"
    git -C "$src" -c safe.directory='*' status --porcelain=v1 > "$dst.status"
    git -C "$src" -c safe.directory='*' diff --binary --full-index > "$dst.patch"
    git -C "$src" -c safe.directory='*' ls-files --others --exclude-standard > "$dst.untracked"
    wc -l "$dst.status" "$dst.untracked"
done

ls -lh "$out"
