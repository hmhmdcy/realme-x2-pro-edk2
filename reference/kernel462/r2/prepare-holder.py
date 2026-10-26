"""Prepare only isolated mux-state API and IMX471 resource-holder sources."""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r2_storage449', HERE.parents[1] / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
SHARED = storage.mount.mounted_build(); SOURCE = SHARED.parent / 'source354'
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel462/r2')
PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
R1 = PRIVATE.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())
frozen = load(HERE.parent / 'r1-final-validation.json')
for name, digest in frozen['files'].items():
    assert sha(HERE.parent / name) == digest, name
assert load(R1 / 'r1-frozen-files-private.json') == frozen
assert min(shutil.disk_usage(SHARED).free, shutil.disk_usage(PRIVATE).free) >= 2 * 1024**3

HOLDER = r'''/* Routed resources outlive sensor devres when shutdown cannot complete.
 * Only this holder owns the routed handles. An unbound failed holder is
 * deliberately retained, with its device and power-module references, until
 * reboot. No worker or subsequent probe retries its hardware operations.
 * Supplier devices must remain bound; consumer references cannot prohibit an
 * administrator from forcibly removing a supplier or its parent controller.
 */
struct imx471_shared {
	struct device *dev;
	struct list_head entry;
	struct mutex lock;
	struct mux_state *route;
	struct reset_control *reset;
	struct clk *clock;
	struct regulator *supplies[ARRAY_SIZE(imx471_supply_name)];
	unsigned long supply_mask;
	bool route_selected;
	bool reset_acquired;
	bool clock_enabled;
	bool power_module_ref;
	bool removing;
	bool quarantined;
};

static LIST_HEAD(imx471_shared_holders);
static DEFINE_MUTEX(imx471_shared_holders_lock);

/* Caller owns h->lock. Pin before selecting or changing shared hardware. */
static int imx471_shared_route_get(struct imx471_shared *h)
{
	int ret;

	if (h->route_selected)
		return 0;
	if (!try_module_get(THIS_MODULE))
		return -ENODEV;
	h->power_module_ref = true;
	ret = mux_state_try_select(h->route);
	if (ret) {
		h->power_module_ref = false;
		module_put(THIS_MODULE);
		return ret;
	}
	h->route_selected = true;
	return 0;
}

/* Caller owns h->lock. No last handle is put before successful power-off. */
static int imx471_shared_off_locked(struct imx471_shared *h)
{
	static const unsigned int order[] = { IMX471_VDIG, IMX471_VANA, IMX471_VIF };
	unsigned int i;
	int ret;

	if (h->clock_enabled) {
		clk_disable_unprepare(h->clock);
		h->clock_enabled = false;
	}
	if (h->reset_acquired) {
		ret = reset_control_assert(h->reset);
		if (ret)
			return ret;
	}
	for (i = 0; i < ARRAY_SIZE(order); i++) {
		unsigned int id = order[i];

		if (!(h->supply_mask & BIT(id)))
			continue;
		ret = regulator_disable(h->supplies[id]);
		if (ret)
			return ret;
		h->supply_mask &= ~BIT(id);
	}
	if (h->reset_acquired) {
		reset_control_release(h->reset);
		h->reset_acquired = false;
	}
	if (h->route_selected) {
		/* mux_state_deselect unlocks even on an idle-state error. Board DT
		 * uses AS_IS; power is already off before the unlock in any case.
		 */
		ret = mux_state_deselect(h->route);
		h->route_selected = false;
		if (ret)
			dev_err(h->dev, "shared route idle transition failed: %d\n", ret);
	}
	if (h->power_module_ref) {
		h->power_module_ref = false;
		module_put(THIS_MODULE);
	}
	return 0;
}

static int imx471_shared_power_off(struct imx471_shared *h)
{
	int ret;

	mutex_lock(&h->lock);
	ret = h->removing ? -ENODEV : imx471_shared_off_locked(h);
	mutex_unlock(&h->lock);
	return ret;
}

static int imx471_shared_power_on(struct imx471_shared *h)
{
	static const unsigned int order[] = { IMX471_VIF, IMX471_VANA, IMX471_VDIG };
	unsigned int i;
	int ret, cleanup;

	mutex_lock(&h->lock);
	if (h->removing) {
		ret = -ENODEV;
		goto unlock;
	}
	if (h->supply_mask || h->clock_enabled || h->reset_acquired) {
		ret = -EIO;
		goto unlock;
	}
	ret = imx471_shared_route_get(h);
	if (ret)
		goto unlock;
	ret = reset_control_acquire(h->reset);
	if (ret)
		goto power_off;
	h->reset_acquired = true;
	ret = reset_control_assert(h->reset);
	if (ret)
		goto power_off;
	ret = clk_set_rate(h->clock, IMX471_EXT_CLK);
	if (ret)
		goto power_off;
	for (i = 0; i < ARRAY_SIZE(order); i++) {
		unsigned int id = order[i];

		ret = regulator_enable(h->supplies[id]);
		if (ret)
			goto power_off;
		h->supply_mask |= BIT(id);
		usleep_range(1000, 2000);
	}
	ret = clk_prepare_enable(h->clock);
	if (ret)
		goto power_off;
	h->clock_enabled = true;
	ret = reset_control_deassert(h->reset);
	if (ret)
		goto power_off;
	usleep_range(10000, 15000);
	goto unlock;

power_off:
	cleanup = imx471_shared_off_locked(h);
	if (cleanup)
		dev_err(h->dev, "shared power-on unwind failed: %d\n", cleanup);
unlock:
	mutex_unlock(&h->lock);
	return ret;
}

/* Called only after PM disable/barrier, or before PM has ever been enabled.
 * A failed shutdown does NOT drop the holder, handle, device, or module refs.
 */
static int imx471_shared_detach(struct imx471_shared *h)
{
	unsigned int i;
	int ret;

	mutex_lock(&h->lock);
	h->removing = true;
	ret = imx471_shared_off_locked(h);
	if (ret) {
		h->quarantined = true;
		mutex_unlock(&h->lock);
		dev_err(h->dev, "shared shutdown failed: %d; holder retained until reboot\n", ret);
		return ret;
	}
	mutex_unlock(&h->lock);
	for (i = 0; i < ARRAY_SIZE(h->supplies); i++)
		if (h->supplies[i])
			regulator_put(h->supplies[i]);
	if (h->clock)
		clk_put(h->clock);
	if (h->reset)
		reset_control_put(h->reset);
	if (h->route)
		mux_state_put(h->route);
	mutex_lock(&imx471_shared_holders_lock);
	list_del(&h->entry);
	mutex_unlock(&imx471_shared_holders_lock);
	mutex_destroy(&h->lock);
	put_device(h->dev);
	kfree(h);
	return 0;
}

static struct imx471_shared *imx471_shared_create(struct device *dev)
{
	struct imx471_shared *h, *existing;
	unsigned int i;
	int ret;

	h = kzalloc(sizeof(*h), GFP_KERNEL);
	if (!h)
		return ERR_PTR(-ENOMEM);
	h->dev = get_device(dev);
	INIT_LIST_HEAD(&h->entry);
	mutex_init(&h->lock);
	mutex_lock(&imx471_shared_holders_lock);
	list_for_each_entry(existing, &imx471_shared_holders, entry) {
		if (existing->dev == dev) {
			mutex_unlock(&imx471_shared_holders_lock);
			mutex_destroy(&h->lock);
			put_device(h->dev);
			kfree(h);
			return ERR_PTR(-EBUSY);
		}
	}
	list_add_tail(&h->entry, &imx471_shared_holders);
	mutex_unlock(&imx471_shared_holders_lock);
	h->route = mux_state_get(dev, "csi-route");
	if (IS_ERR(h->route)) {
		ret = PTR_ERR(h->route);
		h->route = NULL;
		goto detach;
	}
	mutex_lock(&h->lock);
	ret = imx471_shared_route_get(h);
	mutex_unlock(&h->lock);
	if (ret) {
		if (ret == -EBUSY)
			ret = -EPROBE_DEFER;
		goto detach;
	}
	/* A provider's first GPIO setup may occur before consumer acquisition.
	 * Both providers must be bootstrapped with every old consumer stopped.
	 */
	h->reset = reset_control_get_exclusive_released(dev, NULL);
	if (IS_ERR(h->reset)) {
		ret = PTR_ERR(h->reset);
		h->reset = NULL;
		goto detach;
	}
	h->clock = clk_get(dev, NULL);
	if (IS_ERR(h->clock)) {
		ret = PTR_ERR(h->clock);
		h->clock = NULL;
		goto detach;
	}
	for (i = 0; i < ARRAY_SIZE(h->supplies); i++) {
		h->supplies[i] = regulator_get(dev, imx471_supply_name[i]);
		if (IS_ERR(h->supplies[i])) {
			ret = PTR_ERR(h->supplies[i]);
			h->supplies[i] = NULL;
			goto detach;
		}
	}
	return h;

detach:
	imx471_shared_detach(h);
	return ERR_PTR(ret);
}

'''

def replace_once(text, old, new):
    assert text.count(old) == 1, old[:120]
    return text.replace(old, new)

def prepare():
    # Capture only the relevant lifetime/source APIs; source-view creation is separate.
    files = ['drivers/mux/core.c', 'include/linux/mux/consumer.h', 'include/linux/reset.h',
             'drivers/reset/core.c', 'drivers/clk/clk.c', 'drivers/regulator/core.c',
             'drivers/base/dd.c', 'drivers/media/v4l2-core/v4l2-subdev.c',
             'drivers/of/property.c', 'drivers/mux/gpio.c', 'drivers/reset/reset-gpio.c']
    rows = []
    for name in files:
        src = SOURCE / name; dst = PRIVATE / 'original' / name
        dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(src.read_bytes())
        rows.append(dict(path=name, sha256=sha(src), bytes=src.stat().st_size))
    symvers = (SHARED / 'Module.symvers').read_text()
    assert not any('\tmux_state_get\t' in line or '\tmux_state_put\t' in line for line in symvers.splitlines())
    core = (PRIVATE / 'original/drivers/mux/core.c').read_text()
    core = replace_once(core, 'static struct mux_state *\nmux_state_get(struct device *dev, const char *mux_name, bool optional,',
                         'static struct mux_state *\n__mux_state_get(struct device *dev, const char *mux_name, bool optional,')
    core = replace_once(core, 'static void mux_state_put(struct mux_state *mstate)', 'void mux_state_put(struct mux_state *mstate)')
    core = replace_once(core, '\tkfree(mstate);\n}\n\nstatic void devm_mux_state_release', '\tkfree(mstate);\n}\nEXPORT_SYMBOL_GPL(mux_state_put);\n\nstatic void devm_mux_state_release')
    core = replace_once(core, '\tmstate = mux_state_get(dev, mux_name, optional, np);', '\tmstate = __mux_state_get(dev, mux_name, optional, np);')
    public = '''/**
 * mux_state_get() - Get an unmanaged multiplexer state for a device.
 * @dev: The device that needs a multiplexer state.
 * @mux_name: The name identifying the multiplexer state.
 *
 * Return: A mux-state pointer, or an ERR_PTR with a negative errno.
 * Caller must deselect a successfully selected state before mux_state_put().
 * This gets the mux-chip device reference; it does not prevent supplier unbind.
 */
struct mux_state *mux_state_get(struct device *dev, const char *mux_name)
{
\treturn __mux_state_get(dev, mux_name, false, NULL);
}
EXPORT_SYMBOL_GPL(mux_state_get);

'''
    core = replace_once(core, '/*\n * mux_state_put() - Put away the mux-state for good.', public + '/**\n * mux_state_put() - Put away the mux-state for good.')
    # Fix the internal documentation name to agree with the renamed private helper.
    core = replace_once(core, ' * mux_state_get() - Get the mux-state for a device.', ' * __mux_state_get() - Get the mux-state for a device.')
    header = (PRIVATE / 'original/include/linux/mux/consumer.h').read_text()
    header = replace_once(header, 'struct mux_state;\n', 'struct mux_state;\nstruct device_node;\n')
    header = replace_once(header, 'struct mux_state *\ndevm_mux_state_get_from_np',
                          'struct mux_state *mux_state_get(struct device *dev, const char *mux_name);\nvoid mux_state_put(struct mux_state *mstate);\n\nstruct mux_state *\ndevm_mux_state_get_from_np')
    header = replace_once(header, 'static inline struct mux_state *devm_mux_state_get(struct device *dev, const char *mux_name)',
                          'static inline struct mux_state *mux_state_get(struct device *dev, const char *mux_name)\n{\n\treturn ERR_PTR(-EOPNOTSUPP);\n}\nstatic inline void mux_state_put(struct mux_state *mstate) {}\n\nstatic inline struct mux_state *devm_mux_state_get_from_np(struct device *dev,\n\t\t\t\t\t\t    const char *mux_name,\n\t\t\t\t\t\t    struct device_node *np)')
    candidate = PRIVATE / 'candidate'
    for name, text in [('drivers/mux/core.c', core), ('include/linux/mux/consumer.h', header)]:
        dst = candidate / name; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_text(text)
    sensor = (R1 / 'candidate/drivers/media/i2c/imx471.c').read_text()
    sensor = replace_once(sensor, '#include <linux/module.h>', '#include <linux/module.h>\n#include <linux/list.h>\n#include <linux/mutex.h>')
    sensor = replace_once(sensor, '\tstruct reset_control *reset;\n\tstruct mux_state *route;\n\tunsigned long supply_mask;\n\tbool route_selected;\n\tbool reset_acquired;\n\tbool clock_enabled;', '\tstruct imx471_shared *shared;')
    sensor = replace_once(sensor, 'struct imx471 {', 'struct imx471_shared;\n\nstruct imx471 {')
    start = sensor.index('/* Shared-route boards never use'); end = sensor.index('static int imx471_power_off(', start)
    sensor = sensor[:start] + HOLDER + sensor[end:]
    sensor = replace_once(sensor, '\tif (sensor->route)\n\t\treturn imx471_shared_power_off(sensor);', '\tif (sensor->shared)\n\t\treturn imx471_shared_power_off(sensor->shared);')
    sensor = replace_once(sensor, '\tif (sensor->route)\n\t\treturn imx471_shared_power_on(sensor);', '\tif (sensor->shared)\n\t\treturn imx471_shared_power_on(sensor->shared);')
    sensor = replace_once(sensor, '\tclk = devm_v4l2_sensor_clk_get(sensor->dev, NULL);', '\tclk = sensor->shared ? sensor->shared->clock :\n\t\tdevm_v4l2_sensor_clk_get(sensor->dev, NULL);')
    sensor = replace_once(sensor, '\tif (sensor->route) {\n\t\tret = clk_set_rate', '\tif (sensor->shared) {\n\t\tret = clk_set_rate')
    start = sensor.index('static int imx471_probe('); end = sensor.index('static DEFINE_RUNTIME_DEV_PM_OPS(', start)
    probe = sensor[start:end]
    probe = replace_once(probe, '\tret = imx471_init_shared_route(sensor);\n\tif (ret)\n\t\treturn dev_err_probe(sensor->dev, ret, "failed to acquire shared route\\n");', '''\tif (device_property_present(sensor->dev, "mux-states")) {
\t\tif (!dev_of_node(sensor->dev))
\t\t\treturn -EINVAL;
\t\tsensor->shared = imx471_shared_create(sensor->dev);
\t\tif (IS_ERR(sensor->shared))
\t\t\treturn dev_err_probe(sensor->dev, PTR_ERR(sensor->shared),
\t\t\t\t\t     "failed to acquire shared resources\\n");
\t}''')
    probe = replace_once(probe, '\tif (ret)\n\t\treturn dev_err_probe(sensor->dev, ret,\n\t\t\t\t     "failed to check hwcfg: %d\\n", ret);', '\tif (ret) {\n\t\tdev_err_probe(sensor->dev, ret, "failed to check hwcfg: %d\\n", ret);\n\t\tgoto error_shared_detach;\n\t}')
    a = probe.index('\tret = imx471_get_regulators('); b = probe.index('\n\tv4l2_i2c_subdev_init(', a)
    legacy = '''\tif (!sensor->shared) {
\t\tret = imx471_get_regulators(sensor->dev, sensor);
\t\tif (ret)
\t\t\treturn dev_err_probe(sensor->dev, ret, "failed to get regulators\\n");
\t\tsensor->reset_gpio = devm_gpiod_get_optional(sensor->dev, "reset", GPIOD_OUT_HIGH);
\t\tif (IS_ERR(sensor->reset_gpio))
\t\t\treturn dev_err_probe(sensor->dev, PTR_ERR(sensor->reset_gpio),
\t\t\t\t\t     "failed to get reset gpio\\n");
\t\tsensor->img_clk = devm_v4l2_sensor_clk_get(sensor->dev, NULL);
\t\tif (IS_ERR(sensor->img_clk))
\t\t\treturn dev_err_probe(sensor->dev, PTR_ERR(sensor->img_clk),
\t\t\t\t\t     "failed to get imaging clock\\n");
\t}
'''
    probe = probe[:a] + legacy + probe[b:]
    probe = replace_once(probe, '\tif (IS_ERR(sensor->regmap))\n\t\treturn dev_err_probe(sensor->dev, PTR_ERR(sensor->regmap),\n\t\t\t\t     "failed to initialize CCI\\n");', '\tif (IS_ERR(sensor->regmap)) {\n\t\tret = dev_err_probe(sensor->dev, PTR_ERR(sensor->regmap),\n\t\t\t\t    "failed to initialize CCI\\n");\n\t\tgoto error_shared_detach;\n\t}')
    probe = replace_once(probe, '\tif (ret)\n\t\treturn dev_err_probe(sensor->dev, ret,\n\t\t\t\t     "failed to power on\\n");', '\tif (ret) {\n\t\tdev_err_probe(sensor->dev, ret, "failed to power on\\n");\n\t\tgoto error_shared_detach;\n\t}')
    a = probe.index('error_power_off:\n'); b = probe.index('static void imx471_remove(', a)
    probe = probe[:a] + '''error_power_off:
\tif (!sensor->shared && !imx471_power_off(sensor->dev))
\t\tpm_runtime_set_suspended(sensor->dev);
error_shared_detach:
\tif (sensor->shared) {
\t\tif (!imx471_shared_detach(sensor->shared))
\t\t\tpm_runtime_set_suspended(sensor->dev);
\t\tsensor->shared = NULL;
\t}
\treturn ret;
}

''' + probe[b:]
    a = probe.index('\tif (!pm_runtime_status_suspended(')
    probe = probe[:a] + '''\tif (sensor->shared) {
\t\tif (!imx471_shared_detach(sensor->shared))
\t\t\tpm_runtime_set_suspended(&client->dev);
\t\tsensor->shared = NULL;
\t} else if (!pm_runtime_status_suspended(&client->dev)) {
\t\timx471_power_off(&client->dev);
\t\tpm_runtime_set_suspended(&client->dev);
\t}
}

'''
    sensor = sensor[:start] + probe + sensor[end:]
    name = 'drivers/media/i2c/imx471.c'; dst = candidate / name
    dst.parent.mkdir(parents=True, exist_ok=True); dst.write_text(sensor)
    changed = []
    for name in ['drivers/mux/core.c', 'include/linux/mux/consumer.h', 'drivers/media/i2c/imx471.c']:
        base = R1 / 'candidate' / name if name.endswith('imx471.c') else PRIVATE / 'original' / name
        path = candidate / name
        changed.append(dict(path=name, r1_or_original_sha256=sha(base), candidate_sha256=sha(path)))
        patch = ''.join(difflib.unified_diff(base.read_text().splitlines(True), path.read_text().splitlines(True), fromfile='a/'+name, tofile='b/'+name))
        patchname = '0002-media-imx471-retain-resource-holder.patch' if name.endswith('imx471.c') else None
        if patchname: (HERE / patchname).write_text(patch)
    api_patch = ''.join(''.join(difflib.unified_diff((PRIVATE/'original'/name).read_text().splitlines(True), (candidate/name).read_text().splitlines(True), fromfile='a/'+name, tofile='b/'+name)) for name in ['drivers/mux/core.c', 'include/linux/mux/consumer.h'])
    (HERE / '0001-mux-export-unmanaged-state-handles.patch').write_text(api_patch)
    report = dict(stage=462, revision='r2', files=changed, inspected_sources=rows,
                  source_head=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD']).decode().strip(),
                  r1_frozen_files_unchanged=True, old363_missing_new_exports=True,
                  mux_core_builtin_new_image_required=True, fifth_node_added=False,
                  source354_unchanged=True, phone_or_sdk_accessed=False, deployable=False)
    (PRIVATE / 'candidate-manifest-private.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(files=changed, new_image_required=True, r1_unchanged=True, deployable=False)), flush=True)

if __name__ == '__main__': prepare()
