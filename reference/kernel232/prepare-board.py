"""Keep unknown VINs absent; produce conservative and explicit experimental DTs."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel232')
old=(P.parent/'kernel219/timing-source/sm8150-samurai.dts').read_text()
assert hashlib.sha256(old.encode()).hexdigest()==json.loads((R.parent/'kernel219/timing-candidate-source-validation.json').read_text())['board_sha256']
hog='''&pm8150l_gpios {
	/* The unused rear PMIC shares the factory address with the front PMIC. */
	cam_rear_reset_hog: camera-rear-reset-hog {
		gpio-hog;
		gpios = <1 GPIO_ACTIVE_HIGH>;
		output-low;
		line-name = "camera-rear-reset";
	};
};'''
provider='''/ {
	cam_pmic_resets: camera-pmic-resets {
		compatible = "realme,rmx1931-pm8008-resets";
		#reset-cells = <1>;
		p-reset-gpios = <&pm8150l_gpios 1 GPIO_ACTIVE_LOW>;
		q-reset-gpios = <&pm8150l_gpios 4 GPIO_ACTIVE_LOW>;
	};
};'''
assert old.count(hog)==1
new=old.replace(hog,provider,1)
needle='''&i2c4 {
	pmic@4 {'''
replacement='''&i2c4 {
	/* VINs are incomplete: product configuration keeps P disabled. */
	cam_pmic_p: pmic@8 {
		compatible = "qcom,pm8008";
		reg = <8>;
		resets = <&cam_pmic_resets 0>;
		qcom,address-setup-supplier = <&cam_pmic_q>;
		status = "disabled";
	};

	cam_pmic_q: pmic@4 {'''
assert new.count(needle)==1;new=new.replace(needle,replacement,1)
needle='\t\treset-gpios = <&pm8150l_gpios 4 GPIO_ACTIVE_LOW>;'
assert new.count(needle)==1;new=new.replace(needle,'\t\tresets = <&cam_pmic_resets 1>;',1)
experimental=new.replace('status = "disabled";\n\t};\n\n\tcam_pmic_q:',
 'status = "okay";\n\t};\n\n\tcam_pmic_q:',1)
assert experimental!=new
hashes={}
for name,data in [('product-p-disabled.dts',new),('experimental-p-identity-only.dts',experimental)]:
 (P/'candidate'/name).write_text(data);(R/name).write_text(data);hashes[name]=hashlib.sha256(data.encode()).hexdigest()
# Candidate integration snippets; canonical Kconfig and Makefile stay unchanged.
(R/'Kconfig.fragment').write_text('''config RESET_REALME_RMX1931_PM8008
	tristate "Realme RMX1931 camera PM8008 resets"
	depends on OF && GPIOLIB && RESET_CONTROLLER
	help
	  Own P/Q reset GPIOs and hold P while Q changes its I2C address.
''')
(R/'Makefile.fragment').write_text('obj-$(CONFIG_RESET_REALME_RMX1931_PM8008) += reset-realme-rmx1931-pm8008.o\n')
report=dict(stage=232,base_is_actual_deployed219_source=True,source_hashes=hashes,
 product_p_disabled=True,experimental_p_requires_explicit_readonly_module_opt_in=True,
 old_rear_hog_replaced_by_exclusive_provider=True,no_vin_or_sensor_nodes_invented=True,
 canonical_and_phone_not_modified=True)
(R/'board-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
