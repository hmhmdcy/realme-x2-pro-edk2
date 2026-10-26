#!/bin/bash
# 把修好的 Image 换进 EDK2 -> 重建固件 -> 从 FV 里把内核抠出来比对哈希
set -u
LK=/home/cy122/x2pro-linux/linux
RK=/home/cy122/edk2-samurai/repo
LOG=$HOME/edk2-samurai/build-kernel-embed2.log

echo "=== 换 Image ==="
cp -f "$LK/arch/arm64/boot/Image" "$RK/Platform/Realme/sm8150/LinuxKernel/Image"
sha256sum "$RK/Platform/Realme/sm8150/LinuxKernel/Image"

echo
echo "=== 重建固件 ==="
cd "$RK"
export PATH=$HOME/.local/bin:$PATH
export CPATH=$HOME/edk2-samurai/local/uuid/usr/include
export LIBRARY_PATH=$HOME/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu
nohup ./build.sh -d samurai --toolchain GCC5 > "$LOG" 2>&1 &
for i in $(seq 1 70); do
	pgrep -f 'build.sh -d samurai' >/dev/null 2>&1 || { echo "构建结束（第 $i 次检查）"; break; }
	sleep 10
done
tail -3 "$LOG"

echo
echo "=== FD 尺寸 ==="
ls -la workspace/Build/samurai/RELEASE_GCC5/FV/SM8150_UEFI.fd
ls -la boot-samurai.img && sha256sum boot-samurai.img

echo
echo "=== 从 FV 里抠出内核并与 Image 比对 ==="
python3 - "$LK/arch/arm64/boot/Image" "$RK" <<'PY'
import sys, os, hashlib, glob
img = open(sys.argv[1], 'rb').read()
rk = sys.argv[2]
ffs = glob.glob(os.path.join(rk, 'workspace/Build/samurai/RELEASE_GCC5/FV/Ffs/7a3c1e42*/*.ffs'))
if not ffs:
    print("找不到内核的 FFS 文件"); sys.exit(1)
blob = open(ffs[0], 'rb').read()
print("FFS:", os.path.basename(ffs[0]), len(blob), "字节")
i = blob.find(img[:32])
print("内核载荷在 FFS 内偏移:", i)
if i >= 0:
    same = blob[i:i+len(img)] == img
    print("载荷与 Image 完全一致:", same)
    print("FFS 内内核 sha256:", hashlib.sha256(blob[i:i+len(img)]).hexdigest()[:32])
print("Image    sha256:", hashlib.sha256(img).hexdigest()[:32])
PY

echo
echo "=== FVMAIN 里 DTB / 内核标记 ==="
FV=workspace/Build/samurai/RELEASE_GCC5/FV/FVMAIN.Fv
echo "realme,samurai: $(grep -a -c 'realme,samurai' $FV)  xiaomi,cepheus: $(grep -a -c 'xiaomi,cepheus' $FV)"
