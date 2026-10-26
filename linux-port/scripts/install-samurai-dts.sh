#!/bin/bash
# 把 linux-port/dts/sm8150-samurai.dts 装进 v7.3-rc6 主线树，注册 binding，
# 编译 DTB，提交并生成补丁。可重复执行。
set -eu
cd /home/cy122/x2pro-linux/linux
SRC="/mnt/e/RealmeX2Pro edk2/linux-port/dts/sm8150-samurai.dts"
OUT_DIR="/mnt/e/RealmeX2Pro edk2/linux-port/artifacts"
DTS=arch/arm64/boot/dts/qcom/sm8150-samurai.dts

echo "=== 0. 撤掉旧工程的临时改动 ==="
git checkout -- Documentation/devicetree/bindings/arm/qcom.yaml \
                Documentation/devicetree/bindings/vendor-prefixes.yaml \
                arch/arm64/boot/dts/qcom/Makefile 2>/dev/null || true
rm -f arch/arm64/boot/dts/qcom/sm8150-realme-x2pro.dts \
      arch/arm64/boot/dts/qcom/sm8150-realme-x2pro.dtb
git status --short

echo "=== 1. 安装 DTS ==="
cp "$SRC" "$DTS"

echo "=== 2. Makefile ==="
if ! grep -q 'sm8150-samurai.dtb' arch/arm64/boot/dts/qcom/Makefile; then
	cat >> arch/arm64/boot/dts/qcom/Makefile <<'EOF'
dtb-$(CONFIG_ARCH_QCOM) += sm8150-samurai.dtb
EOF
fi
tail -3 arch/arm64/boot/dts/qcom/Makefile

echo "=== 3. qcom.yaml binding ==="
if ! grep -q 'realme,samurai' Documentation/devicetree/bindings/arm/qcom.yaml; then
	sed -i 's|^              - qcom,sm8150-mtp$|              - qcom,sm8150-mtp\n              - realme,samurai|' \
		Documentation/devicetree/bindings/arm/qcom.yaml
fi
grep -n -B2 -A3 'realme,samurai' Documentation/devicetree/bindings/arm/qcom.yaml

echo "=== 4. vendor-prefixes.yaml ==="
if ! grep -q '"\^realme,\.\*"' Documentation/devicetree/bindings/vendor-prefixes.yaml; then
	awk '/^  "\^realtek,\.\*":$/ && !done {
		print "  \"^realme,.*\":";
		print "    description: Realme";
		done = 1
	}
	{ print }' Documentation/devicetree/bindings/vendor-prefixes.yaml > /tmp/vp.yaml
	mv /tmp/vp.yaml Documentation/devicetree/bindings/vendor-prefixes.yaml
fi
grep -n -A1 '"\^realme' Documentation/devicetree/bindings/vendor-prefixes.yaml

echo "=== 5. 编译 DTB ==="
make -s ARCH=arm64 qcom/sm8150-samurai.dtb 2>&1 | tail -20
echo "MAKE_EXIT=${PIPESTATUS[0]}"
ls -la arch/arm64/boot/dts/qcom/sm8150-samurai.dtb
sha256sum arch/arm64/boot/dts/qcom/sm8150-samurai.dtb
mkdir -p "$OUT_DIR"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$OUT_DIR/sm8150-samurai.dtb"

echo "=== 6. 提交 ==="
git add "$DTS" arch/arm64/boot/dts/qcom/Makefile \
	Documentation/devicetree/bindings/arm/qcom.yaml \
	Documentation/devicetree/bindings/vendor-prefixes.yaml
git -c user.name=cy122 -c user.email=cy122@localhost commit -q -m 'arm64: dts: qcom: add realme samurai (X2 Pro) bring-up description

The realme X2 Pro is an SM8150-AC handset whose stock base DTB is an MTP
derivative (oppo,dtsi_no 19781).  Take the MTP description and correct the
board facts against the device firmware itself:

  - the whole remote-processor carve-out area is moved up by roughly
    0x8D400000 and the 0xA0000000 firmware region has no MTP counterpart;
  - tz_mem spans 0x7500000 instead of 0x3900000, and rmtfs_mem does not
    exist on this board;
  - the volume keys are PM8150 GPIO 6/7 rather than pon_resin;
  - ramoops lives at 0xb7e00000 with a useful geometry for bring-up logs.

GPU, WiFi and every remoteproc stay disabled until they can be validated.
The vendor ABL properties (qcom,msm-id / qcom,board-id / oppo,dtsi_no) are
kept because the stock boot chain matches on them.

Signed-off-by: cy122 <cy122@localhost>' && git log --oneline -3
git format-patch -1 -o /home/cy122/x2pro-linux/patches
echo DONE
