#!/bin/bash
# 仓库主 README 加一段指路（主线内核已进固件 + Image 前提）
set -u
RK=/home/cy122/edk2-samurai/repo
cd "$RK"

python3 - <<'PY'
p = "Platform/Realme/sm8150/README.md"
b = open(p, "rb").read()
if b"Mainline Linux" in b and b"LinuxKernel/Image" in b:
    print("已经加过，跳过")
else:
    anchor = b"Host toolchain note: on very new GCC"
    assert anchor in b, "找不到锚点"
    add = (b"**Mainline Linux**: the firmware now embeds a mainline kernel (EFI stub, built-in\r\n"
           b"diagnostic initramfs, EUD earlycon) and boots it as a UEFI application named\r\n"
           b"\"Linux (mainline samurai)\", with a real device tree in `FdtBlob/samurai/`.\r\n"
           b"State and next steps: `HANDOVER-NEXT.md` section 18.\r\n"
           b"\r\n"
           b"`Platform/Realme/sm8150/LinuxKernel/Image` is a build product and is not\r\n"
           b"committed: put it back (or rebuild it with the linux-port scripts) before\r\n"
           b"building, otherwise `./build.sh` fails on the missing file.\r\n"
           b"\r\n"
           b"")
    open(p, "wb").write(b.replace(anchor, add + anchor, 1))
    print("已插入")
PY
sed -n '36,46p' Platform/Realme/sm8150/README.md

git add Platform/Realme/sm8150/README.md
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m 'samurai: point the README at the mainline Linux state

The firmware now carries a mainline kernel and a real device tree; say where
the state lives and warn that LinuxKernel/Image is not committed.'
git log --oneline -2

for i in 1 2 3 4; do
  if timeout 150 git push fork master 2>&1 | tail -3; then break; fi
  sleep 8
done
timeout 60 git ls-remote fork master 2>&1 | head -2
