#!/bin/bash
cd /home/cy122/x2pro-linux/upstream || exit 1
git config user.name  cy122
git config user.email cy122@localhost
git config --local http.proxy ""
git config --local https.proxy ""
P="/mnt/e/RealmeX2Pro edk2/linux-port/patches"
echo "=== git am ==="
timeout 60 git am "$P/0001-tty-serial-add-Qualcomm-EUD-COM-early-console.patch" 2>&1 | tail -2
timeout 60 git am "$P/0002-arm64-dts-qcom-add-realme-samurai-X2-Pro-bring-up-description.patch" 2>&1 | tail -2
echo "=== log ==="
git log --oneline -3
echo "=== ?????????? ==="
git show --stat --format='%h %an <%ae> %ad%n%s' HEAD~1 | head -6
git show --stat --format='%h %an <%ae> %ad%n%s' HEAD | head -8
echo "=== push $(date +%T) ==="
timeout 150 git push -u origin samurai-bringup 2>&1 | tail -4
echo "=== ???? ==="
timeout 60 git ls-remote origin samurai-bringup