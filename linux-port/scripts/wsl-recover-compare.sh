#!/usr/bin/env bash
set -euo pipefail

orig=/mnt/orig-ro
fixed=/mnt/fixed-ro

echo '=== original steps/usr/lib ==='
ls -la "$orig/home/cy122/steps/usr/lib" 2>&1 | head -5 || true
echo '=== fixed steps/usr/lib ==='
ls -la "$fixed/home/cy122/steps/usr/lib" 2>&1 | head -5 || true

echo '=== key file counts ==='
for rel in home/cy122/samurai-dist-repo home/cy122/standard-arm64-v7.3.1 home/cy122/steps; do
    printf '%-45s orig=' "$rel"
    find "$orig/$rel" -type f 2>/dev/null | wc -l
    printf '%-45s fixed=' "$rel"
    find "$fixed/$rel" -type f 2>/dev/null | wc -l
done

echo '=== git status ==='
git -C "$fixed/home/cy122/samurai-dist-repo" -c safe.directory='*' rev-parse HEAD
git -C "$fixed/home/cy122/samurai-dist-repo" -c safe.directory='*' status --porcelain=v1 | wc -l
echo '=== bash history ==='
wc -c "$orig/home/cy122/.bash_history" "$fixed/home/cy122/.bash_history"
echo '=== compare git HEAD/status ==='
git -C "$orig/home/cy122/samurai-dist-repo" -c safe.directory='*' rev-parse HEAD
git -C "$orig/home/cy122/samurai-dist-repo" -c safe.directory='*' status --porcelain=v1 > /tmp/compare-orig-status
git -C "$fixed/home/cy122/samurai-dist-repo" -c safe.directory='*' status --porcelain=v1 > /tmp/compare-fixed-status
diff -u /tmp/compare-orig-status /tmp/compare-fixed-status
echo '=== done ==='
