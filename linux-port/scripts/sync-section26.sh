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
RW="/mnt/e/RealmeX2Pro edk2/README.md"
RK=/home/cy122/edk2-samurai/repo
D="$RK/Platform/Realme/sm8150/linux-port"

if grep -q '^## 26\. ' "$HW"; then echo "section 26 already present"; else
  cat "$W/docs/26-real-machine-review.md" >> "$HW"
fi
grep -n '^## 26\.' "$HW"

MARK="Status update 2026-10-07"
if grep -qF "$MARK" "$RW"; then echo "README already updated"; else
cat >> "$RW" <<'EOF'

## Status update 2026-10-07 (EUD console works; two real bugs found)

* console=eud (a real nbcon console for the EUD COM FIFO) is verified on hardware:
  with keep_bootcon removed the log now continues past the 1.2 s mark where it used
  to die.  Firmware cmdline: earlycon=eud,mmio,0x88e0000 console=tty0 console=eud ...
  and the DTB in the firmware volume carries the serial@88e0000 node for it.
* Two independent bugs kept the kernel from reaching userspace:
  1. 7.3 reads the RPMh regulator voltage back at boot.  On SM8150 the AOSS never
     answers: the read occupies an ACTIVE TCS and blocks every later write (10 s
     timeout = RPMH_TIMEOUT_MS, then "failed to read VOLTAGE ret = -110", rpmh_write
     WARNs, dwc3 -ETIMEDOUT).  Worked around in drivers/soc/qcom/rpmh.c: no read
     commands on qcom,sm8150 / qcom,sc8180x.
  2. The built-in initramfs carried 305 absolute symlinks into the host tree
     (busybox --install -s with an absolute path), so /init could not exec:
     "Kernel panic - not syncing: No working init found" -> panic=15 reboot loop.
     Symlinks are relative now and the cpio is rebuilt.
* Test image: Image-rmx1931-samurai-initfix (RPMh + initramfs fix).
  Full story and hashes: HANDOVER-NEXT.md section 26.
EOF
echo "README updated"
fi

cp -f "$HW" "$RK/Platform/Realme/sm8150/HANDOVER-NEXT.md"
cp -f "$RW" "$RK/Platform/Realme/sm8150/README.md"
mkdir -p "$D"
for x in docs scripts; do cp -r -f "$W/$x" "$D/"; done
chmod +x "$D"/scripts/*.sh 2>/dev/null || true

cd "$RK"
git add Platform/Realme/sm8150/HANDOVER-NEXT.md Platform/Realme/sm8150/README.md Platform/Realme/sm8150/linux-port
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -F - <<'MSG'
docs: section 26 - the EUD console works, and the two bugs that kept us out of userspace

The console itself is done and verified: with keep_bootcon removed the log
continues past the point where the early console is unregistered, which is
only possible because the real console registered and took over.

Behind it were two independent bugs that had nothing to do with the port:

  - Linux 7.3 reads RPMh regulator voltages back at boot.  On SM8150 the AOSS
    never answers such a read: the request occupies an ACTIVE TCS and blocks
    every following write, so the boot stalls for RPMH_TIMEOUT_MS (10 s) and
    then everything that needs a write fails - regulators, RPMh clocks, dwc3.
    The fix skips read commands entirely on qcom,sm8150 and qcom,sc8180x, the
    same way the upstream thread proposes.

  - The built-in initramfs contained 305 symlinks pointing at the host build
    tree (busybox --install -s was given an absolute directory), so inside the
    initramfs /bin/sh and friends dangled, /init could not exec and the kernel
    panicked with "No working init found" - which panic=15 turned into a reboot
    loop that looked like the firmware hanging.

Both are fixed and the resulting image is built; it still has to be written
into the logdump FAT before it can be tested.
MSG
git log --oneline -2
echo "=== push ==="
bash "$W/scripts/push-fork.sh" 2>&1 | tail -5