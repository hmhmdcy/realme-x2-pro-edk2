"""Keep cooperative A5 shutdown separate from forced global block reset."""
from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
parent=json.loads((HERE.parent/'kernel374/source-state.json').read_text())['commit']
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
for name in ['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c','camss-icp-a5-resources.c']:
 (P/(name+'.before')).write_bytes((source/relative/name).read_bytes())
name='camss-icp-a5-boot.c';before=(P/(name+'.before')).read_text();s=before
anchor='\tvoid __iomem *base = a5->resources.sierra;\n\tu32 value;\n\tint ret;\n\n\thrtimer_cancel(&a5->boot_timer);'
assert s.count(anchor)==1;s=s.replace(anchor,anchor.replace('\n\tu32 value;', '\n\tbool cooperative = false;\n\tu32 value;'))
anchor='\t\tif (a5->initialized) {'
assert s.count(anchor)==1;s=s.replace(anchor,'\t\tif (a5->initialized && a5->irq_enabled) {')
anchor='\t\t\t\t\t\t\t value & A5_WFI, 1000, 300000);\n\t\t}'
assert s.count(anchor)==1;s=s.replace(anchor,anchor[:-3]+'\t\t\tcooperative = !a5->pc_error;\n\t\t}')
old='''\t\t/* The block reset is owned exclusively. Retain all RAM and the
\t\t * runtime-PM reference if it cannot quiesce a failed firmware.
\t\t */
\t\tret = reset_control_assert(a5->reset);
\t\tif (ret)
\t\t\treturn ret;
\t\ta5->reset_asserted = true;'''
new='''\t\t/* Confirm the CPU enable and wake requests are actually cleared.
\t\t * Normal firmware shutdown follows PC_PREP/WFI and the local CSR
\t\t * sequence. Keep the global ICP/AHB block accessible until its DMA
\t\t * aliases and clock/domain ownership have been retired.
\t\t */
\t\tvalue = readl(base + A5_CONTROL);
\t\tif (value & (A5_ENABLE | A5_WAKE)) {
\t\t\tcooperative = false;
\t\t\ta5->pc_error = -EIO;
\t\t}
\t\tif (!cooperative) {
\t\t\t/* Failed/uninitialized firmware needs a forced reset. A reset
\t\t\t * failure must retain the CPU, RAM and runtime-PM ownership.
\t\t\t */
\t\t\tret = reset_control_assert(a5->reset);
\t\t\tif (ret)
\t\t\t\treturn ret;
\t\t\ta5->reset_asserted = true;
\t\t}'''
assert s.count(old)==1;s=s.replace(old,new)
anchor='\t\tdev_info(a5->dev, "A5 stopped, block reset asserted; pc_error=%d\\n", a5->pc_error);'
assert s.count(anchor)==1;s=s.replace(anchor,'\t\tdev_info(a5->dev, "A5 stopped, cooperative=%u block_reset=%u pc_error=%d\\n",\n\t\t\t cooperative, a5->reset_asserted, a5->pc_error);')
old='''int camss_a5_runtime_suspend(struct camss_a5 *a5)
{
\tint ret;

\tif (a5->cpu_enabled)
\t\treturn -EBUSY;
\tret = reset_control_assert(a5->reset);
\tif (ret)
\t\treturn ret;
\ta5->reset_asserted = true;
\treturn camss_a5_resources_suspend(&a5->resources);
}'''
new='''int camss_a5_runtime_suspend(struct camss_a5 *a5)
{
\tif (a5->cpu_enabled)
\t\treturn -EBUSY;
\t/* A cooperative stop has already disabled A5 through its local CSR.
\t * Do not assert the global ICP/AHB reset in the normal PM path.
\t * A forced stop has asserted it already; resume releases it before
\t * enabling any clocks. The next explicit start owns the reset cycle.
\t */
\treturn camss_a5_resources_suspend(&a5->resources);
}'''
assert s.count(old)==1;s=s.replace(old,new)
(P/(name+'.proposed')).write_text(s)
(HERE/'cooperative-stop.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/'+str(relative/name),tofile='b/'+str(relative/name))))
(HERE/'camss-icp-a5-boot-test.c').write_bytes((P/'camss-icp-a5-boot-test.c.before').read_bytes())
(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=375,parent=parent,source=str(source),changed=[name],test_owner_unchanged=True,installed=False),indent=2)+'\n')
print('Prepared cooperative stop without global ICP/AHB reset; forced failure reset retained.')
