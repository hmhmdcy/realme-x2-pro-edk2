// SPDX-License-Identifier: GPL-2.0-only
/*
 * Temporary RMX1931 panel DCS probe. Not a production driver.
 */
#include <linux/device.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/delay.h>

#include <drm/drm_mipi_dsi.h>
#include <video/mipi_display.h>

static int seq = 1;
module_param(seq, int, 0444);
MODULE_PARM_DESC(seq, "DCS test sequence: 1=off/sleep/reon, 2=display-on only, 3=tear-on, 4=compression");

static struct mipi_dsi_device *found_dsi;

static int find_dsi_child(struct device *dev, void *data)
{
	if (!strstr(dev_name(dev), ".dsi."))
		return 0;

	found_dsi = to_mipi_dsi_device(dev);
	get_device(dev);
	return 1;
}

static int send_hs(struct mipi_dsi_device *dsi, int (*fn)(struct mipi_dsi_device *))
{
	unsigned long flags = dsi->mode_flags;
	int ret;

	dsi->mode_flags &= ~MIPI_DSI_MODE_LPM;
	ret = fn(dsi);
	dsi->mode_flags = flags;
	return ret;
}

static int send_hs_brightness(struct mipi_dsi_device *dsi, u16 value)
{
	unsigned long flags = dsi->mode_flags;
	int ret;

	dsi->mode_flags &= ~MIPI_DSI_MODE_LPM;
	ret = mipi_dsi_dcs_set_display_brightness_large(dsi, value);
	dsi->mode_flags = flags;
	return ret;
}

static void read_dcs(struct mipi_dsi_device *dsi, u8 cmd)
{
	u8 value = 0;
	int ret;

	ret = mipi_dsi_dcs_read(dsi, cmd, &value, sizeof(value));
	dev_info(&dsi->dev, "DCS %#04x read ret=%d value=%#04x\n",
		 cmd, ret, value);
}

static int __init panel_dcs_probe_init(void)
{
	struct device *parent;
	struct device *child;
	struct mipi_dsi_device *dsi = NULL;
	u8 power_mode = 0;
	u16 brightness = 0;
	int ret;

	parent = bus_find_device_by_name(&platform_bus_type, NULL, "ae94000.dsi");
	if (!parent) {
		pr_err("panel_dcs_probe: DSI parent not found\n");
		return -ENODEV;
	}

	device_for_each_child(parent, NULL, find_dsi_child);
	put_device(parent);
	dsi = found_dsi;
	if (!dsi) {
		pr_err("panel_dcs_probe: DSI child not found\n");
		return -ENODEV;
	}

	dev_info(&dsi->dev, "panel_dcs_probe seq=%d flags=%#lx\n",
		 seq, dsi->mode_flags);

	ret = mipi_dsi_dcs_get_power_mode(dsi, &power_mode);
	dev_info(&dsi->dev, "power mode read ret=%d value=%#x\n", ret, power_mode);
	ret = mipi_dsi_dcs_get_display_brightness_large(dsi, &brightness);
	dev_info(&dsi->dev, "brightness read ret=%d value=%#x\n",
		 ret, brightness);
	read_dcs(dsi, MIPI_DCS_GET_COMPRESSION_MODE);
	read_dcs(dsi, MIPI_DCS_GET_ADDRESS_MODE);
	read_dcs(dsi, MIPI_DCS_GET_PIXEL_FORMAT);
	read_dcs(dsi, MIPI_DCS_GET_DISPLAY_MODE);
	read_dcs(dsi, MIPI_DCS_GET_SIGNAL_MODE);
	read_dcs(dsi, MIPI_DCS_GET_DIAGNOSTIC_RESULT);

	switch (seq) {
	case 1:
		ret = send_hs(dsi, mipi_dsi_dcs_set_display_off);
		dev_info(&dsi->dev, "display off ret=%d\n", ret);
		msleep(50);
		ret = mipi_dsi_dcs_enter_sleep_mode(dsi);
		dev_info(&dsi->dev, "sleep in ret=%d\n", ret);
		msleep(120);
		ret = mipi_dsi_dcs_exit_sleep_mode(dsi);
		dev_info(&dsi->dev, "sleep out ret=%d\n", ret);
		msleep(120);
		ret = send_hs(dsi, mipi_dsi_dcs_set_display_on);
		dev_info(&dsi->dev, "display on ret=%d\n", ret);
		msleep(20);
		ret = send_hs_brightness(dsi, 1024);
		dev_info(&dsi->dev, "brightness 1024 ret=%d\n", ret);
		break;
	case 2:
		ret = send_hs(dsi, mipi_dsi_dcs_set_display_on);
		dev_info(&dsi->dev, "display on ret=%d\n", ret);
		msleep(20);
		ret = send_hs_brightness(dsi, 1024);
		dev_info(&dsi->dev, "brightness 1024 ret=%d\n", ret);
		break;
	case 3:
		{
			static const u8 c2[] = { 0x2d, 0x27 };
			unsigned long flags = dsi->mode_flags;

			ret = mipi_dsi_dcs_write(dsi, 0xc2, c2, sizeof(c2));
			dsi->mode_flags = flags;
			dev_info(&dsi->dev, "0xc2 ret=%d\n", ret);
			ret = send_hs(dsi, mipi_dsi_dcs_set_display_on);
			dev_info(&dsi->dev, "display on ret=%d\n", ret);
			msleep(20);
			ret = send_hs_brightness(dsi, 1024);
			dev_info(&dsi->dev, "brightness 1024 ret=%d\n", ret);
		}
		break;
	case 4:
		{
			struct mipi_dsi_multi_context dsi_ctx = { .dsi = dsi };

			mipi_dsi_compression_mode_multi(&dsi_ctx, true);
			dev_info(&dsi->dev, "compression mode ret=%d\n",
				 dsi_ctx.accum_err);
			ret = send_hs(dsi, mipi_dsi_dcs_set_display_on);
			dev_info(&dsi->dev, "display on ret=%d\n", ret);
			msleep(20);
			ret = send_hs_brightness(dsi, 1024);
			dev_info(&dsi->dev, "brightness 1024 ret=%d\n", ret);
		}
		break;
	default:
		dev_warn(&dsi->dev, "unknown seq %d\n", seq);
	}

	put_device(&dsi->dev);
	found_dsi = NULL;
	return 0;
}

static void __exit panel_dcs_probe_exit(void)
{
}

module_init(panel_dcs_probe_init);
module_exit(panel_dcs_probe_exit);
MODULE_DESCRIPTION("Temporary RMX1931 panel DCS probe");
MODULE_LICENSE("GPL");
