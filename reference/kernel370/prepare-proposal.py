"""Separate A5 quiescence from DMA/PM retirement; prepare an opt-in held failure."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';relative='drivers/media/platform/qcom/camss/'
parent=json.loads((HERE.parent/'kernel369/source-state.json').read_text())['commit']
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
before={n:(source/relative/n).read_text() for n in ['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c']}
after=dict(before)
s=after['camss-icp-a5-boot.c']
assert s.count('static int stop_locked(struct camss_a5 *a5)')==1
s=s.replace('static int stop_locked(struct camss_a5 *a5)','static int quiesce_locked(struct camss_a5 *a5)',1)
anchor='''\tcapture_shared_state(a5);
\t/* Retire all firmware DMA aliases while the supplier is still powered.'''
new='''\tcapture_shared_state(a5);
\treturn 0;
}

static int stop_locked(struct camss_a5 *a5)
{
\tint ret;

\tret = quiesce_locked(a5);
\tif (ret)
\t\treturn ret;
\t/* Retire all firmware DMA aliases while the supplier is still powered.'''
assert s.count(anchor)==1;s=s.replace(anchor,new)
anchor='fail:\n\tpublish_start_failure(a5);\n\ta5->cleanup_error = stop_locked(a5);'
new='''fail:
\tpublish_start_failure(a5);
\t/* Keep owned RAM, aliases and the PM reference until the owner calls
\t * stop. A failed boot can then be inspected after CPU/IRQ quiescence,
\t * before IOMMU retirement or supplier power-down loses the evidence.
\t */
\ta5->cleanup_error = quiesce_locked(a5);'''
assert s.count(anchor)==1;s=s.replace(anchor,new)
after['camss-icp-a5-boot.c']=s
s=after['camss-icp-a5-boot.h']
anchor=' * Failed teardown retains mapped backing; do not unbind until cleanup succeeds.'
assert s.count(anchor)==1
s=s.replace(anchor,''' * Start failure attempts CPU/IRQ quiescence but retains backing and any PM
 * reference. The owner must call stop after either start success or failure.
 * Inspect firmware RAM only after successful quiescence, with CPU/IRQ off,
 * block reset asserted and all mappings/PM ownership still held.
 * Failed teardown retains mapped backing; do not unbind until cleanup succeeds.''')
after['camss-icp-a5-boot.h']=s
s=after['camss-icp-a5-boot-test.c']
s=s.replace('#include <linux/firmware.h>','#include <linux/dma-mapping.h>\n#include <linux/firmware.h>',1)
anchor='static bool finished, pinned;'
assert s.count(anchor)==1;s=s.replace(anchor,'''static bool finished, pinned, held_failure;
static bool hold_start_failure;
module_param(hold_start_failure, bool, 0444);
MODULE_PARM_DESC(hold_start_failure, "Keep quiesced failed boot RAM and PM until cleanup");''')
anchor='\tif (!ret && pinned && !camss_a5_backing_owned(device_a5) &&'
assert s.count(anchor)==1;s=s.replace(anchor,'\tif (!ret)\n\t\theld_failure = false;\n'+anchor)
anchor='\tret = cleanup();\n\tif (ret)\n\t\ttest_error = ret;\n\tupdate_result();'
assert s.count(anchor)==1;s=s.replace(anchor,'''\tret = cleanup();
\tif (ret)
\t\ttest_error = ret;
\telse
\t\tphase = "cleaned";
\tupdate_result();''')
anchor='static struct attribute *test_attributes[] = { &dev_attr_cleanup.attr, NULL };\nstatic const struct attribute_group test_group = { .attrs = test_attributes };'
new='''/* Temporary root-only diagnostic view. No /dev/mem access and no device
 * access after cleanup: reads are serialized against the same owner lock.
 */
static ssize_t firmware_read(struct file *file, struct kobject *kobj,
\t\t\t     const struct bin_attribute *attr, char *buffer,
\t\t\t     loff_t offset, size_t count)
{
\tstruct device *dev = kobj_to_dev(kobj);
\tstruct camss_a5 *a5;
\tssize_t ret = -ENODATA;

\tmutex_lock(&test_lock);
\ta5 = device_a5;
\tif (!held_failure || !a5 || a5 != dev_get_drvdata(dev))
\t\tgoto done;
\tmutex_lock(&a5->lock);
\tif (a5->cpu_enabled || a5->irq_enabled || !a5->reset_asserted ||
\t    !a5->power_held || !a5->firmware.cpu ||
\t    a5->firmware.mapped != a5->firmware.bytes)
\t\tgoto unlock;
\tif (offset < 0) {
\t\tret = -EINVAL;
\t\tgoto unlock;
\t}
\tret = 0;
\tif (offset >= a5->firmware.bytes)
\t\tgoto unlock;
\tcount = min_t(size_t, count, a5->firmware.bytes - offset);
\tdma_rmb();
\tmemcpy(buffer, a5->firmware.cpu + offset, count);
\tret = count;
unlock:
\tmutex_unlock(&a5->lock);
done:
\tmutex_unlock(&test_lock);
\treturn ret;
}
static const struct bin_attribute firmware_attribute = {
\t.attr = { .name = "firmware", .mode = 0400 },
\t.size = CAMSS_A5_FW_WINDOW,
\t.read = firmware_read,
};
static const struct bin_attribute *test_bin_attributes[] = { &firmware_attribute, NULL };
static struct attribute *test_attributes[] = { &dev_attr_cleanup.attr, NULL };
static const struct attribute_group test_group = {
\t.attrs = test_attributes,
\t.bin_attrs = test_bin_attributes,
};'''
assert s.count(anchor)==1;s=s.replace(anchor,new)
anchor='done:\n\tstop = cleanup();\n\tif (stop)\n\t\tret = stop;'
new='''done:
\tif (ret && hold_start_failure && a5->cpu_release_attempted &&
\t    !a5->cleanup_error && !a5->cpu_enabled && !a5->irq_enabled &&
\t    a5->reset_asserted && a5->power_held && a5->firmware.cpu &&
\t    a5->firmware.mapped == a5->firmware.bytes) {
\t\theld_failure = true;
\t\tphase = "failed-held";
\t} else {
\t\tstop = cleanup();
\t\tif (stop)
\t\t\tret = stop;
\t}'''
assert s.count(anchor)==1;s=s.replace(anchor,new)
after['camss-icp-a5-boot-test.c']=s
patch=[]
for name,s in after.items():
 (P/(name+'.before')).write_text(before[name]);(P/(name+'.proposed')).write_text(s)
 patch.extend(difflib.unified_diff(before[name].splitlines(True),s.splitlines(True),fromfile='a/'+relative+name,tofile='b/'+relative+name))
(HERE/'a5-quiesced-failure.patch').write_text(''.join(patch))
(HERE/'camss-icp-a5-boot-test.c').write_text(after['camss-icp-a5-boot-test.c'])
report=dict(stage=370,source=str(source),parent=parent,changed=[relative+n for n in after],
 proposed_sha256={n:hashlib.sha256(s.encode()).hexdigest() for n,s in after.items()},
 applied=False,installed=False,phone_operations=False,hold_opt_in_default=False,firmware_view_mode='0400',
 start_failure_retains_owned_mappings_and_pm_until_stop=True,not_hardware_quiescence_proof=True)
(HERE/'proposal-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
