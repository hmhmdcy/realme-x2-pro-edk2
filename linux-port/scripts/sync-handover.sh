#!/bin/bash
# 把最新的 HANDOVER-NEXT.md 同步进仓库并提交（仓库里那份还停在 §7）
set -u
RK=/home/cy122/edk2-samurai/repo
SRC="/mnt/e/RealmeX2Pro edk2/HANDOVER-NEXT.md"
DST="$RK/Platform/Realme/sm8150/HANDOVER-NEXT.md"
cd "$RK"

echo "=== 同步前 ==="
wc -l "$DST"; sha256sum "$DST" | cut -c1-16

cp -f "$SRC" "$DST"

echo "=== 同步后 ==="
wc -l "$DST"; sha256sum "$DST" | cut -c1-16
grep -c '^## ' "$DST"
tail -3 "$DST"

echo
echo "=== 提交 ==="
git add Platform/Realme/sm8150/HANDOVER-NEXT.md
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m 'docs: handover for the mainline Linux bring-up

The repository copy still stopped at the EDK2-only state (section 7) while the
local one had grown to section 17.  Sync them and add section 18: the mainline
kernel is now embedded in the firmware volume as a UEFI application, the wrong
(cepheus) device tree has been replaced by a real samurai one, and the next
session only has to flash boot-samurai-linux.img and read the EUD log.

Also record what must not be re-derived: PcdDefaultDtPref is TRUE so
DtPlatformDxe installs FdtBlob as the FDT configuration table, the FD grew to
20 MiB but still sits inside conventional memory at 0xCE000000, the earlycon
framework only maps one 4 KiB page (so cross-page registers need their own
ioremapping), and where the Android device tree source (project 19781) lives.'
git log --oneline -3
git status --short

echo
echo "=== 远端情况（push 只是尝试，失败不影响）==="
git remote -v
timeout 120 git push fork master 2>&1 | tail -5 || echo "push 失败/超时（网络不稳，下次重试）"
