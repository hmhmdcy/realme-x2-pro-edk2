"""Describe verified sensor wiring using the existing common PM8008 providers."""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent;W=Path('/home/cy122/x2pro-linux/camera270-kernel')
down=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/arch/arm64/boot/dts/19781/sm8150-camera-sensor-mtp.dtsi')
raw=down.read_text();clean=re.sub(r'/\*.*?\*/|//[^\n]*','',raw,flags=re.S)
blocks=[]
for m in re.finditer(r'qcom,cam-sensor@3\s*\{',clean):
 start=m.end();depth=1;i=start
 while depth:
  if clean[i]=='{':depth+=1
  elif clean[i]=='}':depth-=1
  i+=1
 blocks.append(clean[start:i-1])
found=[b for b in blocks if 'cam_vana-supply = <&L6P>' in b and 'cam_vdig-supply = <&L2P>' in b]
assert len(found)==1;node=found[0]
for pattern in [r'csiphy-sd-index\s*=\s*<3>',r'cci-device\s*=\s*<1>',r'cci-master\s*=\s*<0>',
                r'CAM_CC_MCLK3_CLK',r'<&tlmm\s+16\s+0>',r'<&tlmm\s+23\s+0>',r'cam_vio-supply\s*=\s*<&pm8150l_l1>']:
 assert re.search(pattern,node),pattern
xml=next(Path('/mnt/e/edk2-samurai-out/kernel239/s5k3m5-b-xml-private').rglob('sensorDriverData.xml'))
root=ET.parse(xml).getroot();slave=root.find('slaveInfo');assert slave is not None
scalar={e.tag:e.text.strip() for e in slave if e.text and e.text.strip() and not list(e)}
assert int(scalar['slaveAddress'],0)==0x5a,scalar
power={name:[{e.tag:e.text.strip() for e in row if e.text and e.text.strip()} for row in slave.find(name)] for name in ['powerUpSequence','powerDownSequence']}
assert any(row.get('configType')=='MCLK' and int(row.get('configValue','0'))==19200000 for row in power['powerUpSequence'])
text='''// SPDX-License-Identifier: BSD-3-Clause
/* RMX1931 telephoto: own board19781 wiring and independently decoded mode3. */
&cam_pmic_p {
	regulators {
		cam_tele_vdig: ldo2 {
			regulator-name = "cam-tele-vdig";
			regulator-min-microvolt = <1050000>;
			regulator-max-microvolt = <1056000>;
			regulator-enable-ramp-delay = <1000>;
		};
		cam_tele_vana: ldo6 {
			regulator-name = "cam-tele-vana";
			regulator-min-microvolt = <2800000>;
			regulator-max-microvolt = <2800000>;
			regulator-enable-ramp-delay = <1000>;
		};
	};
};

&tlmm {
	cam_tele_mclk_active: camera-tele-mclk-active-state {
		pins = "gpio16";
		function = "cam_mclk";
		drive-strength = <2>;
		bias-disable;
	};
	cam_tele_mclk_sleep: camera-tele-mclk-sleep-state {
		pins = "gpio16";
		function = "gpio";
		drive-strength = <2>;
		bias-pull-down;
		input-enable;
	};
	cam_tele_reset: camera-tele-reset-state {
		pins = "gpio23";
		function = "gpio";
		drive-strength = <2>;
		bias-pull-down;
	};
};

&cci1_i2c0 {
	status = "okay";
	cam_tele: camera@2d {
		compatible = "samsung,s5k3m5";
		reg = <0x2d>;
		orientation = <1>;
		power-domains = <&camcc TITAN_TOP_GDSC>;
		vdda-supply = <&cam_tele_vana>;
		vddd-supply = <&cam_tele_vdig>;
		vddio-supply = <&vreg_l1c_1p8>;
		clocks = <&camcc CAM_CC_MCLK3_CLK>;
		assigned-clocks = <&camcc CAM_CC_MCLK3_CLK>;
		assigned-clock-rates = <19200000>;
		reset-gpios = <&tlmm 23 GPIO_ACTIVE_LOW>;
		pinctrl-names = "default", "sleep";
		pinctrl-0 = <&cam_tele_mclk_active &cam_tele_reset>;
		pinctrl-1 = <&cam_tele_mclk_sleep &cam_tele_reset>;
		port {
			cam_tele_ep: endpoint {
				data-lanes = <1 2 3 4>;
				/* OEM OP-PLL candidate; physical timing is not yet verified. */
				link-frequencies = /bits/ 64 <723200000>;
				remote-endpoint = <&cam_tele_csiphy3_ep>;
			};
		};
	};
};

&camss {
	ports {
		port@3 {
			reg = <3>;
			cam_tele_csiphy3_ep: endpoint {
				clock-lanes = <7>;
				data-lanes = <0 1 2 3>;
				bus-type = <MEDIA_BUS_TYPE_CSI2_DPHY>;
				remote-endpoint = <&cam_tele_ep>;
			};
		};
	};
};
'''
board=W/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
assert '#include "s5k3m5-samurai.dtsi"' not in board.read_text()
board.write_text(board.read_text()+'\n#include "s5k3m5-samurai.dtsi"\n')
(W/'arch/arm64/boot/dts/qcom/s5k3m5-samurai.dtsi').write_text(text)
(R/'s5k3m5-samurai.dtsi').write_text(text)
report=dict(stage=270,downstream_source_sha256=hashlib.sha256(raw.encode()).hexdigest(),
 standard_compatible='samsung,s5k3m5',cci_controller=1,cci_master=0,sensor_address_7bit='0x2d',
 reset_gpio=23,mclk_gpio=16,mclk_id=3,mclk_hz=19200000,csiphy=3,
 analog_supply='P L6 2.8V',digital_supply='P L2 1.056V',io_supply='PM8150L L1 1.8V',
 separate_actuator_not_powered=True,no_lab_provider=True,no_runtime_OF_mutation=True,
 input_voltage_for_unknown_pldo_not_invented=True,board_dtsi_sha256=hashlib.sha256(text.encode()).hexdigest(),
 link_frequency_unmeasured=True,phone_unchanged=True)
(R/'telephoto-board-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
