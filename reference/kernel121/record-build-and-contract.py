from pathlib import Path
import runpy,subprocess,hashlib,json,re
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
root=Path('/home/cy122/pmos-samurai-kernel118');k=root/'camera121/kernel';base=root/'camera120/kernel'
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel121');out=Path('/mnt/e/edk2-samurai-out/kernel121')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base/'arch/arm64/boot/Image')=='0ec2560bdb332ead8a0bea7636f4fd3d80e041f7ac370f71d20e1f80df183bf9'
for name in ['arch/arm64/boot/dts/qcom/sm8150-samurai.dts','arch/arm64/boot/dts/qcom/sm8150.dtsi','drivers/net/ipa/reg/ipa_reg-v4.1.c','drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c','drivers/regulator/qcom-pm8008-regulator.c']:
    assert (k/name).read_bytes()==(base/name).read_bytes()
assert (k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()==(base/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()
assert b'#121 SMP PREEMPT' in subprocess.check_output(['strings',str(k/'vmlinux')])
log=(out/'kernel-full-build.log').read_text();assert 'error:' not in log and 'Error ' not in log
names=['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','drivers/mfd/qcom-pm8008.ko','drivers/regulator/qcom-pm8008-regulator.ko','drivers/media/platform/qcom/camss/qcom-camss.ko','drivers/i2c/busses/i2c-qcom-cci.ko','usr/initramfs_data.cpio']
report=dict(candidate=121,full_image_modules_dtb_build_pass=True,module_count=sum(1 for p in k.rglob('*.ko')),image_and_module_hashes={n:sha(k/n) for n in names},baseline120_preserved=True,board_dts_dtb_unchanged=True,ipa_and_display_fixes_preserved=True,pm8008_regulator_voltage_driver_unchanged=True,not_deployed=True,full_rootfs121_not_generated=True,goal_complete=False)
(ref/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source');path=own/'drivers/regulator/qcom_pm8008-regulator.c';source=path.read_text()
reset=source[source.index('void  pm8008_do_reset(void)'):source.index('void  pm8008_do_reset(void)')+2500]
tokens=['gpio_set_value(g_pm8008_reset_info[1].reset_gpio, 0);','gpio_set_value(g_pm8008_reset_info[0].reset_gpio, 0);','msleep(10);','gpio_set_value(g_pm8008_reset_info[1].reset_gpio, 1);','regmap_write(g_reset_regmap,0x0644,0x01);','gpio_set_value(g_pm8008_reset_info[0].reset_gpio, 1);']
position=0
for token in tokens:position=reset.index(token,position)+len(token)
assert re.search(r'#define\s+MISC_BASE\s+0x900\b',source)
assert re.search(r'#define\s+MISC_CHIP_ENABLE_REG\s+\(MISC_BASE \+ 0x50\)',source)
mtp=(own/'arch/arm64/boot/dts/19781/sm8150-mtp.dtsi').read_text()
block=mtp[mtp.index('pm8008_enable{'):mtp.index('&pm8008_regulators {')]
assert 'pins = "gpio4";' in block and 'pins = "gpio1";' in block and block.count('output-high;')==2
contract=dict(native_source_sha256=sha(path),native_pin_deassert_level_high=True,mainline_GPIOD_OUT_LOW_needs_active_low_for_high=True,stock_property_zero_flags_not_directly_copied=True,native_recovery_sequence_verified=True,recovery_steps=['both_reset_pins_raw_low','10ms_delay','second_chip_raw_high','second_address_register_0x0644_write_0x01','first_chip_raw_high'],cold_boot_address_straps_not_proven=True,first_probed_chip_selects_global_reset_regmap=True,chip_enable_primary_register_hex='0x950',chip_enable_mask_bit=0,chip_enable_not_managed_by_current_mainline_driver=True,inputs_proven=['both_vdd_l1_l2_from_PM8150L_S8_1352000uV'],inputs_unresolved=['vdd_l3_l4','vdd_l5','vdd_l6','vdd_l7'],no_board_pmic_nodes_created=True,no_runtime_reset_or_i2c_writes=True,shared_i2c4_dual_amps_not_disturbed=True)
(ref/'native-pmic-reset-validation.json').write_text(json.dumps(contract,indent=2)+'\n')
print(json.dumps(report));print(json.dumps(contract))
