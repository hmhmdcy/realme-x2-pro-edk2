"""Prepare only an isolated IMX471 object-lifetime delta over frozen r2."""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import shutil
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepare462r3_storage449',HERE.parents[1]/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
SHARED=storage.mount.mounted_build()
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel462/r3');PRIVATE.mkdir(parents=True,exist_ok=True,mode=0o700)
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
load=lambda path:json.loads(Path(path).read_text())
assert shutil.disk_usage(SHARED).free>=2*1024**3
for part in ['r1','r2']:
    directory=HERE.parent if part=='r1' else HERE.parent/'r2'
    frozen=load(directory/(part+'-final-validation.json'))
    assert frozen==load(PRIVATE.parent/('' if part=='r1' else part)/(part+'-frozen-files-private.json'))
    for name,digest in frozen['files'].items():assert sha(directory/name)==digest,name
old=PRIVATE.parent/'r2/candidate/drivers/media/i2c/imx471.c'
assert sha(old)==next(row['candidate_sha256'] for row in frozen['candidate'] if row['path'].endswith('imx471.c'))
text=old.read_text()

LIFETIME=r'''/* The async registration and video node own one reference, distinct
 * from the bound driver's base reference. Final release can follow unbind.
 * Requires core 0064: clear sd->devnode before a callback can free sd.
 */
static LIST_HEAD(imx471_instances);
static DEFINE_MUTEX(imx471_instances_lock);

static void imx471_destroy(struct kref *ref)
{
	struct imx471 *sensor = container_of(ref, struct imx471, ref);

	if (sensor->sd_initialized)
		v4l2_subdev_cleanup(&sensor->sd);
	if (sensor->entity_initialized)
		media_entity_cleanup(&sensor->sd.entity);
	if (sensor->ctrls_initialized)
		v4l2_ctrl_handler_free(&sensor->ctrl_handler);
	mutex_lock(&imx471_instances_lock);
	list_del(&sensor->instance_entry);
	mutex_unlock(&imx471_instances_lock);
	mutex_destroy(&sensor->lock);
	put_device(sensor->dev);
	kfree(sensor);
}

static struct imx471 *imx471_alloc(struct device *dev)
{
	struct imx471 *sensor, *existing;

	sensor = kzalloc(sizeof(*sensor), GFP_KERNEL);
	if (!sensor)
		return ERR_PTR(-ENOMEM);
	sensor->dev = get_device(dev);
	kref_init(&sensor->ref);
	atomic_set(&sensor->framework_ref, 0);
	INIT_LIST_HEAD(&sensor->instance_entry);
	mutex_init(&sensor->lock);
	mutex_lock(&imx471_instances_lock);
	list_for_each_entry(existing, &imx471_instances, instance_entry) {
		if (existing->dev == dev) {
			mutex_unlock(&imx471_instances_lock);
			mutex_destroy(&sensor->lock);
			put_device(sensor->dev);
			kfree(sensor);
			return ERR_PTR(-EBUSY);
		}
	}
	list_add_tail(&sensor->instance_entry, &imx471_instances);
	mutex_unlock(&imx471_instances_lock);
	return sensor;
}

static int imx471_registered(struct v4l2_subdev *sd)
{
	struct imx471 *sensor = to_imx471(sd);
	int ret = 0;

	mutex_lock(&sensor->lock);
	if (sensor->removing || atomic_read(&sensor->framework_ref)) {
		ret = -EBUSY;
	} else {
		kref_get(&sensor->ref);
		atomic_set(&sensor->framework_ref, 1);
	}
	mutex_unlock(&sensor->lock);
	return ret;
}

static void imx471_release(struct v4l2_subdev *sd)
{
	struct imx471 *sensor = to_imx471(sd);

	/* release may be synchronous inside unregister; never acquire lock here. */
	if (atomic_xchg(&sensor->framework_ref, 0))
		kref_put(&sensor->ref, imx471_destroy);
}

'''

DETACH=r'''/* No control/state lock is held across async unregister or PM barrier.
 * The base reference protects a synchronous framework release during detach.
 * 'powered' describes only the early probe interval before PM was enabled.
 */
static void imx471_detach(struct imx471 *sensor, bool powered)
{
	mutex_lock(&sensor->lock);
	sensor->removing = true;
	mutex_unlock(&sensor->lock);
	if (sensor->sd_initialized)
		v4l2_async_unregister_subdev(&sensor->sd);
	if (sensor->pm_enabled) {
		pm_runtime_disable(sensor->dev);
		sensor->pm_enabled = false;
		powered = !pm_runtime_status_suspended(sensor->dev);
	}
	if (sensor->shared) {
		if (!imx471_shared_detach(sensor->shared))
			pm_runtime_set_suspended(sensor->dev);
		sensor->shared = NULL;
	} else if (powered && !imx471_power_off(sensor->dev)) {
		pm_runtime_set_suspended(sensor->dev);
	}
	/* r2 keeps an independently quarantined resource holder if required.
	 * Sensor memory can now follow only driver/framework object references.
	 */
	kref_put(&sensor->ref, imx471_destroy);
}

'''

PROBE=r'''static int imx471_probe(struct i2c_client *client)
{
	struct imx471 *sensor;
	bool powered = false;
	int ret;

	sensor = imx471_alloc(&client->dev);
	if (IS_ERR(sensor))
		return dev_err_probe(&client->dev, PTR_ERR(sensor),
				     "failed to allocate sensor generation\n");

	if (device_property_present(sensor->dev, "mux-states")) {
		if (!dev_of_node(sensor->dev)) {
			ret = -EINVAL;
			goto detach;
		}
		sensor->shared = imx471_shared_create(sensor->dev);
		if (IS_ERR(sensor->shared)) {
			ret = dev_err_probe(sensor->dev, PTR_ERR(sensor->shared),
					    "failed to acquire shared resources\n");
			sensor->shared = NULL;
			goto detach;
		}
	}

	ret = imx471_check_hwcfg(sensor);
	if (ret) {
		dev_err_probe(sensor->dev, ret, "failed to check hwcfg: %d\n", ret);
		goto detach;
	}
	if (!sensor->shared) {
		ret = imx471_get_regulators(sensor->dev, sensor);
		if (ret) {
			dev_err_probe(sensor->dev, ret, "failed to get regulators\n");
			goto detach;
		}
		sensor->reset_gpio = devm_gpiod_get_optional(sensor->dev, "reset", GPIOD_OUT_HIGH);
		if (IS_ERR(sensor->reset_gpio)) {
			ret = dev_err_probe(sensor->dev, PTR_ERR(sensor->reset_gpio),
					    "failed to get reset gpio\n");
			goto detach;
		}
		sensor->img_clk = devm_v4l2_sensor_clk_get(sensor->dev, NULL);
		if (IS_ERR(sensor->img_clk)) {
			ret = dev_err_probe(sensor->dev, PTR_ERR(sensor->img_clk),
					    "failed to get imaging clock\n");
			goto detach;
		}
	}
	v4l2_i2c_subdev_init(&sensor->sd, client, &imx471_subdev_ops);
	sensor->sd_initialized = true;
	sensor->regmap = devm_cci_regmap_init_i2c(client, 16);
	if (IS_ERR(sensor->regmap)) {
		ret = dev_err_probe(sensor->dev, PTR_ERR(sensor->regmap), "failed to initialize CCI\n");
		goto detach;
	}
	ret = imx471_power_on(sensor->dev);
	if (ret) {
		dev_err_probe(sensor->dev, ret, "failed to power on\n");
		goto detach;
	}
	powered = true;
	ret = imx471_identify_module(sensor);
	if (ret) {
		dev_err_probe(sensor->dev, ret, "failed to find sensor: %d\n", ret);
		goto detach;
	}
	ret = imx471_init_controls(sensor);
	if (ret) {
		dev_err_probe(sensor->dev, ret, "failed to init controls: %d\n", ret);
		goto detach;
	}
	sensor->sd.internal_ops = &imx471_internal_ops;
	sensor->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
	sensor->pad.flags = MEDIA_PAD_FL_SOURCE;
	sensor->sd.entity.function = MEDIA_ENT_F_CAM_SENSOR;
	ret = media_entity_pads_init(&sensor->sd.entity, 1, &sensor->pad);
	if (ret) {
		dev_err_probe(sensor->dev, ret, "failed to init entity pads: %d\n", ret);
		goto detach;
	}
	sensor->entity_initialized = true;
	sensor->sd.state_lock = &sensor->lock;
	ret = v4l2_subdev_init_finalize(&sensor->sd);
	if (ret) {
		dev_err_probe(sensor->dev, ret, "failed to init subdev: %d\n", ret);
		goto detach;
	}
	pm_runtime_set_active(sensor->dev);
	pm_runtime_enable(sensor->dev);
	sensor->pm_enabled = true;
	ret = v4l2_async_register_subdev_sensor(&sensor->sd);
	if (ret)
		goto detach;
	pm_runtime_idle(sensor->dev);
	return 0;

detach:
	imx471_detach(sensor, powered);
	return ret;
}

static void imx471_remove(struct i2c_client *client)
{
	struct v4l2_subdev *sd = i2c_get_clientdata(client);

	imx471_detach(to_imx471(sd), false);
}

'''

def replace(old,new):
    global text
    assert text.count(old)==1,old[:100]
    text=text.replace(old,new)

replace('#include <linux/clk.h>', '#include <linux/atomic.h>\n#include <linux/clk.h>\n#include <linux/kref.h>\n#include <linux/slab.h>')
replace('\tstruct v4l2_subdev sd;', '''\tstruct v4l2_subdev sd;
\tstruct kref ref;
\tatomic_t framework_ref;
\tstruct list_head instance_entry;
\tstruct mutex lock;
\tbool removing;
\tbool sd_initialized;
\tbool ctrls_initialized;
\tbool entity_initialized;
\tbool pm_enabled;''')
replace('static int imx471_get_regulators(',LIFETIME+'static int imx471_get_regulators(')
# All control and stream callbacks below execute under the common ctrl/state
# lock. The removal gate runs before any PM or devm-regmap use.
replace('\t/* Mode metadata controls do not program sensor registers. */', '\tif (sensor->removing)\n\t\treturn -ENODEV;\n\n\t/* Mode metadata controls do not program sensor registers. */')
replace('\tmode = imx471_find_mode(sensor, fmt->format.width, fmt->format.height);', '\tif (sensor->removing)\n\t\treturn -ENODEV;\n\n\tmode = imx471_find_mode(sensor, fmt->format.width, fmt->format.height);')
replace('\tret = pm_runtime_resume_and_get(sensor->dev);', '\tif (sensor->removing)\n\t\treturn -ENODEV;\n\n\tret = pm_runtime_resume_and_get(sensor->dev);')
replace('\tret = cci_write(sensor->regmap, IMX471_REG_MODE_SELECT,\n\t\t\tIMX471_MODE_STANDBY, NULL);', '\tif (sensor->removing)\n\t\treturn -ENODEV;\n\n\tret = cci_write(sensor->regmap, IMX471_REG_MODE_SELECT,\n\t\t\tIMX471_MODE_STANDBY, NULL);')
replace('\t.init_state = imx471_init_state,','\t.init_state = imx471_init_state,\n\t.registered = imx471_registered,\n\t.release = imx471_release,')
replace('\tv4l2_ctrl_handler_init(ctrl_hdlr, 12);', '\tv4l2_ctrl_handler_init(ctrl_hdlr, 12);\n\tsensor->ctrls_initialized = true;\n\tctrl_hdlr->lock = &sensor->lock;')
replace('error:\n\tv4l2_ctrl_handler_free(ctrl_hdlr);\n\n\treturn ctrl_hdlr->error;', 'error:\n\treturn ctrl_hdlr->error;')
start=text.index('static int imx471_probe(');end=text.index('static DEFINE_RUNTIME_DEV_PM_OPS(',start)
text=text[:start]+DETACH+PROBE+text[end:]
candidate=PRIVATE/'candidate/drivers/media/i2c/imx471.c';candidate.parent.mkdir(parents=True,exist_ok=True);candidate.write_text(text)
patch=''.join(difflib.unified_diff(old.read_text().splitlines(True),text.splitlines(True),fromfile='a/drivers/media/i2c/imx471.c',tofile='b/drivers/media/i2c/imx471.c'))
(HERE/'0001-media-imx471-retain-sensor-until-final-release.patch').write_text(patch)
def holder(s):return s[s.index('/* Routed resources outlive'):s.index('static int imx471_power_off(')]
assert holder(old.read_text())==holder(text)
report=dict(stage=462,revision='r3',r2_imx471_sha256=sha(old),candidate_sha256=sha(candidate),
    r2_holder_section_sha256=hashlib.sha256(holder(text).encode()).hexdigest(),r2_holder_unchanged=True,
    requires_r2_unmanaged_mux_and_core0064=True,phone_or_sdk_accessed=False,deployable=False)
(PRIVATE/'candidate-manifest-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
