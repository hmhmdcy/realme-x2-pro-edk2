from pathlib import Path
import difflib, hashlib, json, subprocess

kernel = Path('/home/cy122/x2pro-linux/linux')
root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel99'
out = Path('/mnt/e/edk2-samurai-out/kernel99')
sha = lambda data: hashlib.sha256(data).hexdigest()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=kernel).decode().strip() == 'e42788eafb0bb9d8dfce319c71ca54c5207b2295'
assert not (out/'dts-before').exists()
source = (ref/'aw8697-samurai.c').read_bytes()
target = kernel/'drivers/input/misc/aw8697-samurai.c'
assert not target.exists()
dts_path = kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
dts_before = dts_path.read_text()
assert '&i2c7' not in dts_before
(out/'workspace-dts-mirror-before').write_bytes((root/'linux-port/dts/sm8150-samurai.dts').read_bytes())
(out/'kernel-source-before.patch').write_bytes(subprocess.check_output(['git','diff'],cwd=kernel))
for name, path in (
    ('dts-before', dts_path), ('config-before', kernel/'.config'),
    ('dtb-before', kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'),
    ('Image-before', kernel/'arch/arm64/boot/Image'),
    ('cpio-before', kernel/'usr/initramfs_data.cpio'),
    ('input-Kconfig-before', kernel/'drivers/input/misc/Kconfig'),
    ('input-Makefile-before', kernel/'drivers/input/misc/Makefile'),
):
    (out/name).write_bytes(path.read_bytes())
config = (out/'config-before').read_text()
assert 'CONFIG_REGMAP_I2C=y\n' in config and 'CONFIG_INPUT_FF_MEMLESS=m\n' in config
target.write_bytes(source)
kconfig = (out/'input-Kconfig-before').read_text()
assert 'config INPUT_SAMURAI_AW8697' not in kconfig
addition = '''config INPUT_SAMURAI_AW8697
	tristate "Realme X2 Pro AW8697 haptics candidate"
	depends on I2C && GPIOLIB && OF
	select REGMAP_I2C
	select INPUT_FF_MEMLESS
	help
	  Bounded continuous-mode force feedback for the RMX1931 AW8697.
	  Uses the same-handset 19781 170 Hz profile without waveform firmware.

'''
assert kconfig.count('config INPUT_AW86927\n') == 1
(kernel/'drivers/input/misc/Kconfig').write_text(kconfig.replace('config INPUT_AW86927\n', addition+'config INPUT_AW86927\n'))
makefile = (out/'input-Makefile-before').read_text()
line = 'obj-$(CONFIG_INPUT_SAMURAI_AW8697) += aw8697-samurai.o\n'
(kernel/'drivers/input/misc/Makefile').write_text(makefile+line)
dts_after = dts_before + '''
/* 19781 same-handset wiring; no reset-line sharing with other devices. */
&i2c7 {
	status = "okay";
	clock-frequency = <400000>;

	haptics@5a {
		compatible = "realme,samurai-aw8697", "awinic,aw8697";
		reg = <0x5a>;
		reset-gpios = <&tlmm 116 GPIO_ACTIVE_LOW>;
		interrupt-parent = <&tlmm>;
		interrupts = <24 IRQ_TYPE_EDGE_FALLING>;
		pinctrl-names = "default";
		pinctrl-0 = <&haptics_reset_default &haptics_irq_default>;
	};
};

&tlmm {
	haptics_reset_default: haptics-reset-default-state {
		pins = "gpio116";
		function = "gpio";
		drive-strength = <2>;
		bias-disable;
		output-low;
	};

	haptics_irq_default: haptics-irq-default-state {
		pins = "gpio24";
		function = "gpio";
		drive-strength = <2>;
		bias-disable;
		input-enable;
	};
};
'''
dts_path.write_text(dts_after)
(ref/'sm8150-samurai.dts.after').write_text(dts_after)
(ref/'samurai-haptics-dts.patch').write_text(''.join(difflib.unified_diff(dts_before.splitlines(True),dts_after.splitlines(True),fromfile='a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts',tofile='b/arch/arm64/boot/dts/qcom/sm8150-samurai.dts')))
subprocess.run(['scripts/config','--enable','INPUT_SAMURAI_AW8697','--enable','INPUT_FF_MEMLESS'],cwd=kernel,check=True)
(out/'driver-preparation.json').write_text(json.dumps(dict(driver_source_sha256=sha(source),
    same_handset_dts_wiring=dict(i2c_controller='89c000',address='0x5a',reset_gpio=116,irq_gpio=24),
    profile_hz=170,drive_ceiling=52,normal_overdrive_ceiling=125,
    waveform_firmware_required=False,nv_otp_calibration_writes=False,
    hardware_tested=False,goal_complete=False),indent=2)+'\n')
print('HAPTICS_SOURCE_PREPARED')
