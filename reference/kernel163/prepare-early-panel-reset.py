from pathlib import Path
import difflib, hashlib, json, subprocess

kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel163')
out = Path('/mnt/e/edk2-samurai-out/kernel163')
out.mkdir(mode=0o700, exist_ok=True)
name = 'drivers/pinctrl/qcom/pinctrl-sm8150.c'
path = kernel / name
before = path.read_text()
assert path.read_bytes() == subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=kernel)
assert (kernel / 'drivers/iommu/arm/arm-smmu/arm-smmu.c').read_bytes() == subprocess.check_output(
    ['git', 'show', 'HEAD:drivers/iommu/arm/arm-smmu/arm-smmu.c'], cwd=kernel)
compiled = json.loads((ref.parent / 'kernel161/build-package-validation.json').read_text())['prior_display_source_hashes_verified']
for item, digest in compiled.items():
    assert hashlib.sha256((kernel / item).read_bytes()).hexdigest() == digest, item
assert not (out / 'source-before-private.c').exists()
(out / 'source-before-private.c').write_text(before)
(out / 'config-before-private').write_bytes((kernel / '.config').read_bytes())
(out / 'other-diff-before-private.patch').write_bytes(subprocess.check_output(
    ['git', 'diff', '--binary', '--', '.', ':(exclude)' + name], cwd=kernel))
after = before.replace('#include <linux/module.h>', '#include <linux/gpio/consumer.h>\n#include <linux/module.h>', 1)
after = after.replace('#include "pinctrl-msm.h"', '#include <dt-bindings/gpio/gpio.h>\n\n#include "pinctrl-msm.h"', 1)
probe = '''static int sm8150_pinctrl_probe(struct platform_device *pdev)
{
	return msm_pinctrl_probe(pdev, &sm8150_pinctrl);
}'''
assert after.count(probe) == 1
replacement = '''/* Keep the panel dark while Linux replaces the firmware DSC pipeline. */
static void sm8150_samurai_reset_boot_panel(struct platform_device *pdev)
{
	struct device_node *panel;
	struct of_phandle_args args;
	struct gpio_desc *reset;
	int ret;

	if (!of_machine_is_compatible("realme,samurai"))
		return;

	panel = of_find_compatible_node(NULL, NULL, "samsung,sofef03f-m");
	if (!panel)
		return;
	if (!of_device_is_available(panel))
		goto put_panel;

	ret = of_parse_phandle_with_args(panel, "reset-gpios", "#gpio-cells",
					 0, &args);
	if (ret)
		goto warn;
	if (args.np != pdev->dev.of_node || args.args_count != 2 ||
	    args.args[0] != 6 || args.args[1] != GPIO_ACTIVE_LOW) {
		of_node_put(args.np);
		ret = -EINVAL;
		goto warn;
	}
	of_node_put(args.np);

	reset = fwnode_gpiod_get_index(of_fwnode_handle(panel), "reset", 0,
				       GPIOD_ASIS, "samurai-boot-panel");
	if (IS_ERR(reset)) {
		ret = PTR_ERR(reset);
		goto warn;
	}

	/* Logical assertion drives this active-low reset to physical low. */
	ret = gpiod_direction_output(reset, 1);
	/* Leave the level in place, but allow the panel driver to claim it. */
	gpiod_put(reset);
	if (ret)
		goto warn;

	dev_info(&pdev->dev, "SOFEF03F boot reset asserted before display takeover\\n");
	goto put_panel;
warn:
	dev_warn(&pdev->dev, "SOFEF03F boot reset unavailable: %d\\n", ret);
put_panel:
	of_node_put(panel);
}

static int sm8150_pinctrl_probe(struct platform_device *pdev)
{
	int ret;

	ret = msm_pinctrl_probe(pdev, &sm8150_pinctrl);
	if (!ret)
		sm8150_samurai_reset_boot_panel(pdev);
	return ret;
}'''
after = after.replace(probe, replacement, 1)
path.write_text(after)
patch = '''Subject: [PATCH] pinctrl/qcom: hold samurai panel in reset during boot takeover

The firmware DSC stream is active when Linux starts initializing SMMU and
display clocks. Keep this board's SOFEF03F panel in its active-low reset
after TLMM is ready, before those later device initcalls. Validate the
DT controller, pin and polarity, then release descriptor ownership for
the panel driver's existing native power and first-frame sequence.
Other boards and disabled panels retain the original probe behavior.

---

'''
patch += 'diff --git a/' + name + ' b/' + name + '\n'
patch += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/' + name, tofile='b/' + name))
(ref / 'early-panel-reset.patch').write_text(patch)
report = dict(stage=163, baseline_kernel=158, modified_files=[name],
              before_sha256={name: hashlib.sha256(before.encode()).hexdigest()},
              after_sha256={name: hashlib.sha256(after.encode()).hexdigest()},
              prior_display_source_hashes_verified=compiled, smmu161_candidate_not_included=True,
              board_compatible_required='realme,samurai', panel_compatible_required='samsung,sofef03f-m',
              reset_controller_pin_and_polarity_checked=True, descriptor_released_before_panel_probe=True,
              dtb_unchanged=True, config_unchanged=True, deployed=False, physical_bug_fixed=False)
(ref / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
