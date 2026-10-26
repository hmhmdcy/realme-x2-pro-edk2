#!/bin/bash
# Section 24: the kernel branch reached GitHub.  Append the section to the
# handover, mirror the Linux side into the repo, commit and push to the fork.
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
D="$RK/Platform/Realme/sm8150/linux-port"

if grep -q '^## 24\. ' "$HW"; then echo "section 24 already present"; else
  cat "$W/docs/24-push-done.md" >> "$HW"
fi
grep -n '^## 24\.\|^### 24\.' "$HW"

cp -f "$HW" "$RK/Platform/Realme/sm8150/HANDOVER-NEXT.md"
mkdir -p "$D"
for x in docs scripts; do
  if [ -e "$W/$x" ]; then cp -r -f "$W/$x" "$D/"; else echo "  (skip $x)"; fi
done
chmod +x "$D"/scripts/*.sh 2>/dev/null || true
find "$D" -type f | wc -l

cd "$RK"
git add Platform/Realme/sm8150/HANDOVER-NEXT.md Platform/Realme/sm8150/linux-port
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m "docs: the kernel bring-up branch is on GitHub; push needs an attached WSL session

Section 23 stopped at the push; samurai-bringup is now on hmhmdcy/linux at
a89e94cd5, verified with ls-remote, so the kernel side finally has a real
upstream ancestry on the remote as well.

Two corrections to what section 23 guessed.  GitHub does accept a push from a
--depth=1 clone - no \"shallow update not allowed\" - but it is NOT a
few-hundred-KB delta: the fork does not advertise upstream tags, so git cannot
see that the server already has a90ee4305 and uploads the whole 285 MiB
snapshot pack, which takes about four and a half minutes.  And a nohup'ed
background push does not survive a WSL distro recycle - the first attempt was
killed after two minutes and left tmp_pack_* garbage behind.  The working way is
to keep a foreground wsl.exe attached for the whole push, which is what
scripts/push-branch.sh is written for." 2>/dev/null || true
git log --oneline -2
echo "=== push ==="
bash "$W/scripts/push-fork.sh" 2>&1 | tail -5