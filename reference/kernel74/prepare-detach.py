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
    assert not (out/(name+'.no-start')).exists()
    shutil.copyfile(dpu/name,out/(name+'.no-start'))
ctl = (dpu/'dpu_hw_ctl.c').read_text()
ctl = ctl.replace('\tu32 fetch = DPU_REG_READ(c, CTL_FETCH_PIPE_ACTIVE);\n',
    '\tu32 fetch = DPU_REG_READ(c, CTL_FETCH_PIPE_ACTIVE);\n'
    '\tu32 intf = DPU_REG_READ(c, CTL_INTF_ACTIVE);\n'
    '\tu32 dsc = DPU_REG_READ(c, CTL_DSC_ACTIVE);\n'
    '\tu32 merge = DPU_REG_READ(c, CTL_MERGE_3D_ACTIVE);\n',1)
needle = '\tdpu_hw_ctl_clear_all_blendstages(ctx);\n\tfor (i = 0; i < ctx->mixer_count; i++)\n'
assert ctl.count(needle)==1
ctl = ctl.replace(needle,
    '\t/* Detach the output before committing empty blend stages. */\n'
    '\tDPU_REG_WRITE(c, CTL_INTF_ACTIVE, 0);\n'
    '\tDPU_REG_WRITE(c, CTL_DSC_ACTIVE, 0);\n'
    '\tDPU_REG_WRITE(c, CTL_MERGE_3D_ACTIVE, 0);\n'
    '\tctx->pending_intf_flush_mask = intf;\n'
    '\tctx->pending_dsc_flush_mask = dsc;\n'
    '\tctx->pending_merge_3d_flush_mask = merge;\n'
    '\tif (intf)\n\t\tctx->pending_flush_mask |= BIT(INTF_IDX);\n'
    '\tif (dsc)\n\t\tctx->pending_flush_mask |= BIT(DSC_IDX);\n'
    '\tif (merge)\n\t\tctx->pending_flush_mask |= BIT(MERGE_3D_IDX);\n'
    + needle)
ctl = ctl.replace('\t/* Reset stopped the transfer; do not start an empty DSI frame. */\n',
    '\tdpu_hw_ctl_trigger_start(ctx);\n',1)
ctl = ctl.replace('\tpr_info("boot CTL%d: top=%#x layers=%#x fetch=%#x\\n",\n'
    '\t\tctx->idx - CTL_0, top, layers, fetch);',
    '\tpr_info("boot CTL%d: top=%#x layers=%#x fetch=%#x intf=%#x dsc=%#x\\n",\n'
    '\t\tctx->idx - CTL_0, top, layers, fetch, intf, dsc);',1)
(dpu/'dpu_hw_ctl.c').write_text(ctl)
intf = (dpu/'dpu_hw_intf.c').read_text()
needle = 'static int dpu_hw_intf_get_vsync_info('
assert intf.count(needle)==1
helper = '''/* SM8150 command-mode boot paths must stop automatic frame requests first. */
void dpu_hw_intf_clear_boot_config(struct dpu_hw_intf *intf)
{
	struct dpu_hw_blk_reg_map *c = &intf->hw;
	u32 te = DPU_REG_READ(c, INTF_TEAR_TEAR_CHECK_EN);
	u32 refresh = DPU_REG_READ(c, INTF_TEAR_AUTOREFRESH_CONFIG);
	u32 trigger = DPU_REG_READ(c, INTF_DSI_CMD_MODE_TRIGGER_EN);

	if (!te && !(refresh & BIT(31)) && !trigger)
		return;

	pr_info("boot INTF%d: tearcheck=%#x autorefresh=%#x trigger=%#x\\n",
		intf->idx - INTF_0, te, refresh, trigger);
	dpu_hw_intf_connect_external_te(intf, false);
	dpu_hw_intf_setup_autorefresh_config(intf, 0, false);
	dpu_hw_intf_disable_te(intf);
	DPU_REG_WRITE(c, INTF_DSI_CMD_MODE_TRIGGER_EN, 0);
	pr_info("boot INTF%d stopped: tearcheck=%#x autorefresh=%#x trigger=%#x\\n",
		intf->idx - INTF_0, DPU_REG_READ(c, INTF_TEAR_TEAR_CHECK_EN),
		DPU_REG_READ(c, INTF_TEAR_AUTOREFRESH_CONFIG),
		DPU_REG_READ(c, INTF_DSI_CMD_MODE_TRIGGER_EN));
}

'''
intf = intf.replace(needle,helper+needle)
(dpu/'dpu_hw_intf.c').write_text(intf)
header = (dpu/'dpu_hw_intf.h').read_text()
pos = header.rindex('#endif')
header = header[:pos]+'''/**
 * dpu_hw_intf_clear_boot_config() - stop inherited SM8150 DSI frame requests
 * @intf: DPU 5 DSI interface, with clocks enabled
 */
void dpu_hw_intf_clear_boot_config(struct dpu_hw_intf *intf);

'''+header[pos:]
(dpu/'dpu_hw_intf.h').write_text(header)
rm = (dpu/'dpu_rm.c').read_text()
needle = '\tint i, ret;\n\n\tfor (i = 0; i < cat->ctl_count; i++) {'
assert rm.count(needle)==1
rm = rm.replace(needle,'''\tint i, ret;

	for (i = 0; i < cat->intf_count; i++) {
		struct dpu_hw_intf *intf;

		if (cat->intf[i].type != INTF_DSI)
			continue;
		intf = rm->hw_intf[cat->intf[i].id - INTF_0];
		dpu_hw_intf_clear_boot_config(intf);
	}

	for (i = 0; i < cat->ctl_count; i++) {''',1)
(dpu/'dpu_rm.c').write_text(rm)
patch = []
for name in names:
    path = 'drivers/gpu/drm/msm/disp/dpu1/'+name
    patch.extend(difflib.unified_diff((out/(name+'.before')).read_text().splitlines(keepends=True),
        (kernel/path).read_text().splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path))
(ref/'handoff-detach.patch').write_text(''.join(patch))
build = (ref/'build-handoff.sh').read_text().replace('Image-handoff','Image-detach').replace(
    'logdump-k74-handoff.img','logdump-k74-detach.img').replace('kernel-build.log','detach-build.log').replace(
    'build-hashes.txt','detach-build-hashes.txt')
(ref/'build-detach.sh').write_text(build)
print('Stop inherited DSI TE/autorefresh/trigger before CTL reset; detach INTF/DSC before committing empty stages.')
