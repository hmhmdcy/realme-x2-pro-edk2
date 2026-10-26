#!/bin/bash
# Section 25: the EUD real console is built and about to be flashed.  Append the
# handover section, mirror the Linux side, commit the firmware source change and
# push to the fork.
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

if grep -q '^## 25\. ' "$HW"; then echo "section 25 already present"; else
  cat "$W/docs/25-eud-console.md" >> "$HW"
fi
grep -n '^## 25\.\|^### 25\.' "$HW"

cp -f "$HW" "$RK/Platform/Realme/sm8150/HANDOVER-NEXT.md"
mkdir -p "$D"
for x in docs scripts; do cp -r -f "$W/$x" "$D/"; done
chmod +x "$D"/scripts/*.sh 2>/dev/null || true

cd "$RK"
git add Platform/Realme/sm8150/HANDOVER-NEXT.md \
        Platform/Realme/sm8150/linux-port \
        Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c \
        Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m "samurai: console=eud in the cmdline, new DTB, keep_bootcon dropped

The Linux side now carries a real console for the EUD COM FIFO, so the log
channel no longer has to be kept alive with keep_bootcon: the console is named
eud and selected from the command line, listed last so that it becomes the
preferred console (CON_CONSDEV).  The printk core then keeps it registered and
unregisters the early console by itself.

The device tree in the firmware volume gains the COM FIFO node the console
driver binds to, and the kernel command line is now:

  earlycon=eud,mmio,0x88e0000 console=tty0 console=eud loglevel=7
  ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused
  regulator_ignore_unused

Built and verified offline: the uncompressed FVMAIN.Fv carries the new command
line once and no keep_bootcon, and its device tree carries the eud node.  Note
for whoever verifies this next: the shipped .fd is FVMAIN_COMPACT-compressed and
the LoadOptions string is UTF-16, so grepping the .fd for either string always
returns nothing - check FVMAIN.Fv with strings -el instead.

The tty half (/dev/ttyEUD0) is not in this build yet; see section 25.5." 2>/dev/null || true
git log --oneline -2
git show --stat --oneline HEAD | head -8
echo "=== push ==="
bash "$W/scripts/push-fork.sh" 2>&1 | tail -5