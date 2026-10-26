// SPDX-License-Identifier: GPL-2.0-only
/*
 * ROHM BU64253 independent lifetime candidate. Requires V4L2 core fix 0064.
 * Validation is recorded alongside this source; no hardware acceptance implied.
 */

#include <linux/delay.h>
#include <linux/firmware.h>
#include <linux/i2c.h>
#include <linux/kref.h>
#include <linux/list.h>
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
	/* Never acquire this from a runtime PM callback or control callback. */
	struct mutex lifecycle_lock;
	struct kref ref;
	struct device *dev;
	struct list_head instance_entry;
	atomic_t framework_ref;
	unsigned int open_count;
	bool removing;
	bool ctrls_initialized;
	bool entity_initialized;
	struct regulator *vdd;
	struct bu64253_init init[BU64253_INIT_COUNT];
	bool init_valid;
	u16 target;
	bool target_valid;
	bool supply_enabled;
	bool power_module_ref;
	bool quarantined;
};

static inline struct bu64253 *to_bu64253(struct v4l2_subdev *sd)
{
	return container_of(sd, struct bu64253, sd);
}

/* All generations remain listed until final destruction, so a late FD or a
 * quarantined powered generation blocks same-device rebind. Failed VDD-off is
 * retained until reboot: no retry worker, force-disable or automatic PM reset.
 * The power module reference is acquired BEFORE regulator_enable, never remove.
 */
static LIST_HEAD(bu64253_instances);
static DEFINE_MUTEX(bu64253_instances_lock);

static void bu64253_destroy(struct kref *ref)
{
	struct bu64253 *lens = container_of(ref, struct bu64253, ref);

	/* The detach failure path must retain its base kref. Never put an enabled
	 * regulator even if a future caller breaks that reference invariant.
	 */
	if (WARN_ON(lens->supply_enabled || lens->power_module_ref))
		return;
	if (lens->entity_initialized)
		media_entity_cleanup(&lens->sd.entity);
	if (lens->ctrls_initialized)
		v4l2_ctrl_handler_free(&lens->ctrls);
	if (lens->vdd)
		regulator_put(lens->vdd);
	mutex_destroy(&lens->lifecycle_lock);
	mutex_destroy(&lens->lock);
	mutex_lock(&bu64253_instances_lock);
	if (!list_empty(&lens->instance_entry))
		list_del(&lens->instance_entry);
	mutex_unlock(&bu64253_instances_lock);
	put_device(lens->dev);
	kfree(lens);
}

static int bu64253_registered(struct v4l2_subdev *sd)
{
	struct bu64253 *lens = to_bu64253(sd);
	int ret = 0;

	mutex_lock(&lens->lock);
	/* Do not reuse this sd while a previous registration has open users. */
	if (lens->removing || atomic_read(&lens->framework_ref)) {
		ret = -EBUSY;
	} else {
		kref_get(&lens->ref);
		atomic_set(&lens->framework_ref, 1);
	}
	mutex_unlock(&lens->lock);
	return ret;
}

static void bu64253_release(struct v4l2_subdev *sd)
{
	struct bu64253 *lens = to_bu64253(sd);

	/* Requires core fix 0064. No sd access is valid after the final put. */
	if (atomic_xchg(&lens->framework_ref, 0))
		kref_put(&lens->ref, bu64253_destroy);
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

	if (lens->removing)
		return -ENODEV;
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
	lens->power_module_ref = false;
	module_put(THIS_MODULE);

	return 0;
}

static int bu64253_runtime_resume(struct device *dev)
{
	struct bu64253 *lens = to_bu64253(dev_get_drvdata(dev));
	unsigned int i;
	int ret, cleanup;

	mutex_lock(&lens->lock);
	if (lens->removing) {
		ret = -ENODEV;
		goto unlock;
	}
	if (!lens->init_valid) {
		ret = -ENODATA;
		goto unlock;
	}
	/* Recover an earlier failed rollback without accumulating references. */
	ret = bu64253_power_off(lens);
	if (ret)
		goto unlock;
	if (!try_module_get(THIS_MODULE)) {
		ret = -ENODEV;
		goto unlock;
	}
	lens->power_module_ref = true;
	ret = regulator_enable(lens->vdd);
	if (ret) {
		lens->power_module_ref = false;
		module_put(THIS_MODULE);
		goto unlock;
	}
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
	struct bu64253 *lens = to_bu64253(sd);
	int ret;

	mutex_lock(&lens->lifecycle_lock);
	ret = lens->removing ? -ENODEV : pm_runtime_resume_and_get(sd->dev);
	if (!ret)
		lens->open_count++;
	mutex_unlock(&lens->lifecycle_lock);
	return ret;
}

static int bu64253_close(struct v4l2_subdev *sd, struct v4l2_subdev_fh *fh)
{
	struct bu64253 *lens = to_bu64253(sd);

	mutex_lock(&lens->lifecycle_lock);
	/* Removal already balanced every old-open PM reference. In particular,
	 * a late close must not decrement a new binding's PM usage count.
	 */
	if (!lens->removing) {
		if (WARN_ON(!lens->open_count))
			goto unlock;
		lens->open_count--;
		pm_runtime_put(sd->dev);
	}
unlock:
	mutex_unlock(&lens->lifecycle_lock);
	return 0;
}

static const struct v4l2_subdev_internal_ops bu64253_internal_ops = {
	.registered = bu64253_registered,
	.release = bu64253_release,
	.open = bu64253_open,
	.close = bu64253_close,
};

/* Caller still owns the probe/driver kref. No driver lock surrounds a PM
 * barrier, because callbacks take lens->lock. lifecycle_lock is not used by PM.
 */
static void bu64253_detach(struct bu64253 *lens)
{
	int ret;

	mutex_lock(&lens->lifecycle_lock);
	mutex_lock(&lens->lock);
	lens->removing = true;
	mutex_unlock(&lens->lock);
	v4l2_async_unregister_subdev(&lens->sd);
	while (lens->open_count) {
		pm_runtime_put_noidle(lens->dev);
		lens->open_count--;
	}
	pm_runtime_disable(lens->dev);
	mutex_lock(&lens->lock);
	ret = bu64253_power_off(lens);
	mutex_unlock(&lens->lock);
	if (!ret)
		pm_runtime_set_suspended(lens->dev);
	mutex_unlock(&lens->lifecycle_lock);
	if (ret) {
		/* Void remove cannot refuse unbind. Keep the enabled regulator,
		 * device, module and driver references; do not devm-put VDD.
		 * Probe rejects this same device until reboot. The rail may be on.
		 */
		dev_err(lens->dev, "VDD disable failed: %d; quarantined until reboot\n", ret);
		lens->quarantined = true;
		return;
	}
	kref_put(&lens->ref, bu64253_destroy);
}

static const struct v4l2_subdev_ops bu64253_ops = { };

static int bu64253_probe(struct i2c_client *client)
{
	struct device *dev = &client->dev;
	struct bu64253 *lens, *existing;
	struct v4l2_ctrl *focus;
	int ret;

	if (!i2c_check_functionality(client->adapter, I2C_FUNC_I2C))
		return -EOPNOTSUPP;
	lens = kzalloc(sizeof(*lens), GFP_KERNEL);
	if (!lens)
		return -ENOMEM;
	kref_init(&lens->ref);
	atomic_set(&lens->framework_ref, 0);
	INIT_LIST_HEAD(&lens->instance_entry);
	lens->dev = get_device(dev);
	mutex_init(&lens->lock);
	mutex_init(&lens->lifecycle_lock);
	mutex_lock(&bu64253_instances_lock);
	list_for_each_entry(existing, &bu64253_instances, instance_entry) {
		if (existing->dev == dev) {
			mutex_unlock(&bu64253_instances_lock);
			ret = -EBUSY;
			dev_err_probe(dev, ret, "previous lens generation still retained\n");
			goto put_lens;
		}
	}
	list_add_tail(&lens->instance_entry, &bu64253_instances);
	mutex_unlock(&bu64253_instances_lock);
	ret = bu64253_load_init(dev, lens);
	if (ret) {
		dev_err_probe(dev, ret, "invalid or missing factory init data\n");
		goto put_lens;
	}
	lens->vdd = regulator_get(dev, "vdd");
	if (IS_ERR(lens->vdd)) {
		ret = PTR_ERR(lens->vdd);
		lens->vdd = NULL;
		dev_err_probe(dev, ret, "failed to get VDD\n");
		goto put_lens;
	}
	v4l2_i2c_subdev_init(&lens->sd, client, &bu64253_ops);
	lens->sd.internal_ops = &bu64253_internal_ops;
	lens->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
	lens->sd.entity.function = MEDIA_ENT_F_LENS;
	v4l2_ctrl_handler_init(&lens->ctrls, 1);
	lens->ctrls_initialized = true;
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
		goto put_lens;
	lens->sd.ctrl_handler = &lens->ctrls;
	ret = media_entity_pads_init(&lens->sd.entity, 0, NULL);
	if (ret)
		goto put_lens;
	lens->entity_initialized = true;
	pm_runtime_enable(dev);
	ret = v4l2_async_register_subdev(&lens->sd);
	if (ret)
		goto disable_pm;
	return 0;

disable_pm:
	bu64253_detach(lens);
	return ret;
put_lens:
	kref_put(&lens->ref, bu64253_destroy);
	return ret;
}

static void bu64253_remove(struct i2c_client *client)
{
	bu64253_detach(to_bu64253(i2c_get_clientdata(client)));
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
