#!/bin/bash
# 再同步一次 HANDOVER-NEXT.md（补了复现警告），提交并 push
set -u
RK=/home/cy122/edk2-samurai/repo
cd "$RK"

cp -f "/mnt/e/RealmeX2Pro edk2/HANDOVER-NEXT.md" Platform/Realme/sm8150/HANDOVER-NEXT.md
wc -l Platform/Realme/sm8150/HANDOVER-NEXT.md
grep -n '复现注意' Platform/Realme/sm8150/HANDOVER-NEXT.md

git add Platform/Realme/sm8150/HANDOVER-NEXT.md
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m 'docs: the kernel Image is a build product, put it back after cloning

Platform/Realme/sm8150/LinuxKernel/Image is deliberately not committed (30 MB,
rebuildable).  A fresh clone that runs ./build.sh -d samurai would fail because
SamuraiLinuxKernel.inf references it, so say so in the handover.'
git log --oneline -3

echo
echo "=== push ==="
timeout 120 git push fork master 2>&1 | tail -4 || echo "push 失败/超时，下次重试"
