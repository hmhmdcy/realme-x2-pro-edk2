from pathlib import Path
import shutil,difflib
root=Path('/home/cy122/x2pro-linux/linux')
out=Path('/mnt/e/edk2-samurai-out/kernel75')
ref=Path(__file__).resolve().parent
base=root/'drivers/gpu/drm/msm/disp/dpu1'
for name in ('dpu_hw_ctl.c','dpu_hw_ctl.h','dpu_rm.c'):
    assert not (out/(name+'.stalled-before')).exists()
    shutil.copyfile(base/name,out/(name+'.stalled-before'))
p=base/'dpu_hw_ctl.h';s=p.read_text()
s=s.replace(' * @ctx: CTL context, with clocks enabled\n',' * @ctx: CTL context, with clocks enabled\n * @cleared_intfs: accumulates output bits covered by successful CTL resets\n')
assert s.count('int dpu_hw_ctl_clear_boot_config(struct dpu_hw_ctl *ctx);')==1
p.write_text(s.replace('int dpu_hw_ctl_clear_boot_config(struct dpu_hw_ctl *ctx);','int dpu_hw_ctl_clear_boot_config(struct dpu_hw_ctl *ctx, u32 *cleared_intfs);'))
p=base/'dpu_hw_ctl.c';s=p.read_text();s=s.replace('int dpu_hw_ctl_clear_boot_config(struct dpu_hw_ctl *ctx)','int dpu_hw_ctl_clear_boot_config(struct dpu_hw_ctl *ctx, u32 *cleared_intfs)')
start=s.index('int dpu_hw_ctl_clear_boot_config(');end=s.index('\nstruct ctl_blend_config',start);b=s[start:end]
assert b.endswith('\treturn 1;\n}\n')
b=b[:-len('\treturn 1;\n}\n')]+'\t*cleared_intfs |= intf;\n\treturn 0;\n}\n'
p.write_text(s[:start]+b+s[end:])
p=base/'dpu_rm.c';s=p.read_text();start=s.index('int dpu_rm_clear_boot_config(');end=s.index('\nstatic bool _dpu_rm_needs_split_display',start);b=s[start:end]
b=b.replace('\tint i, ret, reset_ctls = 0;\n\tbool stalled = false;','\tint i, ret;\n\tu32 stalled_intfs = 0, cleared_intfs = 0;')
b=b.replace('\t\t\tstalled = true;','\t\t\tstalled_intfs |= BIT(intf->idx - INTF_0);')
b=b.replace('dpu_hw_ctl_clear_boot_config(ctl);','dpu_hw_ctl_clear_boot_config(ctl, &cleared_intfs);').replace('\t\treset_ctls += ret;\n','')
old='''\tif (stalled && !reset_ctls)
\t\treturn -ETIMEDOUT;
\tif (stalled)
\t\tpr_info("boot stalled command frame aborted: %d CTL reset(s) completed\\n",
\t\t\treset_ctls);'''
new='''\tif (stalled_intfs & ~cleared_intfs)
\t\treturn -ETIMEDOUT;
\tif (stalled_intfs)
\t\tpr_info("boot stalled INTF mask=%#x aborted, CTL outputs=%#x\\n",
\t\t\tstalled_intfs, cleared_intfs);'''
assert b.count(old)==1;b=b.replace(old,new);p.write_text(s[:start]+b+s[end:])
patch=[]
for name in ('dpu_hw_ctl.c','dpu_hw_ctl.h','dpu_rm.c'):
    rel='drivers/gpu/drm/msm/disp/dpu1/'+name
    patch.extend(difflib.unified_diff((out/(name+'.stalled-before')).read_text().splitlines(True),(base/name).read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(ref/'match-stalled-interface.patch').write_text(''.join(patch))
(ref/'build-matched.sh').write_text((ref/'build-diagnostic.sh').read_text().replace('diagnostic','matched'))
print('Every stalled DSI interface must be covered by the output mask of a successfully reset/cleared command CTL.')
