#!/bin/bash
# 从安卓板级文件里抽出对主线有用的硬件事实
set -u
D=/home/cy122/x2pro-linux/refs/19781/arch/arm64/boot/dts/19781
cd "$D" || exit 1

echo "=== 文件规模 ==="
wc -l sm8150-mtp.dtsi sm8150-mtp-overlay.dts sm8150-v2.dts sm8150.dts \
      dsi-panel-samsung-sofef03f-m-amoled-dsc-fhd-plus-90fps-cmd.dtsi 2>/dev/null

echo
echo "=== 机型标识（dtsi_no / 项目号）==="
grep -n -B2 -A6 '19781' sm8150-mtp.dtsi | head -30

echo
echo "=== 音量键 gpio-keys ==="
grep -n -B4 -A40 'gpio_keys' sm8150-mtp.dtsi | head -70

echo
echo "=== UFS 供电 ==="
grep -n -B3 -A14 'ufshc\|ufs_mem' sm8150-mtp.dtsi | grep -iE 'ufshc|ufs_mem|vcc|reset-gpio|status' | head -25

echo
echo "=== 触控（s3706/synaptics）==="
grep -n -B6 -A30 -iE 's3706|synaptics' sm8150-mtp.dtsi | head -60
