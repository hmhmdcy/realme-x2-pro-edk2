from pathlib import Path
import difflib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;relative=Path('drivers/media/platform/qcom/camss')
names=['camss-icp-a5-boot-test.c','Makefile','Kconfig'];before={n:(P/'source'/relative/n).read_text() for n in names};after=dict(before)
s=after[names[0]]
def replace(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
replace('#include "camss-icp-a5-ipe.h"','#include "camss-icp-a5-ipe.h"\n#include "camss-icp-a5-m2m.h"')
replace('static struct camss_a5 *device_a5;','static struct camss_a5 *device_a5;\nstatic struct camss_a5_m2m *m2m_endpoint;\nstatic bool enable_m2m;\nmodule_param(enable_m2m, bool, 0400);')
replace('module_param(bound_seen, bool, 0444);','module_param(bound_seen, bool, 0444);\nstatic bool m2m_bound(void)\n{\n\treturn READ_ONCE(bound_seen);\n}')
replace('int ret = device_a5 ? camss_a5_stop(device_a5) : 0;','int ret = m2m_endpoint ? camss_a5_m2m_cleanup(m2m_endpoint) :\n\t\t  device_a5 ? camss_a5_stop(device_a5) : 0;')
anchor='static struct attribute *test_attributes[] = { &dev_attr_cleanup.attr, &dev_attr_run.attr, NULL };'
replacement='''static ssize_t m2m_status_show(struct device *dev, struct device_attribute *attr,
\t\t\t       char *buffer)
{
\tssize_t ret;

\tmutex_lock(&test_lock);
\tret = camss_a5_m2m_status(m2m_endpoint, buffer, PAGE_SIZE);
\tupdate_result();
\tmutex_unlock(&test_lock);
\treturn ret;
}
static DEVICE_ATTR_RO(m2m_status);
static struct attribute *test_attributes[] = {
\t&dev_attr_cleanup.attr, &dev_attr_run.attr, &dev_attr_m2m_status.attr, NULL };
'''
replace(anchor,replacement)
replace('''\tif (!sysfs_streq(buffer, "1"))
\t\treturn -EINVAL;
\tif (!try_module_get(THIS_MODULE))''','''\tif (!sysfs_streq(buffer, "1"))
\t\treturn -EINVAL;
\tif (enable_m2m)
\t\treturn -EOPNOTSUPP;
\tif (!try_module_get(THIS_MODULE))''')
replace('''\tpm_runtime_enable(dev);
\tphase = "ready";''','''\tpm_runtime_enable(dev);
\tif (enable_m2m) {
\t\tm2m_endpoint = camss_a5_m2m_register(a5, THIS_MODULE,
\t\t\t\t\t "qcom/sm8150/samurai-icp356.elf", m2m_bound);
\t\tif (IS_ERR(m2m_endpoint)) {
\t\t\tret = PTR_ERR(m2m_endpoint);
\t\t\tm2m_endpoint = NULL;
\t\t\tpm_runtime_disable(dev);
\t\t\tcamss_a5_resources_release(&a5->resources);
\t\t\tdevice_a5 = NULL;
\t\t\tplatform_set_drvdata(pdev, NULL);
\t\t\tmutex_unlock(&test_lock);
\t\t\treturn ret;
\t\t}
\t}
\tphase = "ready";''')
replace('''static void boot_test_remove(struct platform_device *pdev)
{
\tmutex_lock(&test_lock);
\tcleanup();''','''static void boot_test_remove(struct platform_device *pdev)
{
\tint ret;

\tmutex_lock(&test_lock);
\tret = camss_a5_m2m_unregister(m2m_endpoint);
\tif (WARN_ON(ret)) {
\t\tmutex_unlock(&test_lock);
\t\treturn;
\t}
\tm2m_endpoint = NULL;
\tcleanup();''')
replace('''\ttest_io.input = (struct camss_a5_nv12_layout) {''','''\tif (enable_m2m && enable_frame)
\t\treturn -EINVAL;
\ttest_io.input = (struct camss_a5_nv12_layout) {''')
after[names[0]]=s
after['Makefile']+='\nobj-$(CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_M2M) += camss-icp-a5-m2m.o\n'
after['Kconfig']+='''
config VIDEO_QCOM_CAMSS_ICP_A5_M2M
\ttristate
\tdepends on VIDEO_QCOM_CAMSS_ICP_A5_CORE && VIDEO_DEV
\tselect V4L2_MEM2MEM_DEV
\tselect VIDEOBUF2_VMALLOC
'''
after['Kconfig']=after['Kconfig'].replace('depends on VIDEO_QCOM_CAMSS_ICP_A5_CORE && OF_OVERLAY\n\nconfig VIDEO_QCOM_CAMSS_ICP_A5_M2M','depends on VIDEO_QCOM_CAMSS_ICP_A5_CORE && OF_OVERLAY\n\tselect VIDEO_QCOM_CAMSS_ICP_A5_M2M\n\nconfig VIDEO_QCOM_CAMSS_ICP_A5_M2M')
for n in ['camss-icp-a5-m2m.c','camss-icp-a5-m2m.h']:
 before[n]='';after[n]=(HERE/n).read_text();names.append(n)
patch=''
for n in names:
 (P/(n+'.before')).write_text(before[n]);(P/(n+'.proposed')).write_text(after[n])
 patch+=''.join(difflib.unified_diff(before[n].splitlines(True),after[n].splitlines(True),fromfile='a/'+str(relative/n) if before[n] else '/dev/null',tofile='b/'+str(relative/n)))
(HERE/'m2m-adapter.patch').write_text(patch);(HERE/'camss-icp-a5-boot-test.c').write_text(after[names[0]])
(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=386,parent='6fb4806e219998f5d06919a9b0266ff7b08867b0',changed=names,
 soc_dma_and_striping_unchanged=True,new_v4l2_m2m_adapter=True,temporary_platform_owner=True,installed=False),indent=2)+'\n')
print('Prepared m2m queue adapter and optional temporary platform-owner registration.')
