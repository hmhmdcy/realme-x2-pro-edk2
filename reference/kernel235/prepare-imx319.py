"""Use both independent vendor XML exports and extend the real ACPI driver."""
from pathlib import Path
import difflib
import hashlib
import json
import struct
import xml.etree.ElementTree as ET

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel235')
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')
sha = lambda data: hashlib.sha256(data).hexdigest()
tables = {}
for vendor in ['sunny', 'qtech']:
    root = ET.parse(P / ('init-xml/' + vendor + '-vendor-xml/Scenario.0/XML/None/sensorDriverData.xml')).getroot()
    mode = root.findall('resolutionInfo/resolutionData')[2]
    tables[vendor] = {}
    for name, node, count, digest in [
        ('global', root.find('initSettings'), 136, '5e8029f021b277c1dd551d481fba3303b0bb4da87e927a3be2eaba616e81e85e'),
        ('mode', mode, 171, 'e31586a739b52f00f6e61804d7dae24ff492c53f495497fe74fc02cf4134ea5e')]:
        rows = []
        for row in node.iter('regSetting'):
            assert row.findtext('regAddrType') == '2' and row.findtext('regDataType') == '1'
            assert row.findtext('operation') == 'WRITE' and row.findtext('delayUs') == '0'
            rows.append((int(row.findtext('registerAddr')), int(row.findtext('registerData'))))
        assert len(rows) == len(dict(rows)) == count
        assert sha(b''.join(struct.pack('>HB', *row) for row in rows)) == digest
        tables[vendor][name] = rows
assert tables['sunny'] == tables['qtech']
header = '/* SPDX-License-Identifier: GPL-2.0-only */\n/* RMX1931 OEM tables, both vendor XML readers cross-checked; no PLL edits. */\n'
for name, rows in tables['sunny'].items():
    header += 'static const struct imx319_reg imx319_oem_' + name + '_regs[] = {\n'
    header += ''.join('\t{ 0x%04x, 0x%02x },\n' % row for row in rows) + '};\n\n'
(R / 'imx319-oem-tables.h').write_text(header)
old = (K / 'drivers/media/i2c/imx319.c').read_text()
assert sha(old.encode()) == 'd17dac3f25d324a389c00a667271c8f8734b5481f1e6e00302b60574411ad786'
text = old


def replace(a, b):
    global text
    assert text.count(a) == 1, (a[:150], text.count(a))
    text = text.replace(a, b)


replace('#include <linux/i2c.h>', '''#include <linux/i2c.h>
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/of.h>
#include <linux/pinctrl/consumer.h>
#include <linux/platform_device.h>
#include <linux/regulator/consumer.h>''')
replace('struct imx319 {', '''struct imx319_profile {
\tconst struct imx319_mode *modes;
\tunsigned int num_modes;
\tconst struct imx319_reg_list *global_setting;
\tconst s64 *link_freqs;
\tunsigned int num_link_freqs;
\tu64 pixel_rate;
};

struct imx319 {''')
replace('\tstruct device *dev;', '''\tstruct device *dev;
\tconst struct imx319_profile *profile;
\tstruct clk *clk;
\tstruct gpio_desc *reset_gpio;
\tstruct regulator *vana, *vdig, *vif;
\tbool of_power_resources;
\tbool vana_enabled, vdig_enabled, vif_enabled, clock_enabled;
\tbool power_fault;
\tbool removing;
\t/* Exactly one owned runtime-PM reference while streaming is true. */
\tbool streaming;''')
profile = '''#include "imx319-oem-tables.h"

static const struct imx319_reg_list imx319_oem_global_setting = {
\t.regs = imx319_oem_global_regs,
\t.num_of_regs = ARRAY_SIZE(imx319_oem_global_regs),
};
static const struct imx319_mode imx319_oem_modes[] = {
\t{
\t\t.width = 1632, .height = 1224,
\t\t.fll_def = 3350, .fll_min = 3350, .llp = 2080,
\t\t.link_freq_index = 0,
\t\t.reg_list = { ARRAY_SIZE(imx319_oem_mode_regs), imx319_oem_mode_regs },
\t},
};
/* Firmware/PLL-derived rates, to be checked against native SOF timestamps. */
static const s64 imx319_oem_link_freqs[] = { 222000000 };
static const struct imx319_profile imx319_acpi_profile = {
\t.modes = supported_modes, .num_modes = ARRAY_SIZE(supported_modes),
\t.global_setting = &imx319_global_setting,
\t.link_freqs = link_freq_menu_items, .num_link_freqs = ARRAY_SIZE(link_freq_menu_items),
\t.pixel_rate = IMX319_LINK_FREQ_DEFAULT * 2 * 4 / 10,
};
static const struct imx319_profile imx319_rmx1931_profile = {
\t.modes = imx319_oem_modes, .num_modes = ARRAY_SIZE(imx319_oem_modes),
\t.global_setting = &imx319_oem_global_setting,
\t.link_freqs = imx319_oem_link_freqs, .num_link_freqs = ARRAY_SIZE(imx319_oem_link_freqs),
\t.pixel_rate = 209066666,
};

'''
replace('static inline struct imx319 *to_imx319', profile + 'static inline struct imx319 *to_imx319')
replace('/* Get bayer order based on flip setting. */', (R / 'imx319-power.c.inc').read_text() + '\n/* Get bayer order based on flip setting. */')
replace('if (fse->index >= ARRAY_SIZE(supported_modes))', 'if (fse->index >= imx319->profile->num_modes)')
replace('fse->min_width = supported_modes[fse->index].width;', 'fse->min_width = imx319->profile->modes[fse->index].width;')
replace('fse->min_height = supported_modes[fse->index].height;', 'fse->min_height = imx319->profile->modes[fse->index].height;')
replace('''mode = v4l2_find_nearest_size(supported_modes,
\t\t\t\t      ARRAY_SIZE(supported_modes),''', '''mode = v4l2_find_nearest_size(imx319->profile->modes,
\t\t\t\t      imx319->profile->num_modes,''')
replace('''\t\tpixel_rate = IMX319_LINK_FREQ_DEFAULT * 2 * 4;
\t\tdo_div(pixel_rate, 10);''', '\t\tpixel_rate = imx319->profile->pixel_rate;')
replace('''\tmutex_lock(&imx319->mutex);

\t/*
\t * Only one bayer order is supported.''', '''\tmutex_lock(&imx319->mutex);
\tif (fmt->which == V4L2_SUBDEV_FORMAT_ACTIVE && imx319->streaming) {
\t\tmutex_unlock(&imx319->mutex);
\t\treturn -EBUSY;
\t}

\t/*
\t * Only one bayer order is supported.''')
replace('reg_list = &imx319_global_setting;', 'reg_list = imx319->profile->global_setting;')
start = text.index('static int imx319_set_stream(')
end = text.index('static const struct v4l2_subdev_core_ops', start)
text = text[:start] + (R / 'imx319-stream.c.inc').read_text() + '\n\n' + text[end:]
replace('max = ARRAY_SIZE(link_freq_menu_items) - 1;', 'max = imx319->profile->num_link_freqs - 1;')
replace('''\t\t\t\t\t\t   link_freq_menu_items);''', '''\t\t\t\t\t\t   imx319->profile->link_freqs);''')
replace('''\tpixel_rate = IMX319_LINK_FREQ_DEFAULT * 2 * 4;
\tdo_div(pixel_rate, 10);''', '\tpixel_rate = imx319->profile->pixel_rate;')
replace('/* pixel_rate = link_freq * 2 * nr_of_lanes / bits_per_sample */',
        '/* Array timing rate is independent of the CSI transport capacity. */')
replace('static struct imx319_hwcfg *imx319_get_hwcfg(struct device *dev)',
        'static struct imx319_hwcfg *imx319_get_hwcfg(struct device *dev,\n\t\t\t\t\t   const struct imx319_profile *profile)')
replace('''\tcfg = devm_kzalloc(dev, sizeof(*cfg), GFP_KERNEL);''', '''\tif (dev->of_node && bus_cfg.bus.mipi_csi2.num_data_lanes != 4)
\t\tgoto out_err;

\tcfg = devm_kzalloc(dev, sizeof(*cfg), GFP_KERNEL);''')
replace('''\t\t\t\t       link_freq_menu_items,
\t\t\t\t       ARRAY_SIZE(link_freq_menu_items),''', '''\t\t\t\t       profile->link_freqs,
\t\t\t\t       profile->num_link_freqs,''')
replace('''\tif (!pm_runtime_get_if_in_use(imx319->dev))
\t\treturn 0;''', '''\tif (imx319->power_fault)
\t\treturn -EIO;
\tret = pm_runtime_get_if_in_use(imx319->dev);
\tif (ret <= 0)
\t\treturn ret;''')
start = text.index('static int imx319_probe(')
end = text.index('static const struct acpi_device_id', start)
text = text[:start] + (R / 'imx319-probe.c.inc').read_text() + '\n\n' + text[end:]
replace('static struct i2c_driver imx319_i2c_driver', '''static const struct of_device_id imx319_of_match[] = {
\t{ .compatible = "realme,rmx1931-imx319" },
\t{ }
};
MODULE_DEVICE_TABLE(of, imx319_of_match);

static struct i2c_driver imx319_i2c_driver''')
replace('\t\t.acpi_match_table = ACPI_PTR(imx319_acpi_ids),', '''\t\t.acpi_match_table = ACPI_PTR(imx319_acpi_ids),
\t\t.of_match_table = imx319_of_match,
\t\t.pm = pm_ptr(&imx319_pm_ops),''')
target = R / 'imx319.c'
if target.exists():
    assert sha(target.read_bytes()) == '49ad45f97bd60caeec74f8cd0f499a398eaa1e16c8999ea0a83a8182330a8e48'
    (P / 'imx319-r4-source-private.c').write_bytes(target.read_bytes())
    (P / 'imx319-r4-source-validation-private.json').write_bytes((R / 'imx319-source-validation.json').read_bytes())
data_block = old[old.index('static const struct imx319_reg'):old.index('static inline struct imx319 *to_imx319')]
assert data_block in text
target.write_text(text)
(R / 'imx319-rmx1931-of-runtime.patch').write_text(''.join(difflib.unified_diff(
    old.splitlines(True), text.splitlines(True), fromfile='a/drivers/media/i2c/imx319.c',
    tofile='b/drivers/media/i2c/imx319.c')))
report = dict(stage=235, source_before_sha256=sha(old.encode()), source_candidate_sha256=sha(text.encode()),
              oem_header_sha256=sha(header.encode()), vendor_xml_global136_and_mode171_both_equal=True,
              actual_of_runtime_implementation=True, acpi_modes_and_register_tables_preserved=True,
              managed_lab_child_dependency=True, clock_and_three_real_supplies_required=True,
              pixel_rate_and_link_frequency_independent=True, rates_not_yet_measured=True,
              canonical_and_phone_unchanged=True)
(R / 'imx319-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
