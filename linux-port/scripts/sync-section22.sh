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
if grep -q '^## 22\. ' "$HW"; then echo "already present"; else cat "$W/docs/22-kernel-upstream.md" >> "$HW"; fi
cp -f "$HW" "$RK/Platform/Realme/sm8150/HANDOVER-NEXT.md"
cp -f "$W/scripts/fork-linux.sh" "$W/scripts/fetch-upstream-bg.sh" "$W/scripts/mirror-linux-port.sh" "$W/scripts/push-fork.sh" "$RK/Platform/Realme/sm8150/linux-port/scripts/" 2>/dev/null || true
grep -n '^## 22\.\|^### 22\.' "$HW"
cd "$RK"
git add Platform/Realme/sm8150/HANDOVER-NEXT.md Platform/Realme/sm8150/linux-port 2>/dev/null
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m "docs: plan for putting the kernel side on GitHub as a real upstream fork

The kernel tree came from the official v7.3-rc6 tarball and was re-imported as a
single squashed commit, so it shares no ancestry with upstream and pushing it
would have meant a 335 MB upload of a brand new history.  We forked
torvalds/linux instead: the fork network already holds the upstream objects, so
once the two patches are rebased onto the real tag only the delta goes up.

Records the exact upstream base (a90ee4305c4a, matching the baseline commit's
message), the new upstream workspace, the commands to run once the 1.2 GB
shallow fetch finishes, the scripts added this round, the pitfalls (forks do
not advertise upstream tags; git fetch cannot resume; the GitHub proxy at
127.0.0.1:7890 is flaky; shallow pushes may be rejected) and the reminder to
rotate the leaked PAT." 2>/dev/null || true
git log --oneline -2
echo "=== push ==="
bash "$W/scripts/push-fork.sh" 2>&1 | tail -5
echo "=== fetch ?? ==="
du -sh /home/cy122/x2pro-linux/upstream/.git 2>/dev/null; pgrep -c -f 'git fetch' || true