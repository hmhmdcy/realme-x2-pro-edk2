#!/bin/bash
set -e
W="/mnt/e/RealmeX2Pro edk2/linux-port"
RK=/home/cy122/edk2-samurai/repo
D="$RK/Platform/Realme/sm8150/linux-port"

echo "=== ?????? remote ==="
git -C /home/cy122/x2pro-linux/linux remote -v || true
git -C /home/cy122/x2pro-linux/linux log --oneline -3

echo "=== ????????? Linux ???? ==="
ls "$RK/Platform/Realme/sm8150/patches/" 2>/dev/null
ls "$RK/Platform/Realme/sm8150/FdtBlob/samurai/" 2>/dev/null

echo "=== ?? linux-port ??? ==="
mkdir -p "$D"
for x in README.md eud_earlycon.c eud.c docs patches dts scripts refs initramfs; do
  if [ -e "$W/$x" ]; then cp -r -f "$W/$x" "$D/"; else echo "  (skip $x)"; fi
done
cat > "$D/README-MIRROR.md" <<'EOF'
# linux-port (mirror)

This is a read-only mirror of the Windows working copy at
`E:\RealmeX2Pro edk2\linux-port\` (see HANDOVER-NEXT.md section 19.7: the Linux
side of this port used to live only on one disk, with no git history at all).

It holds everything that is small and reproducible:

    README.md        port status and how to build/flash
    docs/            NN-<topic>.md companions for handover sections 19-28,
                     plus the Android DTS reference / EDK2 embed / old-project notes
    dts/             sm8150-samurai.dts (the mainline device tree source)
    patches/         0001 EUD earlycon, 0002 samurai DTS, 0003 EUD real console
    scripts/         build/flash/verify helpers (incl. comlog2.cpp)
    refs/19781/      files cherry-picked from the Android downstream tree
    initramfs/       the diagnostic init script
    eud_earlycon.c   the earlycon driver source (also in patches/0001)
    eud.c            the real-console driver source (also in patches/0003)

Deliberately NOT mirrored: `artifacts/` (incl. the 30 MB kernel Image) and the
full kernel tree (`~/x2pro-linux/linux`, a Linux v7.3-rc6 checkout whose only
local commits are exactly the patches in `patches/`).

To recreate the kernel side from scratch:

    tar xf linux-7.3-rc6.tar.gz && cd linux
    git am /path/to/linux-port/patches/0001-*.patch
    git am /path/to/linux-port/patches/0002-*.patch
    git am /path/to/linux-port/patches/0003-*.patch
    make -s ARCH=arm64 qcom/sm8150-samurai.dtb     # -> artifacts/sm8150-samurai.dtb
    bash linux-port/scripts/build-image.sh         # -> the kernel Image
EOF
du -sh "$D"
find "$D" -type f | wc -l

echo "=== ????? ==="
cd "$RK"
git add Platform/Realme/sm8150/linux-port
git add -f Platform/Realme/sm8150/linux-port/refs/19781   # refs hold Android *.dts files that the top-level *.dts rule would ignore
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m "linux-port: mirror the Linux side of the port into the repo

Section 19.7 flagged this: the kernel patches, the device tree source, the
build scripts and the docs only ever existed in a Windows working directory
(E:\\RealmeX2Pro edk2\\linux-port) with no git history, while the EDK2 repo
only carried the compiled DTB and the handover prose.  One disk failure would
have lost the whole Linux side of this project.

Mirrored: README, docs, dts, patches, scripts, refs/19781, initramfs and the
earlycon and real-console sources.  Not mirrored: the 30 MB kernel Image and the
full kernel tree - both are rebuildable from patches/ as documented in
README-MIRROR.md."
git log --oneline -2
git show --stat --oneline HEAD | head -5
echo "=== push ==="
bash "$W/scripts/push-fork.sh" 2>&1 | tail -5