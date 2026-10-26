"""Generate a private, uncompiled BU64253 lifetime/quarantine review draft."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel453/schema')
original = (HERE / 'bu64253.c').read_text()
text = original

def change(old, new):
    global text
    assert text.count(old) == 1, old
    text = text.replace(old, new)

change('#include <linux/i2c.h>', '#include <linux/i2c.h>\n#include <linux/kref.h>\n#include <linux/list.h>')
change('\tstruct mutex lock;\n', '''\tstruct mutex lock;
\t/* Never acquire this from a runtime PM callback or control callback. */
\tstruct mutex lifecycle_lock;
\tstruct kref ref;
\tstruct device *dev;
\tstruct list_head quarantine_entry;
\tatomic_t framework_ref;
\tunsigned int open_count;
\tbool removing;
\tbool ctrls_initialized;
\tbool entity_initialized;
''')
change('static int bu64253_write(', '''/* Review-only policy: an unremoved VDD reference is quarantined until reboot.
 * There is deliberately no retry worker, force-disable or automatic PM reset.
 * This policy still needs product review before this draft can be deployed.
 */
static LIST_HEAD(bu64253_quarantine);
static DEFINE_MUTEX(bu64253_quarantine_lock);

static void bu64253_destroy(struct kref *ref)
{
\tstruct bu64253 *lens = container_of(ref, struct bu64253, ref);

\t/* A powered object retains its driver reference in the quarantine list. */
\tWARN_ON(lens->supply_enabled);
\tif (lens->entity_initialized)
\t\tmedia_entity_cleanup(&lens->sd.entity);
\tif (lens->ctrls_initialized)
\t\tv4l2_ctrl_handler_free(&lens->ctrls);
\tif (lens->vdd)
\t\tregulator_put(lens->vdd);
\tmutex_destroy(&lens->lifecycle_lock);
\tmutex_destroy(&lens->lock);
\tput_device(lens->dev);
\tkfree(lens);
}

static int bu64253_registered(struct v4l2_subdev *sd)
{
\tstruct bu64253 *lens = to_bu64253(sd);
\tint ret = 0;

\tmutex_lock(&lens->lock);
\t/* Do not reuse this sd while a previous registration has open users. */
\tif (lens->removing || atomic_read(&lens->framework_ref)) {
\t\tret = -EBUSY;
\t} else {
\t\tkref_get(&lens->ref);
\t\tatomic_set(&lens->framework_ref, 1);
\t}
\tmutex_unlock(&lens->lock);
\treturn ret;
}

static void bu64253_release(struct v4l2_subdev *sd)
{
\tstruct bu64253 *lens = to_bu64253(sd);

\t/* Requires core fix 0064. No sd access is valid after the final put. */
\tif (atomic_xchg(&lens->framework_ref, 0))
\t\tkref_put(&lens->ref, bu64253_destroy);
}

static int bu64253_write(''')
change('\tif (ctrl->id != V4L2_CID_FOCUS_ABSOLUTE)', '\tif (lens->removing)\n\t\treturn -ENODEV;\n\tif (ctrl->id != V4L2_CID_FOCUS_ABSOLUTE)')
change('\tlens->supply_enabled = false;\n', '\tlens->supply_enabled = false;\n\tmodule_put(THIS_MODULE);\n')
change('\tif (!lens->init_valid) {', '\tif (lens->removing) {\n\t\tret = -ENODEV;\n\t\tgoto unlock;\n\t}\n\tif (!lens->init_valid) {')
change('\tret = regulator_enable(lens->vdd);\n\tif (ret)\n\t\tgoto unlock;', '''\tif (!try_module_get(THIS_MODULE)) {
\t\tret = -ENODEV;
\t\tgoto unlock;
\t}
\tret = regulator_enable(lens->vdd);
\tif (ret) {
\t\tmodule_put(THIS_MODULE);
\t\tgoto unlock;
\t}''')
start = text.index('static int bu64253_open(')
end = text.index('static const struct v4l2_subdev_ops bu64253_ops', start)
text = text[:start] + '''static int bu64253_open(struct v4l2_subdev *sd, struct v4l2_subdev_fh *fh)
{
\tstruct bu64253 *lens = to_bu64253(sd);
\tint ret;

\tmutex_lock(&lens->lifecycle_lock);
\tret = lens->removing ? -ENODEV : pm_runtime_resume_and_get(sd->dev);
\tif (!ret)
\t\tlens->open_count++;
\tmutex_unlock(&lens->lifecycle_lock);
\treturn ret;
}

static int bu64253_close(struct v4l2_subdev *sd, struct v4l2_subdev_fh *fh)
{
\tstruct bu64253 *lens = to_bu64253(sd);

\tmutex_lock(&lens->lifecycle_lock);
\t/* Removal already balanced every old-open PM reference. In particular,
\t * a late close must not decrement a new binding's PM usage count.
\t */
\tif (!lens->removing) {
\t\tif (WARN_ON(!lens->open_count))
\t\t\tgoto unlock;
\t\tlens->open_count--;
\t\tpm_runtime_put(sd->dev);
\t}
unlock:
\tmutex_unlock(&lens->lifecycle_lock);
\treturn 0;
}

static const struct v4l2_subdev_internal_ops bu64253_internal_ops = {
\t.registered = bu64253_registered,
\t.release = bu64253_release,
\t.open = bu64253_open,
\t.close = bu64253_close,
};

/* Caller still owns the probe/driver kref. No driver lock surrounds a PM
 * barrier, because callbacks take lens->lock. lifecycle_lock is not used by PM.
 */
static void bu64253_detach(struct bu64253 *lens)
{
\tint ret;

\tmutex_lock(&lens->lifecycle_lock);
\tmutex_lock(&lens->lock);
\tlens->removing = true;
\tmutex_unlock(&lens->lock);
\tv4l2_async_unregister_subdev(&lens->sd);
\twhile (lens->open_count) {
\t\tpm_runtime_put_noidle(lens->dev);
\t\tlens->open_count--;
\t}
\tpm_runtime_disable(lens->dev);
\tmutex_lock(&lens->lock);
\tret = bu64253_power_off(lens);
\tmutex_unlock(&lens->lock);
\tif (!ret)
\t\tpm_runtime_set_suspended(lens->dev);
\tmutex_unlock(&lens->lifecycle_lock);
\tif (ret) {
\t\t/* Void remove cannot refuse unbind. Keep the enabled regulator,
\t\t * device, module and driver references; do not devm-put VDD.
\t\t * Probe rejects this same device until reboot. The rail may be on.
\t\t */
\t\tdev_err(lens->dev, "VDD disable failed: %d; quarantined until reboot\\n", ret);
\t\tmutex_lock(&bu64253_quarantine_lock);
\t\tlist_add_tail(&lens->quarantine_entry, &bu64253_quarantine);
\t\tmutex_unlock(&bu64253_quarantine_lock);
\t\treturn;
\t}
\tkref_put(&lens->ref, bu64253_destroy);
}

''' + text[end:]
change('\tstruct bu64253 *lens;\n', '\tstruct bu64253 *lens, *quarantined;\n')
change('\tlens = devm_kzalloc(dev, sizeof(*lens), GFP_KERNEL);', '''\tmutex_lock(&bu64253_quarantine_lock);
\tlist_for_each_entry(quarantined, &bu64253_quarantine, quarantine_entry) {
\t\tif (quarantined->dev == dev) {
\t\t\tmutex_unlock(&bu64253_quarantine_lock);
\t\t\treturn dev_err_probe(dev, -EBUSY, "VDD fault quarantined until reboot\\n");
\t\t}
\t}
\tmutex_unlock(&bu64253_quarantine_lock);
\tlens = kzalloc(sizeof(*lens), GFP_KERNEL);''')
change('\tret = bu64253_load_init(dev, lens);\n\tif (ret)\n\t\treturn dev_err_probe(dev, ret, "invalid or missing factory init data\\n");\n\tlens->vdd = devm_regulator_get(dev, "vdd");\n\tif (IS_ERR(lens->vdd))\n\t\treturn dev_err_probe(dev, PTR_ERR(lens->vdd), "failed to get VDD\\n");\n\tmutex_init(&lens->lock);', '''\tkref_init(&lens->ref);
\tatomic_set(&lens->framework_ref, 0);
\tINIT_LIST_HEAD(&lens->quarantine_entry);
\tlens->dev = get_device(dev);
\tmutex_init(&lens->lock);
\tmutex_init(&lens->lifecycle_lock);
\tret = bu64253_load_init(dev, lens);
\tif (ret) {
\t\tdev_err_probe(dev, ret, "invalid or missing factory init data\\n");
\t\tgoto put_lens;
\t}
\tlens->vdd = regulator_get(dev, "vdd");
\tif (IS_ERR(lens->vdd)) {
\t\tret = PTR_ERR(lens->vdd);
\t\tlens->vdd = NULL;
\t\tdev_err_probe(dev, ret, "failed to get VDD\\n");
\t\tgoto put_lens;
\t}''')
change('\tv4l2_ctrl_handler_init(&lens->ctrls, 1);', '\tv4l2_ctrl_handler_init(&lens->ctrls, 1);\n\tlens->ctrls_initialized = true;')
text = text.replace('goto free_ctrls;', 'goto put_lens;')
change('\tpm_runtime_enable(dev);', '\tlens->entity_initialized = true;\n\tpm_runtime_enable(dev);')
start = text.index('disable_pm:\n')
end = text.index('static const struct of_device_id', start)
text = text[:start] + '''disable_pm:
\tbu64253_detach(lens);
\treturn ret;
put_lens:
\tkref_put(&lens->ref, bu64253_destroy);
\treturn ret;
}

static void bu64253_remove(struct i2c_client *client)
{
\tbu64253_detach(to_bu64253(i2c_get_clientdata(client)));
}

''' + text[end:]
assert (HERE / 'bu64253.c').read_text() == original
PRIVATE.mkdir(exist_ok=True)
candidate = PRIVATE / 'bu64253-lifetime-quarantine-review-private.c'
candidate.write_text(text)
patch = ''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
    fromfile='a/drivers/media/i2c/bu64253.c', tofile='b/drivers/media/i2c/bu64253.c'))
(PRIVATE / 'bu64253-lifetime-quarantine-review-private.patch').write_text(patch)
report = dict(stage=453, scope='uncompiled private design draft, not approved for loading',
    original_driver_sha256=hashlib.sha256(original.encode()).hexdigest(),
    private_candidate_sha256=hashlib.sha256(text.encode()).hexdigest(),
    requires_core_patch_0064=True, manual_driver_and_framework_refs=True,
    late_close_does_not_touch_rebound_device_pm=True, remove_disable_fault_policy='retain regulator/device/module/driver references; block same-device probe until reboot',
    quarantine_is_not_successful_power_off_or_automatic_recovery=True,
    fault_policy_requires_review=True, c_compiled=False, framework_runtime_tested=False,
    kernel_pm_lockdep_or_hardware_tested=False, original_driver_modified=False,
    sdk_or_phone_accessed=False)
(HERE / 'schema-lifetime-draft.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
