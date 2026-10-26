from pathlib import Path
import shutil, difflib
root=Path('/home/cy122/x2pro-linux/linux')
out=Path('/mnt/e/edk2-samurai-out/kernel75')
ref=Path(__file__).resolve().parent
base=root/'drivers/gpu/drm/msm/disp/dpu1'
for name in ('dpu_kms.c','dpu_kms.h','dpu_hw_intf.c'):
    assert not (out/(name+'.before')).exists()
    shutil.copyfile(base/name,out/(name+'.before'))
p=base/'dpu_kms.h';s=p.read_text();assert s.count('\tstruct drm_private_obj global_state;')==1
p.write_text(s.replace('\tstruct drm_private_obj global_state;','\tstruct drm_private_obj global_state;\n\tbool global_state_initialized;'))
p=base/'dpu_kms.c';s=p.read_text()
old='''static void dpu_kms_global_obj_fini(struct dpu_kms *dpu_kms)
{
\tdrm_atomic_private_obj_fini(&dpu_kms->global_state);
}'''
new='''static void dpu_kms_global_obj_fini(struct dpu_kms *dpu_kms)
{
\tif (!dpu_kms->global_state_initialized)
\t\treturn;

\tdrm_atomic_private_obj_fini(&dpu_kms->global_state);
\tdpu_kms->global_state_initialized = false;
}'''
assert s.count(old)==1;s=s.replace(old,new)
old='''\tdrm_atomic_private_obj_init(dpu_kms->dev, &dpu_kms->global_state,
\t\t\t\t    &dpu_kms_global_state_funcs);'''
assert s.count(old)==1;s=s.replace(old,old+'\n\tdpu_kms->global_state_initialized = true;')
p.write_text(s)
p=base/'dpu_hw_intf.c';s=p.read_text()
old='''\tpr_info("boot INTF%d: tearcheck=%#x autorefresh=%#x trigger=%#x\\n",
\t\tintf->idx - INTF_0, te, refresh, trigger);'''
new='''\tpr_info("boot INTF%d: tearcheck=%#x autorefresh=%#x trigger=%#x height=%u line=%#x\\n",
\t\tintf->idx - INTF_0, te, refresh, trigger, height,
\t\tDPU_REG_READ(c, INTF_TEAR_LINE_COUNT));'''
assert s.count(old)==1;s=s.replace(old,new)
old='''\t\tif (ret)
\t\t\treturn ret;
\t}
\tdpu_hw_intf_disable_te(intf);'''
new='''\t\tif (ret) {
\t\t\tpr_err("boot INTF%d drain failed: line=%#x height=%u out=%#x count=%#x\\n",
\t\t\t       intf->idx - INTF_0, line, height,
\t\t\t       DPU_REG_READ(c, INTF_TEAR_OUT_LINE_COUNT),
\t\t\t       DPU_REG_READ(c, INTF_TEAR_INT_COUNT_VAL));
\t\t\treturn ret;
\t\t}
\t}
\tdpu_hw_intf_disable_te(intf);'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
patch=[]
for name in ('dpu_kms.c','dpu_kms.h','dpu_hw_intf.c'):
    relative='drivers/gpu/drm/msm/disp/dpu1/'+name
    patch.extend(difflib.unified_diff((out/(name+'.before')).read_text().splitlines(True),(base/name).read_text().splitlines(True),fromfile='a/'+relative,tofile='b/'+relative))
(ref/'drain-diagnostic.patch').write_text(''.join(patch))
print('Added one-time global-object cleanup guard and bounded drain diagnostics. Timeout still fails safely before display IOMMU takeover.')
