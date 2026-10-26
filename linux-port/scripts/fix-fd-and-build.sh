#!/bin/bash
# 修正 FDF 里的 FD 尺寸（CRLF 兼容），然后后台重建固件
set -eu
RK=/home/cy122/edk2-samurai/repo
cd "$RK"

python3 - <<'PY'
import re
p = "Platform/Qualcomm/sm8150/sm8150.fdf"
b = open(p, "rb").read()
b2, n1 = re.subn(rb'(?m)^NumBlocks\s*=\s*0x700(\r?)$', rb'NumBlocks     = 0x1400\1', b)
b2, n2 = re.subn(rb'(?m)^0x00000000\|0x00700000(\r?)$', rb'0x00000000|0x01400000\1', b2)
open(p, "wb").write(b2)
print(f"NumBlocks 替换 {n1} 处, FD 区域替换 {n2} 处")
PY

echo "--- 修改后 ---"
grep -n 'NumBlocks     =\|BlockSize' Platform/Qualcomm/sm8150/sm8150.fdf | head -4
grep -n '^0x00000000|' Platform/Qualcomm/sm8150/sm8150.fdf | head -2
grep -n 'FD_SIZE' configs/sm8150.conf

echo
echo "=== 后台构建固件 ==="
export PATH=$HOME/.local/bin:$PATH
export CPATH=$HOME/edk2-samurai/local/uuid/usr/include
export LIBRARY_PATH=$HOME/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu
nohup ./build.sh -d samurai --toolchain GCC5 > $HOME/edk2-samurai/build-kernel-embed.log 2>&1 &
echo "已启动，日志 $HOME/edk2-samurai/build-kernel-embed.log"
sleep 30
tail -8 $HOME/edk2-samurai/build-kernel-embed.log
