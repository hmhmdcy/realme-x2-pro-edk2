from pathlib import Path
import difflib
import shutil

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root/'reference/kernel74'
out = Path('/mnt/e/edk2-samurai-out/kernel74')
kernel = Path('/home/cy122/x2pro-linux/linux')
ctl = kernel/'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c'
old = ctl.read_text()
needle = '\tdpu_hw_ctl_trigger_flush_v1(ctx);\n\tdpu_hw_ctl_trigger_start(ctx);\n\tdpu_hw_ctl_clear_pending_flush(ctx);'
assert old.count(needle) == 1
assert not (out/'dpu_hw_ctl.c.with-start').exists()
shutil.copyfile(ctl,out/'dpu_hw_ctl.c.with-start')
ctl.write_text(old.replace(needle,
    '\tdpu_hw_ctl_trigger_flush_v1(ctx);\n'
    '\t/* Reset stopped the transfer; do not start an empty DSI frame. */\n'
    '\tdpu_hw_ctl_clear_pending_flush(ctx);'))
changes = ['dpu_kms.c','dpu_rm.c','dpu_rm.h','dpu_hw_ctl.c','dpu_hw_ctl.h']
patch = []
for name in changes:
    path = 'drivers/gpu/drm/msm/disp/dpu1/'+name
    patch.extend(difflib.unified_diff((out/(name+'.before')).read_text().splitlines(keepends=True),
        (kernel/path).read_text().splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path))
(ref/'handoff-no-start.patch').write_text(''.join(patch))
build = (ref/'build-handoff.sh').read_text().replace('Image-handoff','Image-no-start').replace(
    'logdump-k74-handoff.img','logdump-k74-no-start.img').replace('kernel-build.log','no-start-build.log').replace(
    'build-hashes.txt','no-start-build-hashes.txt')
(ref/'build-no-start.sh').write_text(build)
print('Removed only the empty CTL start; retained the guarded, bounded reset and LM/CTL flush.')
