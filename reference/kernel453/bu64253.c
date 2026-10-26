// SPDX-License-Identifier: GPL-2.0-only
/*
 * ROHM BU64253 factory VCM protocol: in-tree k363 Werror and host C
 * ASAN/UBSAN checked. DT/schema, kernel PM integration and hardware pending.
 */

#include <linux/delay.h>
#include <linux/firmware.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/pm_runtime.h>
#include <linux/property.h>
#include <linux/regulator/consumer.h>
#include <linux/string.h>
#include <linux/unaligned.h>
#include <media/v4l2-ctrls.h>
#include <media/v4l2-device.h>

#define BU64253_MAX_FOCUS	1023
#define BU64253_START_US	10000
#define BU64253_INIT_COUNT	3
#define BU64253_INIT_SIZE	(8 + BU64253_INIT_COUNT * 4)

struct bu64253_init {
	u8 address;
	u8 value;
	u16 delay_us;
};

struct bu64253 {
	struct v4l2_subdev sd;
	struct v4l2_ctrl_handler ctrls;
	struct mutex lock;
	struct regulator *vdd;
	struct bu64253_init init[BU64253_INIT_COUNT];
	bool init_valid;
	u16 target;
	bool target_valid;
	bool supply_enabled;
};

static inline struct bu64253 *to_bu64253(struct v4l2_subdev *sd)
{
	return container_of(sd, struct bu64253, sd);
}

static int bu64253_write(struct bu64253 *lens, const u8 *data, int len)
{
	struct i2c_client *client = v4l2_get_subdevdata(&lens->sd);
	int ret = i2c_master_send(client, data, len);

	return ret == len ? 0 : ret < 0 ? ret : -EIO;
}

static int bu64253_set_position(struct bu64253 *lens, u16 position)
{
	u8 data[2];
	int ret;

	if (position > BU64253_MAX_FOCUS)
		return -EINVAL;
	/* Factory MoveFocus sentinel 0xff: command byte C4 plus DAC bits 9:8. */
	data[0] = 0xc4 | ((position >> 8) & 0x03);
	data[1] = position & 0xff;

	ret = bu64253_write(lens, data, sizeof(data));
	if (!ret)
		usleep_range(1, 10);
	return ret;
}

/* Parse completely before probe can register a node or enable VDD. */
static int bu64253_load_init(struct device *dev, struct bu64253 *lens)
{
	const struct firmware *fw;
	const char *name;
	static const u8 addresses[] = { 0xd0, 0xc8, 0xf0 };
	static const u16 delays_us[] = { 5, 100, 10 };
	unsigned int i;
	int ret;

	ret = device_property_read_string(dev, "firmware-name", &name);
	if (ret)
		return ret;
	ret = request_firmware(&fw, name, dev);
	if (ret)
		return ret;
	ret = -EINVAL;
	if (fw->size != BU64253_INIT_SIZE || memcmp(fw->data, "BU53", 4) ||
	    fw->data[4] != 1 || fw->data[5] != BU64253_INIT_COUNT ||
	    fw->data[6] || fw->data[7])
		goto release;
	for (i = 0; i < BU64253_INIT_COUNT; i++) {
		const u8 *record = fw->data + 8 + i * 4;
		u16 delay = get_unaligned_le16(record + 2);

		if (record[0] != addresses[i] || delay != delays_us[i])
			goto release;
		if ((!i && record[1] != 0x71 && record[1] != 0x78) ||
		    (i == 1 && record[1] != 1) ||
		    (i == 2 && record[1] != 0x80))
			goto release;
		lens->init[i].address = record[0];
		lens->init[i].value = record[1];
		lens->init[i].delay_us = delay;
	}
	lens->init_valid = true;
	ret = 0;
release:
	release_firmware(fw);
	return ret;
}

static int bu64253_set_ctrl(struct v4l2_ctrl *ctrl)
{
	struct bu64253 *lens = container_of(ctrl->handler, struct bu64253, ctrls);
	struct device *dev = lens->sd.dev;
	int active, ret = 0;

	if (ctrl->id != V4L2_CID_FOCUS_ABSOLUTE)
		return -EINVAL;

	active = pm_runtime_get_if_in_use(dev);
	if (active < 0)
		return active;
	if (active) {
		ret = bu64253_set_position(lens, ctrl->val);
		pm_runtime_put(dev);
	}
	if (!ret) {
		lens->target = ctrl->val;
		lens->target_valid = true;
	}

	return ret;
}

static const struct v4l2_ctrl_ops bu64253_ctrl_ops = {
	.s_ctrl = bu64253_set_ctrl,
};

/* Caller holds lock. A failed disable retains the regulator reference. */
static int bu64253_power_off(struct bu64253 *lens)
{
	int ret;

	if (!lens->supply_enabled)
		return 0;
	ret = regulator_disable(lens->vdd);
	if (ret)
		return ret;
	lens->supply_enabled = false;
	/* Retained OEM VAF-off sequence has a 1 ms delay, not an ID handshake. */
	usleep_range(1000, 1100);

	return 0;
}

static int bu64253_runtime_resume(struct device *dev)
{
	struct bu64253 *lens = to_bu64253(dev_get_drvdata(dev));
	unsigned int i;
	int ret, cleanup;

	mutex_lock(&lens->lock);
	if (!lens->init_valid) {
		ret = -ENODATA;
		goto unlock;
	}
	/* Recover an earlier failed rollback without accumulating references. */
	ret = bu64253_power_off(lens);
	if (ret)
		goto unlock;
	ret = regulator_enable(lens->vdd);
	if (ret)
		goto unlock;
	lens->supply_enabled = true;
	usleep_range(BU64253_START_US, BU64253_START_US + 1000);
	for (i = 0; i < BU64253_INIT_COUNT; i++) {
		const struct bu64253_init *init = &lens->init[i];
		u8 command[] = { init->address, init->value };

		ret = bu64253_write(lens, command, sizeof(command));
		if (ret)
			goto disable;
		usleep_range(init->delay_us, init->delay_us + 10);
	}
	if (lens->target_valid) {
		ret = bu64253_set_position(lens, lens->target);
		if (ret)
			goto disable;
	}
	goto unlock;

disable:
	cleanup = bu64253_power_off(lens);
	if (cleanup)
		dev_err(dev, "failed to release VDD after initialization error: %d\n",
			cleanup);
unlock:
	mutex_unlock(&lens->lock);
	return ret;
}

static int bu64253_runtime_suspend(struct device *dev)
{
	struct bu64253 *lens = to_bu64253(dev_get_drvdata(dev));
	int ret;

	mutex_lock(&lens->lock);
	ret = bu64253_power_off(lens);
	mutex_unlock(&lens->lock);

	return ret;
}

static int bu64253_open(struct v4l2_subdev *sd, struct v4l2_subdev_fh *fh)
{
	return pm_runtime_resume_and_get(sd->dev);
}

static int bu64253_close(struct v4l2_subdev *sd, struct v4l2_subdev_fh *fh)
{
	pm_runtime_put(sd->dev);
	return 0;
}

static const struct v4l2_subdev_internal_ops bu64253_internal_ops = {
	.open = bu64253_open,
	.close = bu64253_close,
};

static const struct v4l2_subdev_ops bu64253_ops = { };

static int bu64253_probe(struct i2c_client *client)
{
	struct device *dev = &client->dev;
	struct bu64253 *lens;
	struct v4l2_ctrl *focus;
	int ret;

	if (!i2c_check_functionality(client->adapter, I2C_FUNC_I2C))
		return -EOPNOTSUPP;
	lens = devm_kzalloc(dev, sizeof(*lens), GFP_KERNEL);
	if (!lens)
		return -ENOMEM;
	ret = bu64253_load_init(dev, lens);
	if (ret)
		return dev_err_probe(dev, ret, "invalid or missing factory init data\n");
	lens->vdd = devm_regulator_get(dev, "vdd");
	if (IS_ERR(lens->vdd))
		return dev_err_probe(dev, PTR_ERR(lens->vdd), "failed to get VDD\n");
	mutex_init(&lens->lock);
	v4l2_i2c_subdev_init(&lens->sd, client, &bu64253_ops);
	lens->sd.internal_ops = &bu64253_internal_ops;
	lens->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
	lens->sd.entity.function = MEDIA_ENT_F_LENS;
	v4l2_ctrl_handler_init(&lens->ctrls, 1);
	lens->ctrls.lock = &lens->lock;
	focus = v4l2_ctrl_new_std(&lens->ctrls, &bu64253_ctrl_ops,
				V4L2_CID_FOCUS_ABSOLUTE, 0,
				BU64253_MAX_FOCUS, 1, 0);
	/*
	 * Do not select an uncalibrated initial target merely by opening a node.
	 * Explicit writes of the cached default must still reach the device.
	 */
	if (focus)
		focus->flags |= V4L2_CTRL_FLAG_EXECUTE_ON_WRITE;
	ret = lens->ctrls.error;
	if (ret)
		goto free_ctrls;
	lens->sd.ctrl_handler = &lens->ctrls;
	ret = media_entity_pads_init(&lens->sd.entity, 0, NULL);
	if (ret)
		goto free_ctrls;
	pm_runtime_enable(dev);
	ret = v4l2_async_register_subdev(&lens->sd);
	if (ret)
		goto disable_pm;
	return 0;

disable_pm:
	pm_runtime_disable(dev);
	media_entity_cleanup(&lens->sd.entity);
free_ctrls:
	v4l2_ctrl_handler_free(&lens->ctrls);
	mutex_destroy(&lens->lock);
	return ret;
}

static void bu64253_remove(struct i2c_client *client)
{
	struct bu64253 *lens = to_bu64253(i2c_get_clientdata(client));
	int ret;

	v4l2_async_unregister_subdev(&lens->sd);
	pm_runtime_disable(&client->dev);
	mutex_lock(&lens->lock);
	ret = bu64253_power_off(lens);
	mutex_unlock(&lens->lock);
	if (ret)
		dev_err(&client->dev, "failed to release VDD on removal: %d\n", ret);
	if (!ret)
		pm_runtime_set_suspended(&client->dev);
	media_entity_cleanup(&lens->sd.entity);
	v4l2_ctrl_handler_free(&lens->ctrls);
	mutex_destroy(&lens->lock);
}

static const struct of_device_id bu64253_of_match[] = {
	{ .compatible = "rohm,bu64253" },
	{ }
};
MODULE_DEVICE_TABLE(of, bu64253_of_match);

static const struct dev_pm_ops bu64253_pm_ops = {
	SET_RUNTIME_PM_OPS(bu64253_runtime_suspend,
			   bu64253_runtime_resume, NULL)
	SET_SYSTEM_SLEEP_PM_OPS(pm_runtime_force_suspend, pm_runtime_force_resume)
};

static struct i2c_driver bu64253_driver = {
	.driver = {
		.name = "bu64253",
		.of_match_table = bu64253_of_match,
		.pm = &bu64253_pm_ops,
	},
	.probe = bu64253_probe,
	.remove = bu64253_remove,
};
module_i2c_driver(bu64253_driver);

MODULE_DESCRIPTION("ROHM BU64253 lens controller");
MODULE_LICENSE("GPL");
