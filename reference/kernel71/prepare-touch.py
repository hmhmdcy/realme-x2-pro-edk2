from pathlib import Path
import hashlib, json, shutil, subprocess

k=Path('/home/cy122/x2pro-linux/linux')
out=Path('/mnt/e/edk2-samurai-out/kernel71')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
guards={'.config':'439398137656726f4d2abe57011b9e1c42eb21dbc7f1095ddebec2cf23443546',
 'arch/arm64/boot/Image':'d51d1260091d0d568c30b6dc6e673474658259654d63b0e65d5f3baf036145ff',
 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb':'4641207124f1276f00749132d118ba73c3fdeaef24aeac8b2b1df017ef5dea9a',
 'drivers/tty/serial/eud.c':'39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4',
 'drivers/tty/serial/eud_earlycon.c':'34da9936de5de9b36f232be3b8e0a730f9a56a77a6121b283b8e551bb3c65ad9'}
for p,h in guards.items(): assert sha(k/p)==h,p
assert sha(Path('/home/cy122/x2pro-linux/initramfs/init'))=='e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab'
backups={'.config':'config-before','arch/arm64/boot/Image':'Image-before',
 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb':'samurai-before.dtb',
 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts':'samurai-before.dts',
 'drivers/input/rmi4/rmi_i2c.c':'rmi_i2c-before.c'}
for p,n in backups.items():
 assert not (out/n).exists(),n
 shutil.copyfile(k/p,out/n)
(out/'baseline-hashes.json').write_text(json.dumps(guards,indent=2)+'\n')

p=k/'drivers/input/rmi4/rmi_i2c.c'
s=p.read_text()
def replace(old,new):
 global s
 assert s.count(old)==1,old[:120]
 s=s.replace(old,new)
replace('#include <linux/delay.h>','#include <linux/delay.h>\n#include <linux/gpio/consumer.h>')
replace(' * @startup_delay: Milliseconds to pause after powering up the regulators',
 ' * @startup_delay: Milliseconds to pause after power-up and reset release\n * @reset_gpio: Optional active-low hardware reset')
replace('\tu32 startup_delay;','\tu32 startup_delay;\n\tstruct gpio_desc *reset_gpio;')
replace('\tregulator_bulk_disable(ARRAY_SIZE(rmi_i2c->supplies),\n\t\t\t       rmi_i2c->supplies);\n}',
 '\tif (rmi_i2c->reset_gpio)\n\t\tgpiod_set_value_cansleep(rmi_i2c->reset_gpio, 1);\n\n\tregulator_bulk_disable(ARRAY_SIZE(rmi_i2c->supplies),\n\t\t\t       rmi_i2c->supplies);\n}')
replace('static int rmi_i2c_probe(struct i2c_client *client)',
 '''/* Based on Roman Vivchar's 20260912-rmi4-reset-v1 patch. */
static void rmi_i2c_release_reset(struct rmi_i2c_xport *rmi_i2c)
{
	if (rmi_i2c->reset_gpio) {
		usleep_range(10000, 20000);
		gpiod_set_value_cansleep(rmi_i2c->reset_gpio, 0);
		/* Hardware reset restores page zero; force the next page select. */
		rmi_i2c->page = -1;
	}

	msleep(rmi_i2c->startup_delay);
}

static int rmi_i2c_probe(struct i2c_client *client)''')
replace('\terror = regulator_bulk_enable(ARRAY_SIZE(rmi_i2c->supplies),',
 '''	rmi_i2c->reset_gpio = devm_gpiod_get_optional(&client->dev, "reset",
						  GPIOD_OUT_HIGH);
	if (IS_ERR(rmi_i2c->reset_gpio))
		return dev_err_probe(&client->dev, PTR_ERR(rmi_i2c->reset_gpio),
				     "Failed to get reset GPIO\\n");

	error = regulator_bulk_enable(ARRAY_SIZE(rmi_i2c->supplies),''')
assert s.count('\tmsleep(rmi_i2c->startup_delay);')==4
start=s.index('static int rmi_i2c_probe')
s=s[:start]+s[start:].replace('\tmsleep(rmi_i2c->startup_delay);','\trmi_i2c_release_reset(rmi_i2c);')
assert s.count('\tregulator_bulk_disable(ARRAY_SIZE(rmi_i2c->supplies),\n\t\t\t       rmi_i2c->supplies);')==3
start=s.index('static int rmi_i2c_suspend')
s=s[:start]+s[start:].replace('\tregulator_bulk_disable(ARRAY_SIZE(rmi_i2c->supplies),\n\t\t\t       rmi_i2c->supplies);','\trmi_i2c_regulator_bulk_disable(rmi_i2c);')
p.write_text(s)

p=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
s=p.read_text()
needle='\t/*\n\t * The volume keys are PM8150 GPIOs'
assert s.count(needle)==1
s=s.replace(needle,'''\t/* 19781 vendor DTS/common power code: PM8150L GPIO5 high enables VIO. */
	vreg_touch_1p8: regulator-touch-1p8 {
		compatible = "regulator-fixed";
		regulator-name = "touch-vio-1p8";
		regulator-min-microvolt = <1800000>;
		regulator-max-microvolt = <1800000>;
		gpio = <&pm8150l_gpios 5 GPIO_ACTIVE_HIGH>;
		enable-active-high;
		pinctrl-names = "default";
		pinctrl-0 = <&touch_vio_enable_default>;
	};

'''+needle)
s+='''
/* S3706 wiring from this handset's 19781 overlay and saved Android tree. */
&gpi_dma2 {
	status = "okay";
};

&qupv3_id_2 {
	status = "okay";
};

&i2c17 {
	status = "okay";

	touchscreen@20 {
		compatible = "syna,rmi4-i2c";
		reg = <0x20>;
		#address-cells = <1>;
		#size-cells = <0>;
		interrupt-parent = <&tlmm>;
		interrupts = <122 IRQ_TYPE_LEVEL_LOW>;
		reset-gpios = <&tlmm 54 GPIO_ACTIVE_LOW>;
		pinctrl-names = "default";
		pinctrl-0 = <&touch_irq_default &touch_reset_default>;
		vdd-supply = <&vreg_l17a_3p0>;
		vio-supply = <&vreg_touch_1p8>;
		/* Vendor: 10 ms power-to-reset release, 80 ms reset-to-normal. */
		syna,startup-delay-ms = <80>;
		syna,reset-delay-ms = <80>;

		rmi4-f12@12 {
			reg = <0x12>;
			syna,sensor-type = <1>;
			touchscreen-size-x = <1080>;
			touchscreen-size-y = <2400>;
		};
	};
};

&vreg_l17a_3p0 {
	regulator-min-microvolt = <3000000>;
	regulator-max-microvolt = <3000000>;
};

&pm8150l_gpios {
	touch_vio_enable_default: touch-vio-enable-default-state {
		pins = "gpio5";
		function = "normal";
		bias-disable;
		power-source = <0>;
		qcom,drive-strength = <3>;
		drive-push-pull;
	};
};

&tlmm {
	touch_irq_default: touch-irq-default-state {
		pins = "gpio122";
		function = "gpio";
		drive-strength = <8>;
		bias-pull-up;
		input-enable;
	};

	touch_reset_default: touch-reset-default-state {
		pins = "gpio54";
		function = "gpio";
		drive-strength = <8>;
		bias-disable;
	};
};
'''
p.write_text(s)
subprocess.run([str(k/'scripts/config'),'--file',str(k/'.config'),
 '--enable','I2C_QCOM_GENI','--enable','QCOM_GPI_DMA','--enable','RMI4_CORE',
 '--enable','RMI4_I2C','--enable','RMI4_F12','--disable','RMI4_F34'],check=True)
print('Touch DTS/RMI reset patch and builtin configuration applied; baseline saved.')
