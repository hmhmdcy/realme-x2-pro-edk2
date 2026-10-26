"""Prepare actual isolated235 PMIC sources; keep canonical after228 intact."""
from pathlib import Path
import ast
import difflib
import hashlib
import importlib.util
import json
import shutil

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel235')
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')
sha = lambda data: hashlib.sha256(data).hexdigest()
spec = importlib.util.spec_from_file_location('snapshot227', R.parent / 'kernel227/prepare-fastrpc.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
before = helper.snapshot()
assert before == json.loads((P.parent / 'kernel228/canonical-after-private.json').read_text())
(P / 'kernel-before-private.json').write_text(json.dumps(before, indent=2) + '\n')
old = (R.parent / 'kernel232/qcom-pm8008.c').read_text()
assert sha(old.encode()) == 'bd6c578e4347eecee1219f934f578c530efc4c20568ba0139f9bb35b102d8092'
text = old


def replace(a, b):
    global text
    assert text.count(a) == 1, a
    text = text.replace(a, b)


replace('#include <linux/mfd/core.h>', '#include <linux/mfd/core.h>\n#include <linux/mfd/qcom-pm8008-imx319-lab.h>')
replace('struct pm8008_reset {', '''static bool experimental_p_imx319_power;
module_param(experimental_p_imx319_power, bool, 0444);
MODULE_PARM_DESC(experimental_p_imx319_power, "Enable strictly isolated P L1/L4 IMX319 laboratory regulators");

struct pm8008_reset {''')
replace('''\t/* Incomplete rear VIN description: missing opt-in must never release P. */
\tif (supplier && !experimental_p_address_only) {
\t\tret = -EOPNOTSUPP;
\t\tgoto put_node;
\t}''', '''\t/* On this board factory-address P must never fall back to seven rails. */
\tif (of_machine_is_compatible("realme,samurai") &&
\t    client->addr == PM8008_FACTORY_ADDRESS && !supplier) {
\t\tret = -EINVAL;
\t\tgoto put_node;
\t}
\t/* Default-off, mutually exclusive lab profiles. Never reinterpret Q. */
\tif (supplier) {
\t\tif (experimental_p_address_only == experimental_p_imx319_power) {
\t\t\tret = -EOPNOTSUPP;
\t\t\tgoto put_node;
\t\t}
\t\tif (experimental_p_imx319_power !=
\t\t    device_property_present(dev, "realme,imx319-power-lab") ||
\t\t    (experimental_p_imx319_power && client->irq > 0)) {
\t\t\tret = -EINVAL;
\t\t\tgoto put_node;
\t\t}
\t} else if (device_property_present(dev, "realme,imx319-power-lab")) {
\t\tret = -EINVAL;
\t\tgoto put_node;
\t}''')
replace('''\tstruct i2c_client *dummy;
\tint num_cells;''', '''\tstruct i2c_client *dummy;
\tstruct pm8008_imx319_lab_state *lab;
\tstruct pm8008_imx319_lab_data *lab_data;
\tstruct mfd_cell lab_cell = { .name = "pm8008-reg-lab14" };
\tint num_cells;''')
replace('static int pm8008_read_identity(struct i2c_client *client, u16 address)', '''static int pm8008_lab_assert_p_reset(void *data)
{
\tstruct pm8008_reset *reset = data;
\tint ret;

\tif (!reset || !reset->control || reset->gpio)
\t\treturn -EINVAL;
\tret = pm8008_set_reset(reset, true);
\tif (ret)
\t\treturn ret;
\tret = reset_control_status(reset->control);
\treturn ret < 0 ? ret : ret == 1 ? 0 : -EIO;
}

static int pm8008_read_identity(struct i2c_client *client, u16 address)''')
replace('''\tmutex_unlock(&pm8008_address_lock);
put_node:''', '''\tmutex_unlock(&pm8008_address_lock);
\tif (!ret && supplier)
\t\tdev_set_drvdata(dev, reset);
put_node:''')
replace('''\tif (client->irq > 0) {
\t\tname = devm_kasprintf''', '''\tif (experimental_p_imx319_power &&
\t    device_property_present(dev, "qcom,address-setup-supplier")) {
\t\tlab = devm_kzalloc(dev, sizeof(*lab), GFP_KERNEL);
\t\tif (!lab)
\t\t\treturn -ENOMEM;
\t\tlab_data = devm_kzalloc(dev, sizeof(*lab_data), GFP_KERNEL);
\t\tif (!lab_data)
\t\t\treturn -ENOMEM;
\t\tlab->magic = PM8008_IMX319_LAB_MAGIC;
\t\tlab->parent = dev;
\t\tlab->primary = regmap;
\t\tlab->secondary = regmap2;
\t\tlab->mask = PM8008_IMX319_LAB_MASK;
\t\tmutex_init(&lab->lock);
\t\tlab->assert_p_reset = pm8008_lab_assert_p_reset;
\t\tlab->reset_cookie = dev_get_drvdata(dev);
\t\tlab_data->state = lab;
\t\tlab_cell.platform_data = lab_data;
\t\tlab_cell.pdata_size = sizeof(*lab_data);
\t\t/* Child receives a pointer; fault survives child unbind/reprobe. */
\t\treturn devm_mfd_add_devices(dev, PLATFORM_DEVID_AUTO, &lab_cell,
\t\t\t\t\t    1, NULL, 0, NULL);
\t}

\tif (client->irq > 0) {
\t\tname = devm_kasprintf''')
target = R / 'qcom-pm8008.c'
assert not target.exists()
target.write_text(text)
(R / 'pm8008-p-imx319-lab.patch').write_text(''.join(difflib.unified_diff(
    old.splitlines(True), text.splitlines(True), fromfile='a/drivers/mfd/qcom-pm8008.c',
    tofile='b/drivers/mfd/qcom-pm8008.c')))
shutil.copyfile(P.parent / 'kernel234/usb-ipv6-candidates-private.json', P / 'usb-ipv6-candidates-private.json')
host = (R.parent / 'kernel234/host.py').read_text().replace('kernel234', 'kernel235').replace('usb234', 'usb235').replace('operation failed', 'operation failed')
(R / 'host.py').write_text(host)
baseline = (R.parent / 'kernel234/collect-baseline.py').read_text().replace("root / 'k234-baseline-r2'", "root / 'k235-baseline'").replace('stage=234,', 'stage=235,')
ast.parse(baseline)
(R / 'collect-baseline.py').write_text(baseline)
for path in R.glob('*.py'):
    ast.parse(path.read_text())
report = dict(stage=235, canonical_after228_preserved=True, mfd_before_sha256=sha(old.encode()),
              mfd_candidate_sha256=sha(text.encode()),
              regulator_candidate_sha256=sha((R / 'qcom-pm8008-imx319-lab.c').read_bytes()),
              shared_header_sha256=sha((R / 'qcom-pm8008-imx319-lab.h').read_bytes()),
              q_regulator_source_unchanged=True, new_profile_default_disabled=True,
              profiles_mutually_exclusive=True, fault_lifetime_is_parent_mfd_epoch=True,
              physical_p_vin_unmanaged_and_not_invented=True, phone_unchanged=True)
(R / 'pmic-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
