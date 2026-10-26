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
if grep -q '^## 20\. ' "$HW"; then echo "already present"; else cat "$W/docs/20-linux-boot.md" >> "$HW"; fi
cp -f "$HW" "$RK/Platform/Realme/sm8150/HANDOVER-NEXT.md"
grep -n '^## 20\.\|^### 20\.' "$HW"
cd "$RK"
git add Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c Platform/Realme/sm8150/HANDOVER-NEXT.md
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m "samurai: boot the mainline kernel from a FAT partition - it runs on hardware

The kernel cannot live in the firmware volume: FFS files top out at 16 MiB (24
bit size field) so the 30 MB image was silently truncated and corrupted FVMAIN,
and the 62 MB uncompressed volume did not fit the 66 MiB PrePi memory pool, so
the DXE core was never loaded (the screen stopped at LoadDxeCoreFromFv In).

The kernel now lives on the FAT16 partition named logdump (64 MiB, verified
all-zero, not mounted by Android, not written by the factory package, backed up)
and PlatformBm.c scans every file system for a \\Image that really starts with
the PE signature, registers it and starts it right after EUD is enabled.

Verified on hardware: earlycon output reaches the host over EUD
(Linux version / Machine model: Realme / PSCI v1.1 / GIC / RCU ...).

Also add keep_bootcon so the EUD boot console is not torn down when the real
console registers." 2>/dev/null || true
git log --oneline -2
echo "=== push ==="
bash "$W/scripts/push-fork.sh" 2>&1 | tail -6