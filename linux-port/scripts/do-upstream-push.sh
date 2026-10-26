#!/bin/bash
D=/home/cy122/x2pro-linux/upstream
cd "$D" || exit 1
echo "=== ???? (?? 36s) $(date +%T) ==="
up=no
for i in $(seq 1 12); do
  if timeout 6 git ls-remote up HEAD >/dev/null 2>&1; then echo "proxy OK at ${i}"; up=yes; break; fi
  printf "."
  sleep 2
done
[ "$up" = yes ] || { echo " ??????????"; exit 2; }
echo "=== fetch $(date +%T) ==="
timeout 225 git fetch --depth=1 up refs/tags/v7.3-rc6:refs/tags/v7.3-rc6 2>&1 | tail -3
echo "=== ${date +%T} ==="
git rev-parse --verify -q refs/tags/v7.3-rc6 && echo "TAG OK" || { echo "NO TAG"; du -sh .git; exit 1; }
git checkout -b samurai-bringup refs/tags/v7.3-rc6 2>&1 | tail -2
P="/mnt/e/RealmeX2Pro edk2/linux-port/patches"
git am "$P/0001-tty-serial-add-Qualcomm-EUD-COM-early-console.patch" 2>&1 | tail -1
git am "$P/0002-arm64-dts-qcom-add-realme-samurai-X2-Pro-bring-up-description.patch" 2>&1 | tail -1
git log --oneline -4
timeout 120 git push -u origin samurai-bringup 2>&1 | tail -3
timeout 60 git ls-remote origin samurai-bringup