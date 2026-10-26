from pathlib import Path
import json
out = Path('/mnt/e/edk2-samurai-out/kernel76/charging-research')
tasks = [
 ['oppo-ace','arch/arm64/boot/dts','tree'],
 ['oppo-ace','drivers/power/oppo/charger_ic/oppo_mp2650.c','raw'],
 ['oppo-ace','drivers/power/oppo/gauge_ic/oppo_bq27541.c','raw'],
 ['oppo-ace','drivers/power/oppo/oppo_charger.c','raw'],
 ['oneplus','arch/arm64/boot/dts','tree'],
 ['oneplus','drivers/power','tree'],
 ['oneplus','drivers/power/supply/qcom/qpnp-smb5.c','raw'],
 ['mainline','drivers/power/supply','tree'],
 ['mainline','drivers/power/supply/bq27xxx_battery.c','raw'],
 ['mainline','Documentation/devicetree/bindings/power/supply/bq27xxx.yaml','raw'],
]
tasks2 = [
 ['oppo-ace','msm-4.14/arch/arm64/boot/dts','tree'],
 ['oppo-ace','msm-4.14/drivers/power/oppo/charger_ic/oppo_mp2650.c','raw'],
 ['oppo-ace','msm-4.14/drivers/power/oppo/gauge_ic/oppo_bq27541.c','raw'],
 ['oppo-ace','msm-4.14/drivers/power/oppo/oppo_charger.c','raw'],
 ['oneplus','arch/arm64/boot/dts/qcom','tree'],
 ['oneplus','drivers/power/supply','tree'],
 ['mainline','arch/arm64/boot/dts/qcom/sm8150-oneplus-guacamole.dts','raw'],
 ['mainline','arch/arm64/boot/dts/qcom/sm8150-oneplus-common.dtsi','raw'],
 ['mainline','drivers/power/supply/Kconfig','raw'],
 ['mainline','drivers/power/supply/Makefile','raw'],
]
(out/'source-tasks2.json').write_text(json.dumps(tasks2,indent=2)+'\n')
tasks3 = [
 ['oppo-ace','msm-4.14/arch/arm64/boot/dts/19081/sm8150-mtp.dtsi','raw'],
 ['oppo-ace','msm-4.14/arch/arm64/boot/dts/19081/pm8150b.dtsi','raw'],
 ['oppo-ace','msm-4.14/arch/arm64/boot/dts/19081','tree'],
 ['oppo-ace','msm-4.14/drivers/power/oppo/charger_ic/oppo_mp2650.h','raw'],
 ['oppo-ace','msm-4.14/Makefile','raw'],
 ['oneplus','arch/arm64/boot/dts/qcom/sm8150-mtp.dtsi','raw'],
 ['oneplus','arch/arm64/boot/dts/qcom/pm8150b.dtsi','raw'],
 ['oneplus','Makefile','raw'],
 ['mainline','Makefile','raw'],
]
(out/'source-tasks3.json').write_text(json.dumps(tasks3,indent=2)+'\n')
tasks4 = [
 ['oneplus','arch/arm64/boot/dts/qcom/guacamole.dtsi','raw'],
 ['oneplus','arch/arm64/boot/dts/qcom/guacamole_sm8150.dtsi','raw'],
 ['oneplus','arch/arm64/boot/dts/qcom/guacamole_pvt.dtsi','raw'],
 ['mainline','drivers/power/supply/qcom_smbx.c','raw'],
 ['mainline','Documentation/devicetree/bindings/power/supply/qcom,pmi8998-charger.yaml','raw'],
]
(out/'source-tasks4.json').write_text(json.dumps(tasks4,indent=2)+'\n')
(out/'source-tasks.json').write_text(json.dumps(tasks,indent=2)+'\n')
