"""Separate resource binding from explicit A5 lifecycle execution."""
from pathlib import Path
import difflib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
names=['camss-icp-a5-boot.c','camss-icp-a5-boot-test.c'];before={n:(P/(n+'.before')).read_text() for n in names};after=dict(before)
s=after[names[0]]
anchor='\t\ta5->pc_error = send_command(a5, SYS_PC_PREP, PC_DONE);'
assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\n\t\t\tif (!a5->pc_error)\n\t\t\t\tdev_info(a5->dev, "A5 SYS_PC_PREP acknowledged\\n");')
anchor='\tret = send_command(a5, SYS_PING, PING_ACK);';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\n\tif (!ret)\n\t\tdev_info(a5->dev, "A5 SYS_PING acknowledged\\n");');after[names[0]]=s
s=after[names[1]].replace('#include <linux/dma-mapping.h>','#include <linux/device/bus.h>\n#include <linux/dma-mapping.h>').replace('#include <linux/mutex.h>','#include <linux/mutex.h>\n#include <linux/notifier.h>')
anchor='static bool finished, pinned, held_failure;';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\nstatic bool bound_seen;\nmodule_param(bound_seen, bool, 0444);')
a=s.index('static int boot_test_probe(');b=s.index('static void boot_test_remove(',a);probe=s[a:b]
x=probe.index('\tphase = "request-firmware";');y=probe.index('\tmutex_unlock(&test_lock);\n\treturn 0;',x)
run=probe[x:y]
probe=probe[:x]+'''\tphase = "ready";
\tfinished = true;
\ttest_error = 0;
\tupdate_result();
\tdev_info(dev, "A5 diagnostic probe ready; no firmware started\\n");
\tmutex_unlock(&test_lock);
\treturn 0;
}

'''
probe=probe.replace('\tconst struct firmware *firmware;\n','').replace('\tint ret, stop;','\tint ret;')
run='''static void run_locked(struct device *dev)
{
\tstruct camss_a5 *a5 = device_a5;
\tconst struct firmware *firmware;
\tint ret, stop;

\tfinished = false;
\tdev_info(dev, "A5 diagnostic run begin after binding\\n");
'''+run+'''\tdev_info(dev, "A5 diagnostic run end ret=%d init=%u ping=%u pc=%u irqs=%u msgs=%u wd=%u proto=%u backing=%u power=%u groups=%u domains=%u\\n",
\t\t test_error, a5->init_done, a5->ping_done, a5->pc_done,
\t\t a5->interrupts, a5->messages, a5->watchdogs, a5->protocol_errors,
\t\t camss_a5_backing_owned(a5), a5->power_held,
\t\t a5->resources.enabled_groups, a5->resources.held_domains);
}

'''
s=s[:a]+probe+run+s[b:]
anchor='static struct attribute *test_attributes[] = { &dev_attr_cleanup.attr, NULL };';assert s.count(anchor)==1
store='''static void run_locked(struct device *dev);

static ssize_t run_store(struct device *dev, struct device_attribute *attr,
\t\t\t const char *buffer, size_t count)
{
\tint ret = 0;

\tif (!sysfs_streq(buffer, "1"))
\t\treturn -EINVAL;
\tif (!try_module_get(THIS_MODULE))
\t\treturn -ENODEV;
\tmutex_lock(&test_lock);
\tif (!device_a5 || device_a5 != dev_get_drvdata(dev) || !finished ||
\t    !READ_ONCE(bound_seen) || camss_a5_backing_owned(device_a5) ||
\t    device_a5->cpu_enabled || device_a5->power_held ||
\t    device_a5->resources.enabled_groups || device_a5->resources.held_domains) {
\t\tret = -EBUSY;
\t} else {
\t\trun_locked(dev);
\t}
\tmutex_unlock(&test_lock);
\tmodule_put(THIS_MODULE);
\tif (ret)
\t\treturn ret;
\treturn count;
}
static DEVICE_ATTR_WO(run);
static struct attribute *test_attributes[] = { &dev_attr_cleanup.attr, &dev_attr_run.attr, NULL };'''
s=s.replace(anchor,store)
anchor='static int __init boot_test_init(void)';assert s.count(anchor)==1
notifier='''/* Observe the normal platform binding notification without altering links. */
static int test_bus_event(struct notifier_block *block, unsigned long action, void *data)
{
\tstruct device *dev = data;
\tconst char *event;

\tif (!of_device_is_compatible(dev->of_node, "realme,samurai-a5-icp-boot-test"))
\t\treturn NOTIFY_DONE;
\tswitch (action) {
\tcase BUS_NOTIFY_BIND_DRIVER:
\t\tevent = "bind";
\t\tbreak;
\tcase BUS_NOTIFY_BOUND_DRIVER:
\t\tWRITE_ONCE(bound_seen, true);
\t\tevent = "bound";
\t\tbreak;
\tcase BUS_NOTIFY_UNBIND_DRIVER:
\t\tWRITE_ONCE(bound_seen, false);
\t\tevent = "unbind";
\t\tbreak;
\tcase BUS_NOTIFY_UNBOUND_DRIVER:
\tcase BUS_NOTIFY_DRIVER_NOT_BOUND:
\t\tWRITE_ONCE(bound_seen, false);
\t\tevent = "unbound";
\t\tbreak;
\tdefault:
\t\treturn NOTIFY_DONE;
\t}
\tdev_info(dev, "A5 diagnostic bus event=%s\\n", event);
\treturn NOTIFY_DONE;
}
static struct notifier_block test_bus_notifier = { .notifier_call = test_bus_event };

'''
s=s.replace(anchor,notifier+anchor)
anchor='\tret = platform_driver_register(&boot_test_driver);\n\tif (ret)\n\t\treturn ret;'
new='''\tret = bus_register_notifier(&platform_bus_type, &test_bus_notifier);
\tif (ret)
\t\treturn ret;
\tret = platform_driver_register(&boot_test_driver);
\tif (ret) {
\t\tbus_unregister_notifier(&platform_bus_type, &test_bus_notifier);
\t\treturn ret;
\t}''';assert s.count(anchor)==1;s=s.replace(anchor,new)
anchor='\tret = of_overlay_fdt_apply(a5_boot_test_overlay,';s=s.replace(anchor,'\tpr_info("A5 diagnostic overlay apply begin\\n");\n'+anchor,1)
anchor='\t\t\t\t  sizeof(a5_boot_test_overlay), &overlay_id, NULL);';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\n\tpr_info("A5 diagnostic overlay apply end ret=%d bound=%u\\n", ret, READ_ONCE(bound_seen));')
anchor='\t\tplatform_driver_unregister(&boot_test_driver);\n\t}';assert s.count(anchor)==1;s=s.replace(anchor,'\t\tplatform_driver_unregister(&boot_test_driver);\n\t\tbus_unregister_notifier(&platform_bus_type, &test_bus_notifier);\n\t}')
anchor='''static void __exit boot_test_exit(void)
{
\tof_overlay_remove(&overlay_id);
\tplatform_driver_unregister(&boot_test_driver);
}'''
new='''static void __exit boot_test_exit(void)
{
\tint ret;

\tpr_info("A5 diagnostic module exit begin\\n");
\tret = of_overlay_remove(&overlay_id);
\tpr_info("A5 diagnostic overlay remove ret=%d\\n", ret);
\tplatform_driver_unregister(&boot_test_driver);
\tbus_unregister_notifier(&platform_bus_type, &test_bus_notifier);
\tpr_info("A5 diagnostic module exit end\\n");
}''';assert s.count(anchor)==1;s=s.replace(anchor,new);after[names[1]]=s
patch=[]
for name,text in after.items():
 (P/(name+'.proposed')).write_text(text);patch.extend(difflib.unified_diff(before[name].splitlines(True),text.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/'+name,tofile='b/drivers/media/platform/qcom/camss/'+name))
(HERE/'post-bind-diagnostic.patch').write_text(''.join(patch));(HERE/names[1]).write_text(after[names[1]])
report=dict(stage=374,parent=json.loads((HERE.parent/'kernel373/source-state.json').read_text())['commit'],changed=names,applied=False,installed=False,
 resource_only_probe=True,explicit_post_bound_run=True,normal_bus_notifier_observation_only=True,firmware_cpu_started=False)
(HERE/'proposal-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
