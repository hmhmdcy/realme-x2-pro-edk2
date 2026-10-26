from pathlib import Path
import shutil,difflib
root=Path('/home/cy122/x2pro-linux/linux')
out=Path('/mnt/e/edk2-samurai-out/kernel75')
ref=Path(__file__).resolve().parent
base=root/'drivers/gpu/drm/msm/disp/dpu1'
for name in ('dpu_hw_intf.c','dpu_hw_ctl.c','dpu_rm.c'):
    assert not (out/(name+'.diagnostic-before')).exists()
    shutil.copyfile(base/name,out/(name+'.diagnostic-before'))
p=base/'dpu_hw_intf.c';s=p.read_text()
start=s.index('int dpu_hw_intf_clear_boot_config(');end=s.index('\nstatic int dpu_hw_intf_get_vsync_info',start)
b=s[start:end]
b=b.replace('\tint ret;','\tint ret = 0;')
b=b.replace('pr_err("boot INTF%d drain failed:','pr_info("boot INTF%d frame stalled:')
b=b.replace('\n\t\t\treturn ret;\n\t\t}', '\n\t\t\t/* The caller must abort this inherited frame with CTL reset. */\n\t\t}')
assert b.endswith('\treturn 0;\n}\n')
b=b[:-len('\treturn 0;\n}\n')]+'\treturn ret;\n}\n'
p.write_text(s[:start]+b+s[end:])
p=base/'dpu_hw_ctl.c';s=p.read_text();start=s.index('int dpu_hw_ctl_clear_boot_config(');end=s.index('\nstruct ctl_blend_config',start)
b=s[start:end];assert b.endswith('\treturn 0;\n}\n')
b=b[:-len('\treturn 0;\n}\n')]+'\treturn 1;\n}\n'
p.write_text(s[:start]+b+s[end:])
p=base/'dpu_rm.c';s=p.read_text();start=s.index('int dpu_rm_clear_boot_config(');end=s.index('\nstatic bool _dpu_rm_needs_split_display',start)
b=s[start:end];b=b.replace('\tint i, ret;','\tint i, ret, reset_ctls = 0;\n\tbool stalled = false;')
old='''\t\tret = dpu_hw_intf_clear_boot_config(intf);
\t\tif (ret)
\t\t\treturn ret;'''
new='''\t\tret = dpu_hw_intf_clear_boot_config(intf);
\t\tif (ret == -ETIMEDOUT)
\t\t\tstalled = true;
\t\telse if (ret)
\t\t\treturn ret;'''
assert b.count(old)==1;b=b.replace(old,new)
old='''\t\tret = dpu_hw_ctl_clear_boot_config(ctl);
\t\tif (ret)
\t\t\treturn ret;
\t}

\treturn 0;'''
new='''\t\tret = dpu_hw_ctl_clear_boot_config(ctl);
\t\tif (ret < 0)
\t\t\treturn ret;
\t\treset_ctls += ret;
\t}

\t/* Never change domains with a stalled frame and no confirmed CMD reset. */
\tif (stalled && !reset_ctls)
\t\treturn -ETIMEDOUT;
\tif (stalled)
\t\tpr_info("boot stalled command frame aborted: %d CTL reset(s) completed\\n",
\t\t\treset_ctls);

\treturn 0;'''
assert b.count(old)==1;b=b.replace(old,new)
p.write_text(s[:start]+b+s[end:])
patch=[]
for name in ('dpu_hw_intf.c','dpu_hw_ctl.c','dpu_rm.c'):
    relative='drivers/gpu/drm/msm/disp/dpu1/'+name
    patch.extend(difflib.unified_diff((out/(name+'.diagnostic-before')).read_text().splitlines(True),(base/name).read_text().splitlines(True),fromfile='a/'+relative,tofile='b/'+relative))
(ref/'stalled-frame.patch').write_text(''.join(patch))
s=(ref/'build-diagnostic.sh').read_text().replace('diagnostic','stalled')
(ref/'build-stalled.sh').write_text(s)
print('Stalled frames require successful bounded command CTL reset, detach, empty commit and second reset before IOMMU takeover.')
