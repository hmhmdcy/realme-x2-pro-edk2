#!/bin/bash
set -e
W="/mnt/e/RealmeX2Pro edk2/linux-port"
HW="/mnt/e/RealmeX2Pro edk2/HANDOVER-NEXT.md"

# 2026-10-08: HANDOVER-NEXT.md is an index now - a section lives in exactly one
# file (linux-port/docs/NN-<topic>.md or sessions/NN-<topic>.md).  Never append
# a section body back into the handover.
if grep -q '^## History index' "$HW" 2>/dev/null; then
  echo "HANDOVER-NEXT.md is an index now - nothing to append; edit the section file instead."
  exit 0
fi
RK=/home/cy122/edk2-samurai/repo
if grep -q '^## 23\. ' "$HW"; then echo "already present"; else cat "$W/docs/23-upstream-push.md" >> "$HW"; fi
cp -f "$HW" "$RK/Platform/Realme/sm8150/HANDOVER-NEXT.md"
for f in probe-upstream.sh fetch-noproxy.sh finish-upstream.sh do-upstream-push.sh fetch-upstream-bg.sh fork-linux.sh mirror-linux-port.sh; do
  [ -f "$W/scripts/$f" ] && cp -f "$W/scripts/$f" "$RK/Platform/Realme/sm8150/linux-port/scripts/"
done
grep -n '^## 23\.\|^### 23\.' "$HW"
cd "$RK"
git add Platform/Realme/sm8150/HANDOVER-NEXT.md Platform/Realme/sm8150/linux-port 2>/dev/null
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m "docs: the kernel side is on the real upstream commit; WSL must bypass the proxy

The 1.2 GB v7.3-rc6 fetch had been failing for half an hour because git was
going through the Windows proxy at 127.0.0.1:7890, which dies with a TLS
handshake error a few seconds in.  Direct access takes 39 seconds.

The branch samurai-bringup now sits on the real upstream commit a90ee4305
(Linux 7.3-rc6) with our two patches applied cleanly, so the kernel side has a
proper upstream ancestry from here on.  Only the push is still missing, and the
likely reason plus the way to handle each error is written down, together with
the facts not to re-derive (upstream tag/commit metadata, the local tree hash
differing from upstream so the API-synthesised-commit shortcut is out, forks not
advertising upstream tags, git fetch not resuming)." 2>/dev/null || true
git log --oneline -2
echo "=== push ==="
bash "$W/scripts/push-fork.sh" 2>&1 | tail -5