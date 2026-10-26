#!/bin/bash
# Append HANDOVER-NEXT.md section 19, refresh linux-port/README.md, commit and push.
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

echo "=== 1. append section 19 to the working copy ==="
if grep -q '^## 19\. ' "$HW"; then
  echo "already present, skipping append"
else
  cat "$W/docs/19-loadoptions.md" >> "$HW"
fi
grep -n '^## 19\. \|^### 19\.' "$HW"
wc -l "$HW"

echo
echo "=== 2. README.md ==="
python3 "$W/scripts/update-readme-section19.py"

echo
echo "=== 3. copy both into the repo ==="
cp -f "$HW" "$RK/Platform/Realme/sm8150/HANDOVER-NEXT.md"
cp -f "$W/README.md" "$RK/Platform/Realme/sm8150/README.md"
diff -q "$HW" "$RK/Platform/Realme/sm8150/HANDOVER-NEXT.md" && echo "HANDOVER-NEXT.md in sync"
diff -q "$W/README.md" "$RK/Platform/Realme/sm8150/README.md" && echo "README.md in sync"

echo
echo "=== 4. commit ==="
cd "$RK"
git add Platform/Realme/sm8150/HANDOVER-NEXT.md Platform/Realme/sm8150/README.md
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -F "$W/scripts/commit-msg-section19.txt"
git log --oneline -3
git status --short

echo
echo "=== 5. push ==="
for i in 1 2 3 4; do
  echo "--- attempt $i ---"
  timeout 150 git push fork master 2>&1 | tail -3 && break
  sleep 8
done
timeout 60 git ls-remote fork master
echo DONE