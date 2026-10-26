#!/bin/bash
# 拉取安卓侧设备树/内核设备树作为参考。网络不稳，每个仓库独立容错。
set -u
REF=/home/cy122/x2pro-linux/refs
mkdir -p "$REF"
cd "$REF"

clone() {  # name url [branch] [sparse paths...]
  local name="$1" url="$2" br="${3:-}" ; shift 3 2>/dev/null || shift 2
  if [ -d "$name/.git" ]; then echo "[skip] $name 已存在"; return 0; fi
  echo "=== clone $name  ($url ${br:+-b $br}) ==="
  if [ -n "$br" ]; then
    git clone --depth 1 --filter=blob:none --no-checkout -b "$br" "$url" "$name" 2>&1 | tail -3
  else
    git clone --depth 1 --filter=blob:none --no-checkout "$url" "$name" 2>&1 | tail -3
  fi
  if [ -d "$name/.git" ] && [ "$#" -gt 0 ]; then
    git -C "$name" sparse-checkout init --cone 2>&1 | tail -1
    git -C "$name" sparse-checkout set "$@" 2>&1 | tail -2
    git -C "$name" checkout 2>&1 | tail -2
  fi
}

clone device-samurai   https://github.com/crdroidandroid/android_device_realme_samurai
clone device-samurai-n https://github.com/nayem8854/android_device_realme_samurai
clone device-sm8150    https://github.com/realme-sm8150-development/android_device_realme_sm8150-common lineage-18.1
clone twrp-rmx1931     https://github.com/HyperTeam/twrp_device_realme_RMX1931

echo
echo "=== 内核设备树（稀疏拉取 arch/arm64/boot/dts/qcom）==="
clone kernel-realme-oss https://github.com/realme-kernel-opensource/realme_6pro_7pro_8pro_X2-AndroidR-kernel-source "" arch/arm64/boot/dts/qcom arch/arm64/configs
if [ ! -d kernel-realme-oss/arch ]; then
  echo "[fallback] alextrack2013/android_kernel_realme_sm8150"
  clone kernel-alextrack https://github.com/alextrack2013/android_kernel_realme_sm8150 "" arch/arm64/boot/dts/qcom
fi

echo
echo "=== 结果 ==="
du -sh "$REF"/* 2>/dev/null
echo "--- 各仓库里与 samurai/19781 有关的设备树文件 ---"
for d in "$REF"/*/; do
  echo "## $(basename "$d")"
  find "$d" -path '*/.git' -prune -o -type f -print 2>/dev/null \
    | grep -iE 'samurai|19781|sm8150|msmnile' | head -25
done
