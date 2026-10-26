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
if grep -q '^## 21\. ' "$HW"; then echo "already present"; else cat "$W/docs/21-eud-framing.md" >> "$HW"; fi
cp -f "$HW" "$RK/Platform/Realme/sm8150/HANDOVER-NEXT.md"
grep -n '^## 21\.\|^### 21\.' "$HW"
cp -f "$W/comlog2.cpp" "$RK/Platform/Realme/sm8150/" 2>/dev/null || cp -f "/mnt/e/eud-host/comlog2.cpp" "$RK/Platform/Realme/sm8150/EUD-comlog2.cpp"
cp -f "/mnt/e/eud-host/comlog2.cpp" "$W/scripts/comlog2.cpp" 2>/dev/null || true
cd "$RK"
git add Platform/Realme/sm8150/HANDOVER-NEXT.md Platform/Realme/sm8150/EUD-comlog2.cpp 2>/dev/null
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m "docs: the EUD log garble comes from the kernel side, not the host parser

eud_write() pushes 8 register writes per frame (id, length, six data bytes)
into a FIFO that is only about seven bytes deep, and only waits for TX ready
after the whole frame.  The last byte or two is dropped, the next frame's 0x90
is eaten as data and every frame boundary after that is wrong - which is why
the capture came out as interleaved fragments and why no host-side reassembly
could have fixed it.

Record the fix (per-register flow control, four data bytes per frame), the new
comlog2 host logger with aggressive resync and a raw dump, and how to verify."
git log --oneline -2
echo "=== push ==="
bash "$W/scripts/push-fork.sh" 2>&1 | tail -5