from pathlib import Path
import difflib
import shutil

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root/'reference/kernel74'
out = Path('/mnt/e/edk2-samurai-out/kernel74')
kernel = Path('/home/cy122/x2pro-linux/linux')
dpu = kernel/'drivers/gpu/drm/msm/disp/dpu1'
names = ['dpu_kms.c','dpu_rm.c','dpu_rm.h','dpu_hw_ctl.c','dpu_hw_ctl.h','dpu_hw_intf.c','dpu_hw_intf.h']
for name in names:
    assert not (out/(name+'.detach')).exists()
    shutil.copyfile(dpu/name,out/(name+'.detach'))
path = dpu/'dpu_hw_intf.c'
text = path.read_text().replace('void dpu_hw_intf_clear_boot_config(', 'int dpu_hw_intf_clear_boot_config(',1)
needle = '\tu32 trigger = DPU_REG_READ(c, INTF_DSI_CMD_MODE_TRIGGER_EN);\n'
assert text.count(needle)==1
text = text.replace(needle,needle+
    '\tu32 height = DPU_REG_READ(c, INTF_TEAR_VSYNC_INIT_VAL) & 0xffff;\n'
    '\tu32 line;\n\tint ret;\n',1)
text = text.replace('if (!te && !(refresh & BIT(31)) && !trigger)\n\t\treturn;',
    'if (!te && !(refresh & BIT(31)) && !trigger)\n\t\treturn 0;',1)
needle = '\tdpu_hw_intf_setup_autorefresh_config(intf, 0, false);\n\tdpu_hw_intf_disable_te(intf);'
assert text.count(needle)==1
text = text.replace(needle,'''\tdpu_hw_intf_setup_autorefresh_config(intf, 0, false);
	/* Keep the identity domain until the inherited frame finishes. */
	if (refresh & BIT(31)) {
		if (!height)
			return -EINVAL;
		ret = readl_poll_timeout(c->blk_addr + INTF_TEAR_LINE_COUNT, line,
					 !(line & 0xffff) || (line & 0xffff) >= height,
					 100, 50000);
		if (ret)
			return ret;
	}
	dpu_hw_intf_disable_te(intf);''',1)
needle = '\t\tDPU_REG_READ(c, INTF_DSI_CMD_MODE_TRIGGER_EN));\n}\n\nstatic int dpu_hw_intf_get_vsync_info('
assert text.count(needle)==1
text = text.replace(needle,'\t\tDPU_REG_READ(c, INTF_DSI_CMD_MODE_TRIGGER_EN));\n\treturn 0;\n}\n\nstatic int dpu_hw_intf_get_vsync_info(',1)
path.write_text(text)
path = dpu/'dpu_hw_intf.h'
text = path.read_text().replace(' * @intf: DPU 5 DSI interface, with clocks enabled\n */',
    ' * @intf: DPU 5 DSI interface, with clocks enabled\n *\n'
    ' * Return: 0 on success or a negative error if the inherited frame cannot drain.\n */',1).replace(
    'void dpu_hw_intf_clear_boot_config(', 'int dpu_hw_intf_clear_boot_config(',1)
path.write_text(text)
path = dpu/'dpu_rm.c'
text = path.read_text().replace('\t\tdpu_hw_intf_clear_boot_config(intf);',
    '\t\tret = dpu_hw_intf_clear_boot_config(intf);\n\t\tif (ret)\n\t\t\treturn ret;',1)
path.write_text(text)
path = dpu/'dpu_hw_ctl.c'
text = path.read_text()
needle = '\tdpu_hw_ctl_trigger_start(ctx);\n\tdpu_hw_ctl_clear_pending_flush(ctx);\n\n\tpr_info("boot CTL%d cleared:'
assert text.count(needle)==1
text = text.replace(needle,'''\tdpu_hw_ctl_trigger_start(ctx);
	dpu_hw_ctl_clear_pending_flush(ctx);
	/* Discard an empty kickoff that was waiting for the disabled TE. */
	ret = dpu_hw_ctl_reset_control(ctx);
	if (ret)
		return ret;

	pr_info("boot CTL%d cleared:''',1)
path.write_text(text)
patch = []
for name in names:
    relative = 'drivers/gpu/drm/msm/disp/dpu1/'+name
    patch.extend(difflib.unified_diff((out/(name+'.before')).read_text().splitlines(keepends=True),
        (kernel/relative).read_text().splitlines(keepends=True),fromfile='a/'+relative,tofile='b/'+relative))
(ref/'handoff-drain.patch').write_text(''.join(patch))
(ref/'build-drain.sh').write_text((ref/'build-handoff.sh').read_text().replace('Image-handoff','Image-drain').replace(
    'logdump-k74-handoff.img','logdump-k74-drain.img').replace('kernel-build.log','drain-build.log').replace('build-hashes.txt','drain-build-hashes.txt'))
(ref/'check-drain.sh').write_text((ref/'check-no-start.sh').read_text().replace('handoff-no-start.patch','handoff-drain.patch').replace('checkpatch-no-start.txt','checkpatch-drain.txt'))
print('Drain the old autorefresh frame within 50 ms, and reset away the empty deferred kickoff before changing domains.')
