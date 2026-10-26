#!/bin/bash
# 把 Android 设备树里对主线有用的文件挑出来，复制回 Windows 工作区，并抽取关键事实。
set -u
SRC=/home/cy122/x2pro-linux/refs/19781/arch/arm64/boot/dts/19781
DST="/mnt/e/RealmeX2Pro edk2/linux-port/refs/19781"
LK=/home/cy122/x2pro-linux/linux

mkdir -p "$DST"
for f in sm8150-mtp.dtsi sm8150-mtp-overlay.dts sm8150-v2.dts sm8150.dts Makefile \
         sm8150-sde-display.dtsi sm8150-pinctrl.dtsi sm8150-qupv3.dtsi \
         dsi-panel-samsung-sofef03f-m-amoled-dsc-fhd-plus-90fps-cmd.dtsi; do
  [ -f "$SRC/$f" ] && cp -f "$SRC/$f" "$DST/" && echo "copied $f"
done
du -sh "$DST"
ls -la "$DST"

echo
echo "=== 触控节点全文（916-1000 行）==="
sed -n '916,1000p' "$SRC/sm8150-mtp.dtsi"

echo
echo "=== 主线里 i2c@c80000 的标签（用于把 qupv3_se17_i2c 映射到主线）==="
grep -n -B6 'i2c@c80000' "$LK/arch/arm64/boot/dts/qcom/sm8150.dtsi" | grep -E '^\s*[0-9]+[:-]\s*(i2c|qupv3|geniqup|spi)' | head -10

echo
echo "=== 安卓源里充电/电量/传感器/NFC 的节点名 ==="
grep -nE '^\s*[a-z0-9_]+@?[0-9a-fx]*\s*\{' "$SRC/sm8150-mtp.dtsi" | grep -iE 'charg|batt|bq2|mp2650|gauge|nfc|sn100|sensor|aw87|tfa98|nau|akm|stk|abov' | head -20

echo
echo "=== 面板 dtsi 头部（时序/初始化样本）==="
head -45 "$SRC/dsi-panel-samsung-sofef03f-m-amoled-dsc-fhd-plus-90fps-cmd.dtsi"
