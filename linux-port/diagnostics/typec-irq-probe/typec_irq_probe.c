// SPDX-License-Identifier: GPL-2.0
/*
 * Diagnostic-only Type-C IRQ wake probe for the RMX1931 PM8150B port.
 *
 * This module deliberately does not register a second platform driver.  It
 * locates the already-bound Type-C device, borrows its parent SPMI regmap,
 * and can issue one controlled TYPEC_DISABLE/EN_SNK_ONLY cycle.  A one-shot
 * PM suspend notifier schedules the cycle from a non-freezable kthread so
 * the PM8150B IRQ can be tested after the system has entered s2idle.
 *
 * It is not a production workaround and must be unloaded after the test.
 */

#include <linux/atomic.h>
#include <linux/device.h>
#include <linux/err.h>
#include <linux/kthread.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/regmap.h>
#include <linux/suspend.h>
#include <linux/wait.h>

#define TYPEC_BASE_DEFAULT	0x1500
#define TYPEC_MODE_CFG_REG	0x44
#define TYPEC_DISABLE_CMD	0x01
#define EN_SNK_ONLY		0x02

static char *device_name = "c440000.spmi:pmic@2:typec@1500";
module_param(device_name, charp, 0444);
MODULE_PARM_DESC(device_name, "platform device name of the PMIC Type-C port");

static unsigned int base = TYPEC_BASE_DEFAULT;
module_param(base, uint, 0444);
MODULE_PARM_DESC(base, "PMIC Type-C register base");

static bool armed;
module_param(armed, bool, 0600);
MODULE_PARM_DESC(armed, "arm one TYPEC_DISABLE/EN_SNK_ONLY cycle at suspend");

static unsigned int delay_ms = 8000;
module_param(delay_ms, uint, 0600);
MODULE_PARM_DESC(delay_ms, "delay after PM_SUSPEND_PREPARE before the cycle");

static unsigned int off_ms = 1500;
module_param(off_ms, uint, 0600);
MODULE_PARM_DESC(off_ms, "time to keep the Type-C port disabled");

static struct device *typec_dev;
static struct regmap *typec_regmap;
static struct task_struct *probe_thread;
static DECLARE_WAIT_QUEUE_HEAD(probe_wait);
static atomic_t run_requested = ATOMIC_INIT(0);
static atomic_t suspend_requested = ATOMIC_INIT(0);

static int set_run_param(const char *val, const struct kernel_param *kp)
{
	bool run;
	int ret;

	ret = kstrtobool(val, &run);
	if (ret)
		return ret;
	if (run) {
		atomic_set(&run_requested, 1);
		wake_up_interruptible(&probe_wait);
	}
	return 0;
}

static const struct kernel_param_ops run_param_ops = {
	.set = set_run_param,
	.get = param_get_int,
};

static int run_dummy;
module_param_cb(run, &run_param_ops, &run_dummy, 0200);
MODULE_PARM_DESC(run, "write 1 to run one cycle without suspending");

static void read_state(const char *tag)
{
	unsigned int mode = 0;
	unsigned int misc = 0;
	unsigned int sm = 0;
	int ret_mode;
	int ret_misc;
	int ret_sm;

	ret_mode = regmap_read(typec_regmap, base + TYPEC_MODE_CFG_REG, &mode);
	ret_misc = regmap_read(typec_regmap, base + 0x0b, &misc);
	ret_sm = regmap_read(typec_regmap, base + 0x0a, &sm);

	pr_info("typec_irq_probe %s: mode=%d/0x%02x misc=%d/0x%02x sm=%d/0x%02x\n",
		tag, ret_mode, mode, ret_misc, misc, ret_sm, sm);
}

static int probe_thread_fn(void *unused)
{
	unsigned int original = EN_SNK_ONLY;
	unsigned int mode_after = 0;
	int ret;

	while (!kthread_should_stop()) {
		wait_event_interruptible(probe_wait,
					 atomic_read(&run_requested) ||
					 kthread_should_stop());
		if (kthread_should_stop())
			break;
		if (!atomic_xchg(&run_requested, 0))
			continue;

		if (atomic_xchg(&suspend_requested, 0) && delay_ms)
			msleep(delay_ms);

		read_state("before");
		ret = regmap_read(typec_regmap, base + TYPEC_MODE_CFG_REG,
				  &original);
		if (ret) {
			pr_err("typec_irq_probe: mode read failed: %d\n", ret);
			armed = false;
			continue;
		}

		pr_info("typec_irq_probe: disabling Type-C mode 0x%02x\n",
			original);
		ret = regmap_write(typec_regmap, base + TYPEC_MODE_CFG_REG,
				   TYPEC_DISABLE_CMD);
		if (ret) {
			pr_err("typec_irq_probe: disable write failed: %d\n", ret);
			armed = false;
			continue;
		}
		read_state("disabled");

		if (off_ms)
			msleep(off_ms);

		pr_info("typec_irq_probe: restoring Type-C mode 0x%02x\n",
			original);
		ret = regmap_write(typec_regmap, base + TYPEC_MODE_CFG_REG,
				   original);
		if (ret)
			pr_err("typec_irq_probe: restore write failed: %d\n", ret);
		read_state("restored");

		ret = regmap_read(typec_regmap, base + TYPEC_MODE_CFG_REG,
				  &mode_after);
		pr_info("typec_irq_probe: cycle complete mode_ret=%d mode=0x%02x\n",
			ret, mode_after);
		armed = false;
	}
	return 0;
}

static int typec_irq_probe_pm_notify(struct notifier_block *nb,
				     unsigned long event, void *unused)
{
	if (event == PM_SUSPEND_PREPARE && READ_ONCE(armed)) {
		atomic_set(&suspend_requested, 1);
		atomic_set(&run_requested, 1);
		wake_up_interruptible(&probe_wait);
		pr_info("typec_irq_probe: armed for delay_ms=%u off_ms=%u\n",
			delay_ms, off_ms);
	}
	return NOTIFY_DONE;
}

static struct notifier_block typec_irq_probe_pm_nb = {
	.notifier_call = typec_irq_probe_pm_notify,
};

static int __init typec_irq_probe_init(void)
{
	struct platform_device *pdev;
	int ret;

	typec_dev = bus_find_device_by_name(&platform_bus_type, NULL,
					    device_name);
	if (!typec_dev)
		return -ENODEV;
	pdev = to_platform_device(typec_dev);

	typec_regmap = dev_get_regmap(typec_dev->parent, NULL);
	if (!typec_regmap) {
		put_device(typec_dev);
		typec_dev = NULL;
		return -ENODEV;
	}

	if (of_property_read_u32(typec_dev->of_node, "reg", &base))
		base = TYPEC_BASE_DEFAULT;

	probe_thread = kthread_run(probe_thread_fn, NULL, "typec-irq-probe");
	if (IS_ERR(probe_thread)) {
		int ret = PTR_ERR(probe_thread);

		probe_thread = NULL;
		put_device(typec_dev);
		typec_dev = NULL;
		return ret;
	}

	ret = register_pm_notifier(&typec_irq_probe_pm_nb);
	if (ret) {
		kthread_stop(probe_thread);
		probe_thread = NULL;
		put_device(typec_dev);
		typec_dev = NULL;
		return ret;
	}
	pr_info("typec_irq_probe: bound %s base=0x%x\n",
		dev_name(typec_dev), base);
	return 0;
}

static void __exit typec_irq_probe_exit(void)
{
	unregister_pm_notifier(&typec_irq_probe_pm_nb);
	if (probe_thread) {
		kthread_stop(probe_thread);
		probe_thread = NULL;
	}
	if (typec_dev) {
		put_device(typec_dev);
		typec_dev = NULL;
	}
}

module_init(typec_irq_probe_init);
module_exit(typec_irq_probe_exit);

MODULE_DESCRIPTION("Diagnostic PM8150B Type-C IRQ wake probe");
MODULE_AUTHOR("Codex");
MODULE_LICENSE("GPL");
