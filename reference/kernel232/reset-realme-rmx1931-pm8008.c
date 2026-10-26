// SPDX-License-Identifier: GPL-2.0-only
/* RMX1931 board reset sequencing for PM8008 devices sharing reset address 8. */
#include <linux/err.h>
#include <linux/gpio/consumer.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/reset-controller.h>
#include <linux/slab.h>

enum rmx1931_pm8008_reset_id {
	RMX1931_PM8008_P,
	RMX1931_PM8008_Q,
	RMX1931_PM8008_NUM_RESETS,
};

struct rmx1931_pm8008_resets {
	struct reset_controller_dev rcdev;
	struct gpio_desc *p;
	struct gpio_desc *q;
	struct mutex lock;
	bool p_state_valid;
	bool p_asserted;
};

static struct rmx1931_pm8008_resets *
to_rmx1931_pm8008_resets(struct reset_controller_dev *rcdev)
{
	return container_of(rcdev, struct rmx1931_pm8008_resets, rcdev);
}

static int rmx1931_pm8008_set_reset(struct reset_controller_dev *rcdev,
				 unsigned long id, int asserted)
{
	struct rmx1931_pm8008_resets *priv = to_rmx1931_pm8008_resets(rcdev);
	int ret;

	if (id >= RMX1931_PM8008_NUM_RESETS)
		return -EINVAL;

	mutex_lock(&priv->lock);
	/* A Q reset may put it back at address 8, which an awake P occupies. */
	if (id == RMX1931_PM8008_Q) {
		/* SPMI output reads may be cached, including after a failed write. */
		if (!priv->p_state_valid) {
			ret = -EIO;
			goto out;
		}
		if (!priv->p_asserted) {
			ret = -EBUSY;
			goto out;
		}
		ret = gpiod_get_value_cansleep(priv->p);
		if (ret < 0)
			goto out;
		if (!ret) {
			ret = -EBUSY;
			goto out;
		}
	}

	/* Q starts ASIS: establish output direction on its first actual action. */
	ret = gpiod_direction_output(id == RMX1931_PM8008_P ? priv->p : priv->q,
				     asserted);
	if (id == RMX1931_PM8008_P) {
		priv->p_state_valid = !ret;
		if (!ret)
			priv->p_asserted = asserted;
	}
out:
	mutex_unlock(&priv->lock);
	return ret;
}

static int rmx1931_pm8008_assert(struct reset_controller_dev *rcdev,
			       unsigned long id)
{
	return rmx1931_pm8008_set_reset(rcdev, id, 1);
}

static int rmx1931_pm8008_deassert(struct reset_controller_dev *rcdev,
				 unsigned long id)
{
	/* P's MFD consumer must independently verify that Q is fully bound. */
	return rmx1931_pm8008_set_reset(rcdev, id, 0);
}

static int rmx1931_pm8008_status(struct reset_controller_dev *rcdev,
			       unsigned long id)
{
	struct rmx1931_pm8008_resets *priv = to_rmx1931_pm8008_resets(rcdev);
	int ret;

	if (id >= RMX1931_PM8008_NUM_RESETS)
		return -EINVAL;
	mutex_lock(&priv->lock);
	if (id == RMX1931_PM8008_P && !priv->p_state_valid)
		ret = -EIO;
	else
		ret = gpiod_get_value_cansleep(id == RMX1931_PM8008_P ? priv->p : priv->q);
	mutex_unlock(&priv->lock);
	return ret;
}

static const struct reset_control_ops rmx1931_pm8008_ops = {
	.assert = rmx1931_pm8008_assert,
	.deassert = rmx1931_pm8008_deassert,
	.status = rmx1931_pm8008_status,
};

static void rmx1931_pm8008_hold(void *data)
{
	struct rmx1931_pm8008_resets *priv = data;
	struct device *dev = priv->rcdev.dev;
	int ret;

	ret = rmx1931_pm8008_assert(&priv->rcdev, RMX1931_PM8008_P);
	if (ret) {
		dev_err(dev, "failed to hold PM8008 P in reset: %d\n", ret);
		return;
	}
	ret = rmx1931_pm8008_assert(&priv->rcdev, RMX1931_PM8008_Q);
	if (ret)
		dev_err(dev, "failed to hold PM8008 Q in reset: %d\n", ret);
}

static int rmx1931_pm8008_resets_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct rmx1931_pm8008_resets *priv;
	int ret;

	priv = devm_kzalloc(dev, sizeof(*priv), GFP_KERNEL);
	if (!priv)
		return -ENOMEM;
	mutex_init(&priv->lock);
	priv->rcdev.dev = dev;

	/* Own and hold P before Q can acquire a reset handle or access I2C. */
	priv->p = devm_gpiod_get(dev, "p-reset", GPIOD_OUT_HIGH);
	if (IS_ERR(priv->p))
		return dev_err_probe(dev, PTR_ERR(priv->p), "failed to hold P reset\n");
	priv->p_state_valid = true;
	priv->p_asserted = true;
	priv->q = devm_gpiod_get(dev, "q-reset", GPIOD_ASIS);
	if (IS_ERR(priv->q))
		return dev_err_probe(dev, PTR_ERR(priv->q), "failed to own Q reset\n");

	/* MFD managed links order consumers; rcdev unregister drains API callbacks. */
	ret = devm_add_action_or_reset(dev, rmx1931_pm8008_hold, priv);
	if (ret)
		return ret;
	priv->rcdev.owner = THIS_MODULE;
	priv->rcdev.ops = &rmx1931_pm8008_ops;
	priv->rcdev.of_node = dev->of_node;
	priv->rcdev.of_reset_n_cells = 1;
	priv->rcdev.nr_resets = RMX1931_PM8008_NUM_RESETS;
	return devm_reset_controller_register(dev, &priv->rcdev);
}

static const struct of_device_id rmx1931_pm8008_resets_of_match[] = {
	{ .compatible = "realme,rmx1931-pm8008-resets" },
	{ }
};
MODULE_DEVICE_TABLE(of, rmx1931_pm8008_resets_of_match);

static struct platform_driver rmx1931_pm8008_resets_driver = {
	.probe = rmx1931_pm8008_resets_probe,
	.driver = {
		.name = "rmx1931-pm8008-resets",
		.of_match_table = rmx1931_pm8008_resets_of_match,
	},
};
module_platform_driver(rmx1931_pm8008_resets_driver);

MODULE_DESCRIPTION("Realme RMX1931 PM8008 board reset controller");
MODULE_LICENSE("GPL");
