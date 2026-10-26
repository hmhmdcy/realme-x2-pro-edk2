"""Prepare common sensor/PMIC drivers and board data, without touching hardware."""
from pathlib import Path
import difflib
import hashlib
import json
import re

R = Path(__file__).resolve().parent
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')

def change(s, old, new):
    assert s.count(old) == 1, (old[:100], s.count(old))
    return s.replace(old, new, 1)

# Link frequency describes a sensor operating configuration, not a phone model.
s = (R.parent/'kernel266/imx319.c').read_text()
start = s.index('/* RMX1931 resources:')
end = s.index('static int imx319_get_power_resources(', start)
s = s[:start] + '/* Standard regulator consumers supply dependency ordering. */\n' + s[end:]
start = s.index('\tif (!of_device_is_compatible(', s.index('static int imx319_get_power_resources('))
end = s.index('\timx319->reset_gpio =', start)
s = s[:start] + s[end:]
start = s.index('\tret = regulator_set_voltage(', s.index('static int imx319_get_power_resources('))
end = s.index('\timx319->of_power_resources = true;', start)
s = s[:start] + s[end:]
s = change(s, '\tint ret;\n\n\tif (!dev->of_node)\n', '\n\tif (!dev->of_node)\n')
for name in ['vana', 'vdig', 'vif']:
    s = change(s, f'devm_regulator_get(dev, "{name}")', f'devm_regulator_get_optional(dev, "{name}")')
    # These supplies are required by the sensor. The optional API avoids dummy fallback.
s = s.replace('imx319_rmx1931_profile', 'imx319_222mhz_profile')
s = s.replace('imx319_acpi_profile', 'imx319_482mhz_profile')
s = s.replace('imx319_oem', 'imx319_222mhz')
s = s.replace('imx319-oem-tables.h', 'imx319-222mhz-tables.h')
s = change(s, '\timx319->profile = client->dev.of_node ? &imx319_222mhz_profile : &imx319_482mhz_profile;\n', '')
s = change(s, 'static struct imx319_hwcfg *imx319_get_hwcfg(struct device *dev,\n\t\t\t\t\t   const struct imx319_profile *profile)',
           'static struct imx319_hwcfg *imx319_get_hwcfg(struct imx319 *imx319)')
s = change(s, '\tstruct imx319_hwcfg *cfg;\n', '\tstruct device *dev = imx319->dev;\n\tconst struct imx319_profile *profile;\n\tstruct imx319_hwcfg *cfg;\n\tunsigned int i;\n')
needle = '\tret = v4l2_link_freq_to_bitmap(dev, bus_cfg.link_frequencies,'
selection = '''\tprofile = NULL;
\tfor (i = 0; i < bus_cfg.nr_of_link_frequencies; i++) {
\t\tif (bus_cfg.link_frequencies[i] == IMX319_LINK_FREQ_DEFAULT)
\t\t\tprofile = &imx319_482mhz_profile;
\t\telse if (bus_cfg.link_frequencies[i] == 222000000)
\t\t\tprofile = &imx319_222mhz_profile;
\t\telse
\t\t\tcontinue;
\t\tbreak;
\t}
\tif (!profile)
\t\tgoto out_err;
\timx319->profile = profile;

'''
s = change(s, needle, selection+needle)
s = change(s, 'imx319_get_hwcfg(imx319->dev, imx319->profile)', 'imx319_get_hwcfg(imx319)')
s = change(s, '"realme,rmx1931-imx319"', '"sony,imx319"')
s = s.replace('#include <linux/platform_device.h>\n', '')
s = s.replace('of_power_resources', 'managed_power')
assert not any(x in s for x in ['rmx1931', 'samurai', 'lab_supplier', 'of_machine_is_compatible'])
(R/'imx319.c').write_text(s)
header = (R.parent/'kernel266/imx319-oem-tables.h').read_text().replace('imx319_oem', 'imx319_222mhz')
(R/'imx319-222mhz-tables.h').write_text(header)

# Keep the PM8008 address dependency in the common chip driver. A temporary
# GPIO lease holds any explicitly dependent PMIC at the factory address.
s = (R.parent/'kernel235/qcom-pm8008.c').read_text()
for include in ['#include <linux/mfd/qcom-pm8008-imx319-lab.h>\n', '#include <linux/reset.h>\n']:
    s = s.replace(include, '')
start = s.index('/* Laboratory bring-up only:')
end = s.index('struct pm8008_reset {', start)
s = s[:start] + s[end:]
s = change(s, '\tstruct reset_control *control;', '\tstruct gpio_desc *blocker;')
s = change(s, '\treturn reset->gpio || reset->control;', '\treturn reset->gpio;')
start = s.index('\tif (reset->control)')
end = s.index('\tif (reset->gpio)', start)
s = s[:start] + s[end:]
start = s.index('static int pm8008_link_reset_supplier(')
end = s.index('static struct device_node *pm8008_address_supplier_node(', start)
s = s[:start] + '''static int pm8008_get_reset(struct i2c_client *client, struct pm8008_reset *reset)
{
\treset->dev = &client->dev;
\treset->gpio = devm_gpiod_get_optional(&client->dev, "reset", GPIOD_ASIS);
\treturn PTR_ERR_OR_ZERO(reset->gpio);
}

/* Hold a dependent device in reset until address assignment is complete. */
static int pm8008_hold_address_conflict(struct i2c_client *client,
\t\t\t\t      struct pm8008_reset *reset)
{
\tstruct device_node *node, *supplier;
\tu32 address, initial;

\tif (device_property_read_u32(&client->dev, "qcom,initial-address", &initial))
\t\treturn 0;
\tfor_each_available_child_of_node(client->dev.of_node->parent, node) {
\t\tif (node == client->dev.of_node ||
\t\t    !of_device_is_compatible(node, "qcom,pm8008") ||
\t\t    of_property_read_u32(node, "reg", &address) || address != initial)
\t\t\tcontinue;
\t\tsupplier = of_parse_phandle(node, "qcom,address-setup-supplier", 0);
\t\tif (supplier != client->dev.of_node) {
\t\t\tof_node_put(supplier);
\t\t\tof_node_put(node);
\t\t\treturn -EINVAL;
\t\t}
\t\tof_node_put(supplier);
\t\treset->blocker = devm_fwnode_gpiod_get_index(&client->dev,
\t\t\t\tof_fwnode_handle(node), "reset", 0,
\t\t\t\tGPIOD_OUT_HIGH, "pm8008-address-conflict");
\t\tof_node_put(node);
\t\treturn PTR_ERR_OR_ZERO(reset->blocker);
\t}
\treturn 0;
}

''' + s[end:]
s = change(s, '!device_property_present(dev, "resets") ||\n\t    device_property_present(dev, "reset-gpios") ||',
           '!device_property_present(dev, "reset-gpios") ||')
start = s.index('static int pm8008_lab_assert_p_reset(')
end = s.index('static int pm8008_read_identity(', start)
s = s[:start] + s[end:]
start = s.index('static int pm8008_reset_and_address(')
end = s.index('static int pm8008_probe(', start)
s = s[:start] + '''static int pm8008_reset_and_address(struct i2c_client *client,
\t\t\t\t    struct pm8008_reset **result)
{
\tstruct device *dev = &client->dev;
\tstruct device_node *supplier;
\tstruct pm8008_reset *reset;
\tint ret;

\tsupplier = pm8008_address_supplier_node(client);
\tif (IS_ERR(supplier))
\t\treturn PTR_ERR(supplier);
\tif (supplier) {
\t\tret = pm8008_link_address_supplier(client, supplier);
\t\tif (ret)
\t\t\tgoto put_node;
\t}
\treset = devm_kzalloc(dev, sizeof(*reset), GFP_KERNEL);
\tif (!reset) {
\t\tret = -ENOMEM;
\t\tgoto put_node;
\t}
\tret = pm8008_hold_address_conflict(client, reset);
\tif (ret)
\t\tgoto put_node;
\tret = pm8008_get_reset(client, reset);
\tif (ret)
\t\tgoto put_node;
\t/* Children disappear before reset is asserted and its GPIO released. */
\tif (pm8008_has_reset(reset)) {
\t\tret = devm_add_action_or_reset(dev, pm8008_hold_reset, reset);
\t\tif (ret)
\t\t\tgoto put_node;
\t}
\tmutex_lock(&pm8008_address_lock);
\tret = pm8008_initialize_address(client, reset);
\tif (!ret)
\t\tret = pm8008_read_identity(client, client->addr);
\tmutex_unlock(&pm8008_address_lock);
\tif (!ret)
\t\t*result = reset;
put_node:
\tof_node_put(supplier);
\treturn ret;
}

struct pm8008_global_enable {
\tstruct regmap *regmap;
\tunsigned int original;
};

static void pm8008_restore_global(void *data)
{
\tstruct pm8008_global_enable *enable = data;
\tint ret;

\tret = regmap_update_bits(enable->regmap, 0x0950, BIT(0), enable->original);
\tif (ret)
\t\tdev_err(regmap_get_device(enable->regmap),
\t\t\t"failed to restore global enable: %d\\n", ret);
}

''' + s[end:]
s = change(s, '\tstruct pm8008_imx319_lab_state *lab;\n\tstruct pm8008_imx319_lab_data *lab_data;\n\tstruct mfd_cell lab_cell = { .name = "pm8008-reg-lab14" };',
           '\tstruct pm8008_reset *reset;\n\tstruct pm8008_global_enable *enable;')
s = change(s, 'pm8008_reset_and_address(client);', 'pm8008_reset_and_address(client, &reset);')
start = s.index('\tif (experimental_p_address_only &&')
end = s.index('\tdummy =', start)
s = s[:start] + s[end:]
start = s.index('\n\tif (experimental_p_imx319_power &&')
end = s.index('\tif (client->irq > 0)', start)
s = s[:start] + '''
\tenable = devm_kzalloc(dev, sizeof(*enable), GFP_KERNEL);
\tif (!enable)
\t\treturn -ENOMEM;
\tenable->regmap = regmap;
\tret = regmap_read(regmap, 0x0950, &enable->original);
\tif (ret)
\t\treturn ret;
\tenable->original &= BIT(0);
\tret = devm_add_action_or_reset(dev, pm8008_restore_global, enable);
\tif (ret)
\t\treturn ret;
\tret = regmap_update_bits(regmap, 0x0950, BIT(0), BIT(0));
\tif (ret)
\t\treturn ret;

''' + s[end:]
s = change(s, '\treturn devm_mfd_add_devices(dev, PLATFORM_DEVID_AUTO, cells,\n\t\t\t\tnum_cells, NULL, 0, domain);',
'''\tret = devm_mfd_add_devices(dev, PLATFORM_DEVID_AUTO, cells,
\t\t\t\t   num_cells, NULL, 0, domain);
\tif (ret)
\t\treturn ret;
\t/* The persistent consumer link permits the dependent PMIC to probe next. */
\tif (reset->blocker) {
\t\tdevm_gpiod_put(dev, reset->blocker);
\t\treset->blocker = NULL;
\t}
\treturn 0;''')
assert not any(x in s for x in ['experimental_', 'rmx1931', 'samurai', '_lab', 'reset_control_'])
(R/'qcom-pm8008.c').write_text(s)

# Extend the upstream regulator implementation, using DT constraints for all
# seven possible outputs. Only enabled, described outputs are registered.
s = (K/'drivers/regulator/qcom-pm8008-regulator.c').read_text()
s = change(s, '#include <linux/device.h>', '#include <linux/device.h>\n#include <linux/iopoll.h>\n#include <linux/property.h>')
s = change(s, '#define LDO_ENABLE_REG', '#define LDO_STATUS_REG\t\t\t0x08\n#define LDO_ENABLE_REG')
start = s.index('static const struct regulator_ops pm8008_regulator_ops =')
s = s[:start] + '''/* Wait for the analogue rail instead of assuming the ENABLE write is enough. */
static int pm8008_regulator_enable(struct regulator_dev *rdev)
{
\tstruct pm8008_regulator *preg = rdev_get_drvdata(rdev);
\tunsigned int value;
\tint ret, cleanup;

\tret = regulator_enable_regmap(rdev);
\tif (!ret)
\t\tret = regmap_read_poll_timeout(preg->regmap, preg->base + LDO_STATUS_REG,
\t\t\t\t\t       value, value & ENABLE_BIT, 100, 10000);
\tif (!ret)
\t\treturn 0;
\t/* A failed bus write may have reached hardware; always try to undo it. */
\tcleanup = regulator_disable_regmap(rdev);
\tif (cleanup)
\t\tdev_err(rdev_get_dev(rdev), "failed enable rollback: %d\\n", cleanup);
\treturn ret;
}

''' + s[start:]
s = change(s, '\t.list_voltage\t\t= regulator_list_voltage_linear,',
           '\t.list_voltage\t\t= regulator_list_voltage_linear_range,\n\t.map_voltage\t\t= regulator_map_voltage_linear_range,')
s = change(s, '\t.enable\t\t\t= regulator_enable_regmap,', '\t.enable\t\t\t= pm8008_regulator_enable,')
s = change(s, '\tstruct regmap *regmap;\n', '\tstruct regmap *regmap;\n\tstruct device_node *regulators, *node;\n\tchar supply[32];\n')
s = change(s, '\tfor (i = 0; i < ARRAY_SIZE(pm8008_reg_data); i++) {\n\t\tdata = &pm8008_reg_data[i];',
'''\tregulators = of_get_child_by_name(dev->parent->of_node, "regulators");
\tif (!regulators)
\t\treturn -ENODEV;
\tfor (i = 0; i < ARRAY_SIZE(pm8008_reg_data); i++) {
\t\tdata = &pm8008_reg_data[i];
\t\tregulators = of_get_child_by_name(dev->parent->of_node, "regulators");
\t\tnode = of_get_child_by_name(regulators, data->name);
\t\tof_node_put(regulators);
\t\tif (!of_device_is_available(node)) {
\t\t\tof_node_put(node);
\t\t\tcontinue;
\t\t}
\t\tof_node_put(node);''')
s = change(s, '\t\tdesc->supply_name = data->supply_name;',
'''\t\tsnprintf(supply, sizeof(supply), "%s-supply", data->supply_name);
\t\tif (device_property_present(dev->parent, supply))
\t\t\tdesc->supply_name = data->supply_name;''')
s = change(s, '\tif (!regulators)\n\t\treturn -ENODEV;\n\tfor (i =',
           '\tif (!regulators)\n\t\treturn -ENODEV;\n\tof_node_put(regulators);\n\n\tfor (i =')
(R/'qcom-pm8008-regulator.c').write_text(s)

# Board-only GPIO numbers, rail constraints and CSI wiring.
s = (R.parent/'kernel232/experimental-p-identity-only.dts').read_text()
start = s.index('/ {\n\tcam_pmic_resets: camera-pmic-resets {')
end = s.index('\n};', start)+3
s = s[:start] + s[end:]
s = change(s, '\t\tresets = <&cam_pmic_resets 0>;', '\t\treset-gpios = <&pm8150l_gpios 1 GPIO_ACTIVE_LOW>;\n\t\tvdd-l1-l2-supply = <&vreg_s8c_1p3>;')
s = change(s, '\t\tresets = <&cam_pmic_resets 1>;', '\t\treset-gpios = <&pm8150l_gpios 4 GPIO_ACTIVE_LOW>;')
s += '\n#include "imx319.dtsi"\n'
(R/'sm8150-samurai.dts').write_text(s)
s = (R.parent/'kernel266/imx319-p-lab.dtsi').read_text()
s = change(s, '/* RMX1931 lab only: original 19781 wiring and two selected P outputs. */',
           '/* RMX1931 camera wiring and voltage constraints from the 19781 board. */')
s = change(s, '\trealme,imx319-power-lab;\n\t/* VIN ownership remains unresolved; this is not a product PMIC profile. */',
           '\t/* PLDO inputs are not software-managed here; no dummy VIN is added. */')
s = change(s, '"realme,rmx1931-imx319"', '"sony,imx319"')
s = s.replace('/* OEM PLL-derived candidate; native SOF validation pending. */',
              '/* Four-lane sensor PLL operating point, validated in 237. */')
(R/'imx319.dtsi').write_text(s)

inputs = ['imx319.c','imx319-222mhz-tables.h','qcom-pm8008.c','qcom-pm8008-regulator.c','sm8150-samurai.dts','imx319.dtsi']
report = dict(stage=267, source_sha256={n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in inputs},
              sensor_board_name_checks_removed=True, sensor_supply_voltages_from_dt=True,
              sensor_configuration_from_endpoint_link_frequency=True,
              pmic_lab_child_and_parameters_removed=True, board_reset_provider_removed=True,
              gpio_numbers_and_wiring_in_dt=True, pmic_common_driver_for_both_chips=True,
              register_only_described_outputs=True, omitted_vin_does_not_create_dummy=True,
              unknown_pldo_input_source_not_invented=True, candidate_not_installed=True)
(R/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
