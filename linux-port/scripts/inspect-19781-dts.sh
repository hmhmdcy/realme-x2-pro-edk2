#!/bin/bash
# 抽取安卓设备树里最关键的几处，评估可参考性
set -u
D=/home/cy122/x2pro-linux/refs/19781/arch/arm64/boot/dts/19781
cd "$D" || { echo "路径不对，找一下:"; find /home/cy122/x2pro-linux/refs/19781 -maxdepth 6 -name 'sm8150-mtp-overlay.dts' 2>/dev/null; exit 1; }

echo "=== 目录概览 ==="
ls | wc -l
ls -la sm8150-mtp-overlay.dts dsi-panel-samsung-sofef03f-m-amoled-dsc-fhd-plus-90fps-cmd.dtsi 2>&1

echo
echo "=== 关键硬件在哪些文件里 ==="
for pat in '19781' 's3706|synaptics' 'gpio-keys|gpio_keys' 'sofef03f' 'vccq2-supply' 'wcn3990' 'mp2650|bq27|oplus_chg' 'sn100|nfc'; do
  echo "--- $pat"
  grep -rl -iE "$pat" . 2>/dev/null | head -5
done

echo
echo "=== sm8150-mtp-overlay.dts 头部 ==="
head -30 sm8150-mtp-overlay.dts

echo
echo "=== 音量键片段 ==="
grep -n -A14 'gpio_keys\|gpio-keys' sm8150-mtp-overlay.dts 2>/dev/null | head -45
echo "=== 面板 / 触控 ==="
grep -n -iE 'sofef03f|panel@|dsi_panel' sm8150-mtp-overlay.dts 2>/dev/null | head -8
grep -n -iE 'touch|s3706|synaptics' sm8150-mtp-overlay.dts 2>/dev/null | head -8
echo "=== UFS / 电源 ==="
grep -n -B2 -A8 'vccq2-supply' sm8150-mtp-overlay.dts 2>/dev/null | head -20
