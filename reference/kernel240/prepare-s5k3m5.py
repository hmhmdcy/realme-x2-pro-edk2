"""Extend the actual upstream driver with verified RMX1931 OEM mode3."""
from pathlib import Path
import difflib
import hashlib
import json
import struct
import xml.etree.ElementTree as ET

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel239')
check = json.loads((R.parent / 'kernel239/s5k3m5-crosscheck-validation.json').read_text())
assert check['independent_bounded_original_bin_decoder_agrees']
data = json.loads((P / 's5k3m5-direct-registers-private.json').read_text())
init, mode = data['init'], data['modes'][3]
assert len(init) == 917 and len(mode) == 53
xml = ET.parse(next((P / 's5k3m5-b-xml-private').rglob('sensorDriverData.xml'))).getroot()
def rows(node):
    return [[int(row.findtext('registerAddr')), int(row.findtext('regAddrType')), int(row.findtext('regDataType')),
             row.findtext('operation'), [int(v.text) for v in row.findall('registerData')],
             [int(v.text) for v in row.findall('delayUs')]] for row in node.findall('regSetting')]
assert init == rows(xml.find('initSettings/initSetting'))
assert mode == rows(xml.findall('resolutionInfo/resolutionData')[3].find('resSettings'))
assert all(row[1] == 2 and row[3] == 'WRITE' and len(row[4]) == len(row[5]) == 1 for row in init + mode)
assert all(row[2] == 2 and row[5] == [0] for row in mode)
header = '''/* SPDX-License-Identifier: GPL-2.0-only */
/* RMX1931 OEM tables: independent BIN decoder and both schema views agree. */
struct s5k3m5_oem_reg { u32 reg; u16 value; u32 delay_us; };
static const struct s5k3m5_oem_reg s5k3m5_rmx_init[] = {
'''
header += ''.join('\t{ CCI_REG%d(0x%04x), 0x%04x, %d },\n' % (r[2]*8, r[0], r[4][0], r[5][0]) for r in init)
header += '};\n\nstatic const struct cci_reg_sequence s5k3m5_rmx_mode3_regs[] = {\n'
header += ''.join('\t{ CCI_REG16(0x%04x), 0x%04x },\n' % (r[0], r[4][0]) for r in mode) + '};\n'
(R / 's5k3m5-oem-tables.h').write_text(header)
old = (R / 's5k3m5-base.c').read_text()
assert hashlib.sha256(old.encode()).hexdigest() == '4ea922b55097a2cd653e1920516875e97d20a18dc41a6109278fd02df2bcc5ba'
text = old
def replace(a, b):
    global text
    assert text.count(a) == 1, (a[:100], text.count(a))
    text = text.replace(a, b)
replace('#include <linux/module.h>', '#include <linux/module.h>\n#include <linux/of.h>\n#include <linux/pinctrl/consumer.h>\n#include <linux/platform_device.h>\n#include <linux/property.h>\n#include <linux/string.h>')
replace('struct s5k3m5 {', '''struct s5k3m5_profile {
	const struct s5k3m5_mode *modes;
	unsigned int num_modes;
	const s64 *link_freqs;
	unsigned int num_link_freqs;
	u64 pixel_rate;
	unsigned long mclk_rate;
	bool rmx1931;
};

struct s5k3m5 {''')
replace('\tstruct device *dev;', '''	struct device *dev;
	const struct s5k3m5_profile *profile;
	bool supply_enabled[S5K3M5_NUM_SUPPLIES];
	bool clock_enabled;
	bool power_fault;
	bool streaming;
	bool removing;''')
profiles = '''#include "s5k3m5-oem-tables.h"

static const struct s5k3m5_mode s5k3m5_rmx_modes[] = {
	{ .width = 2104, .height = 1560, .hts = 9648, .vts = 1663, .exposure = 256,
	  .reg_list = { s5k3m5_rmx_mode3_regs, ARRAY_SIZE(s5k3m5_rmx_mode3_regs) } },
};
static const s64 s5k3m5_rmx_link_freqs[] = { 723200000 };
static const struct s5k3m5_profile s5k3m5_default_profile = {
	.modes = s5k3m5_supported_modes, .num_modes = ARRAY_SIZE(s5k3m5_supported_modes),
	.link_freqs = s5k3m5_link_freq_menu, .num_link_freqs = ARRAY_SIZE(s5k3m5_link_freq_menu),
	.pixel_rate = 482000000, .mclk_rate = S5K3M5_MCLK_FREQ_24MHZ,
};
static const struct s5k3m5_profile s5k3m5_rmx_profile = {
	.modes = s5k3m5_rmx_modes, .num_modes = ARRAY_SIZE(s5k3m5_rmx_modes),
	.link_freqs = s5k3m5_rmx_link_freqs, .num_link_freqs = ARRAY_SIZE(s5k3m5_rmx_link_freqs),
	/* OEM mode3 timing metadata; native SOF/line timing validation pending. */
	.pixel_rate = 481930000, .mclk_rate = 19200000, .rmx1931 = true,
};

'''
replace('static int s5k3m5_set_ctrl(', profiles + 'static int s5k3m5_set_ctrl(')
replace('static inline u64 s5k3m5_freq_to_pixel_rate(const u64 freq)\n{\n\treturn div_u64(freq * 2 * S5K3M5_DATA_LANES, 10);\n}\n\n', '')
replace('ARRAY_SIZE(s5k3m5_link_freq_menu) - 1,\n\t\t\t\t\t0, s5k3m5_link_freq_menu);', 's5k3m5->profile->num_link_freqs - 1,\n\t\t\t\t\t0, s5k3m5->profile->link_freqs);')
replace('pixel_rate = s5k3m5_freq_to_pixel_rate(s5k3m5_link_freq_menu[0]);', 'pixel_rate = s5k3m5->profile->pixel_rate;')
replace('\tret = v4l2_fwnode_device_parse(s5k3m5->dev, &props);', '''	if (ctrl_hdlr->error) {
		ret = ctrl_hdlr->error;
		goto error_free_hdlr;
	}
	ret = v4l2_fwnode_device_parse(s5k3m5->dev, &props);''')
replace('\t/* Page pointer */', '''	if (s5k3m5->profile->rmx1931) {
		unsigned int i;

		for (i = 0; i < ARRAY_SIZE(s5k3m5_rmx_init); i++) {
			const struct s5k3m5_oem_reg *reg = &s5k3m5_rmx_init[i];

			ret = cci_write(s5k3m5->regmap, reg->reg, reg->value, NULL);
			if (ret)
				goto error;
			if (reg->delay_us)
				usleep_range(reg->delay_us, reg->delay_us + 5);
		}
		cci_multi_reg_write(s5k3m5->regmap, reg_list->regs, reg_list->num_regs, &ret);
		if (ret)
			goto error;
		goto setup_controls;
	}
	/* Page pointer */''')
replace('\tret = __v4l2_ctrl_handler_setup(s5k3m5->sd.ctrl_handler);', 'setup_controls:\n\tret = __v4l2_ctrl_handler_setup(s5k3m5->sd.ctrl_handler);')
replace('''	ret = pm_runtime_resume_and_get(s5k3m5->dev);
	if (ret)''', '''	if (s5k3m5->removing)
		return -ENODEV;
	if (s5k3m5->streaming)
		return 0;
	if (s5k3m5->power_fault)
		return -EIO;
	ret = pm_runtime_resume_and_get(s5k3m5->dev);
	if (ret < 0)''')
replace('''	return 0;

error:
	dev_err(s5k3m5->dev, "failed to start streaming: %d\\n", ret);
	pm_runtime_put_autosuspend(s5k3m5->dev);''', '''	s5k3m5->streaming = true;
	__v4l2_ctrl_grab(s5k3m5->hflip, true);
	__v4l2_ctrl_grab(s5k3m5->vflip, true);
	return 0;

error:
	dev_err(s5k3m5->dev, "failed to start streaming: %d\\n", ret);
	if (s5k3m5->profile->rmx1931) {
		int cleanup_ret;

		cleanup_ret = cci_write(s5k3m5->regmap, S5K3M5_REG_CTRL_MODE, 0, NULL);
		if (cleanup_ret)
			s5k3m5->power_fault = true;
		cleanup_ret = pm_runtime_put_sync_suspend(s5k3m5->dev);
		if (cleanup_ret < 0)
			s5k3m5->power_fault = true;
	} else {
		pm_runtime_put_autosuspend(s5k3m5->dev);
	}''')
replace('''	ret = cci_write(s5k3m5->regmap, S5K3M5_REG_CTRL_MODE, 0, NULL);
	if (ret)
		dev_err(s5k3m5->dev, "failed to stop streaming: %d\\n", ret);

	pm_runtime_put_autosuspend(s5k3m5->dev);''', '''	if (!s5k3m5->streaming)
		return 0;
	ret = cci_write(s5k3m5->regmap, S5K3M5_REG_CTRL_MODE, 0, NULL);
	if (ret) {
		dev_err(s5k3m5->dev, "failed to stop streaming: %d\\n", ret);
		if (s5k3m5->profile->rmx1931)
			s5k3m5->power_fault = true;
	}
	s5k3m5->streaming = false;
	if (s5k3m5->profile->rmx1931) {
		int suspend_ret = pm_runtime_put_sync_suspend(s5k3m5->dev);

		if (suspend_ret < 0) {
			s5k3m5->power_fault = true;
			if (!ret)
				ret = suspend_ret;
		}
	} else {
		pm_runtime_put_autosuspend(s5k3m5->dev);
	}
	__v4l2_ctrl_grab(s5k3m5->hflip, false);
	__v4l2_ctrl_grab(s5k3m5->vflip, false);''')
replace('''	mode = v4l2_find_nearest_size(s5k3m5_supported_modes,
				      ARRAY_SIZE(s5k3m5_supported_modes),''', '''	if (fmt->which == V4L2_SUBDEV_FORMAT_ACTIVE && s5k3m5->streaming)
		return -EBUSY;
	mode = v4l2_find_nearest_size(s5k3m5->profile->modes,
				      s5k3m5->profile->num_modes,''')
replace('fse->index >= ARRAY_SIZE(s5k3m5_supported_modes)', 'fse->index >= s5k3m5->profile->num_modes')
replace('fse->min_width = s5k3m5_supported_modes[fse->index].width;', 'fse->min_width = s5k3m5->profile->modes[fse->index].width;')
replace('fse->min_height = s5k3m5_supported_modes[fse->index].height;', 'fse->min_height = s5k3m5->profile->modes[fse->index].height;')
replace('sel->r.height = s5k3m5->mode->width;', 'sel->r.height = s5k3m5->mode->height;')
replace('''				       s5k3m5_link_freq_menu,
				       ARRAY_SIZE(s5k3m5_link_freq_menu),''', '''				       s5k3m5->profile->link_freqs,
				       s5k3m5->profile->num_link_freqs,''')
replace('static int s5k3m5_power_on(struct device *dev)', (R / 's5k3m5-power.c.inc').read_text() + '\nstatic int s5k3m5_power_on(struct device *dev)')
replace('\tret = regulator_bulk_enable(S5K3M5_NUM_SUPPLIES, s5k3m5->supplies);', '\tif (s5k3m5->profile->rmx1931)\n\t\treturn s5k3m5_rmx_power_on(s5k3m5);\n\tret = regulator_bulk_enable(S5K3M5_NUM_SUPPLIES, s5k3m5->supplies);')
replace('''	gpiod_set_value_cansleep(s5k3m5->reset_gpio, 1);

	clk_disable_unprepare(s5k3m5->mclk);''', '''	if (s5k3m5->profile->rmx1931)
		return s5k3m5_rmx_power_off(s5k3m5);
	gpiod_set_value_cansleep(s5k3m5->reset_gpio, 1);

	clk_disable_unprepare(s5k3m5->mclk);''')
replace('\ts5k3m5->dev = &client->dev;', '''	s5k3m5->dev = &client->dev;
	s5k3m5->profile = device_get_match_data(&client->dev);
	if (!s5k3m5->profile)
		s5k3m5->profile = &s5k3m5_default_profile;''')
replace('if (freq != S5K3M5_MCLK_FREQ_24MHZ)', 'if (freq != s5k3m5->profile->mclk_rate)')
start = text.index('\ts5k3m5->reset_gpio = devm_gpiod_get_optional', text.index('static int s5k3m5_probe'))
end = text.index('\n\t/* The sensor must be powered on', start)
original_resources = text[start:end]
new_resources = '''	if (s5k3m5->profile->rmx1931) {
		ret = s5k3m5_rmx_resources(s5k3m5);
		if (ret)
			return dev_err_probe(s5k3m5->dev, ret, "RMX1931 power resources unavailable\\n");
	} else {
''' + ''.join('\t' + line + '\n' for line in original_resources.splitlines()) + '\t}\n'
text = text[:start] + new_resources + text[end:]
replace('s5k3m5->mode = &s5k3m5_supported_modes[0];', 's5k3m5->mode = &s5k3m5->profile->modes[0];')
replace('''	pm_runtime_set_active(s5k3m5->dev);
	pm_runtime_enable(s5k3m5->dev);''', '''	ret = pm_runtime_set_active(s5k3m5->dev);
	if (ret)
		goto subdev_cleanup_without_pm;
	pm_runtime_get_noresume(s5k3m5->dev);
	pm_runtime_set_autosuspend_delay(s5k3m5->dev, 1000);
	pm_runtime_use_autosuspend(s5k3m5->dev);
	pm_runtime_enable(s5k3m5->dev);''')
replace('''	pm_runtime_set_autosuspend_delay(s5k3m5->dev, 1000);
	pm_runtime_use_autosuspend(s5k3m5->dev);
	pm_runtime_idle(s5k3m5->dev);''', '''	pm_runtime_mark_last_busy(s5k3m5->dev);
	pm_runtime_put_autosuspend(s5k3m5->dev);''')
replace('''subdev_cleanup:
	v4l2_subdev_cleanup(&s5k3m5->sd);
	pm_runtime_disable(s5k3m5->dev);
	pm_runtime_set_suspended(s5k3m5->dev);''', '''subdev_cleanup:
	pm_runtime_put_noidle(s5k3m5->dev);
	pm_runtime_disable(s5k3m5->dev);
	pm_runtime_set_suspended(s5k3m5->dev);
subdev_cleanup_without_pm:
	v4l2_subdev_cleanup(&s5k3m5->sd);''')
replace('''	v4l2_async_unregister_subdev(sd);
	v4l2_subdev_cleanup(sd);''', '''	struct v4l2_subdev_state *state;

	v4l2_async_unregister_subdev(sd);
	state = v4l2_subdev_lock_and_get_active_state(sd);
	s5k3m5->removing = true;
	if (s5k3m5->streaming)
		s5k3m5_disable_streams(sd, state, 0, BIT_ULL(0));
	v4l2_subdev_unlock_state(state);
	v4l2_subdev_cleanup(sd);''')
replace('{ .compatible = "samsung,s5k3m5" },', '{ .compatible = "realme,rmx1931-s5k3m5", .data = &s5k3m5_rmx_profile },\n\t{ .compatible = "samsung,s5k3m5", .data = &s5k3m5_default_profile },')
(R / 's5k3m5.c').write_text(text)
(R / 's5k3m5-rmx1931.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), text.splitlines(True), fromfile='a/drivers/media/i2c/s5k3m5.c', tofile='b/drivers/media/i2c/s5k3m5.c')))
report = dict(stage=240, source_sha256=hashlib.sha256(text.encode()).hexdigest(),
              header_sha256=hashlib.sha256(header.encode()).hexdigest(),
              init_records=917, mode3_records=53, xml_and_original_bin_decoding_preserved=True,
              init_last_write8_and_delay_microseconds_preserved=True, no_af_supply_in_sensor_profile=True,
              mode3_pixel_rate_uses_oem_metadata=481930000, link_freq_pll_candidate=723200000,
              physical_timing_not_yet_verified=True, base_24mhz_modes_preserved=True,
              gain_units_remain_multiplicative_1_to16_integer=True, fine_gain_step_open=True,
              selection_height_bug_fixed=True, active_stream_format_changes_blocked=True,
              runtime_pm_reference_owned_per_stream=True, shared_power_lease_busy_retryable=True,
              no_phone_operation=True)
(R / 's5k3m5-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
