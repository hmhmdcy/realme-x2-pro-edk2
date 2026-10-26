#!/bin/bash
set -e
W="/mnt/e/RealmeX2Pro edk2/linux-port"
HW="/mnt/e/RealmeX2Pro edk2/HANDOVER-NEXT.md"
RK=/home/cy122/edk2-samurai/repo

cp -f "$HW" "$RK/Platform/Realme/sm8150/HANDOVER-NEXT.md"
grep -n '^### 19\.8' "$HW"
cd "$RK"
git add Platform/Realme/sm8150/HANDOVER-NEXT.md
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -F "$W/scripts/commit-msg-section198.txt"
git log --oneline -2
echo "=== push ==="
bash "$W/scripts/push-fork.sh"