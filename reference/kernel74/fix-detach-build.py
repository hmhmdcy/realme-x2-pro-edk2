from pathlib import Path
import difflib

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel74')
out = Path('/mnt/e/edk2-samurai-out/kernel74')
kernel = Path('/home/cy122/x2pro-linux/linux')
dpu = kernel/'drivers/gpu/drm/msm/disp/dpu1'
path = dpu/'dpu_rm.c'
text = path.read_text()
needle = 'intf = to_dpu_hw_intf(rm->intf_blks[cat->intf[i].id - INTF_0]);'
assert text.count(needle)==1
path.write_text(text.replace(needle,'intf = rm->hw_intf[cat->intf[i].id - INTF_0];'))
names = ['dpu_kms.c','dpu_rm.c','dpu_rm.h','dpu_hw_ctl.c','dpu_hw_ctl.h','dpu_hw_intf.c','dpu_hw_intf.h']
patch = []
for name in names:
    relative = 'drivers/gpu/drm/msm/disp/dpu1/'+name
    patch.extend(difflib.unified_diff((out/(name+'.before')).read_text().splitlines(keepends=True),
        (kernel/relative).read_text().splitlines(keepends=True),fromfile='a/'+relative,tofile='b/'+relative))
(ref/'handoff-detach.patch').write_text(''.join(patch))
(ref/'build-detach-fixed.sh').write_text((ref/'build-detach.sh').read_text().replace('detach-build.log','detach-build-fixed.log'))
(ref/'check-detach.sh').write_text((ref/'check-no-start.sh').read_text().replace('handoff-no-start.patch','handoff-detach.patch').replace('checkpatch-no-start.txt','checkpatch-detach.txt'))
print('Use the actual resource-manager hw_intf pointer array; preserve the rejected build log.')
