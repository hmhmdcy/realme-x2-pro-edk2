from pathlib import Path
import hashlib
import json

kernel=Path('/home/cy122/x2pro-linux/linux')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel74')
base=kernel/'drivers/gpu/drm/msm/disp/dpu1'
expected=json.loads((ref/'sources-before.json').read_text())
for name in ('dpu_kms.c','dpu_rm.c','dpu_rm.h','dpu_hw_ctl.c','dpu_hw_ctl.h'):
    p=base/name
    assert hashlib.sha256(p.read_bytes()).hexdigest()==expected[str(p.relative_to(kernel))],name

p=base/'dpu_hw_ctl.c'
text=p.read_text()
marker='struct ctl_blend_config {\n'
assert text.count(marker)==1
helper='''/* Stop inherited command-mode fetches before replacing the IOMMU domain. */
int dpu_hw_ctl_clear_boot_config(struct dpu_hw_ctl *ctx)
{
	struct dpu_hw_blk_reg_map *c = &ctx->hw;
	u32 top = DPU_REG_READ(c, CTL_TOP);
	u32 fetch = DPU_REG_READ(c, CTL_FETCH_PIPE_ACTIVE);
	u32 layers = 0;
	int i, ret;

	for (i = 0; i < ctx->mixer_count; i++) {
		enum dpu_lm lm = ctx->mixer_hw_caps[i].id;

		layers |= DPU_REG_READ(c, CTL_LAYER(lm));
		layers |= DPU_REG_READ(c, CTL_LAYER_EXT(lm));
		layers |= DPU_REG_READ(c, CTL_LAYER_EXT2(lm));
		layers |= DPU_REG_READ(c, CTL_LAYER_EXT3(lm));
	}

	/* Video-mode shutdown requires stopping the INTF timing engine. */
	if (!(top & BIT(17)) || (!layers && !fetch))
		return 0;

	pr_info("boot CTL%d: top=%#x layers=%#x fetch=%#x\\n",
		ctx->idx - CTL_0, top, layers, fetch);
	ret = dpu_hw_ctl_reset_control(ctx);
	if (ret)
		return ret;

	dpu_hw_ctl_clear_all_blendstages(ctx);
	for (i = 0; i < ctx->mixer_count; i++)
		dpu_hw_ctl_update_pending_flush_mixer(ctx, ctx->mixer_hw_caps[i].id);
	ctx->pending_flush_mask |= CTL_FLUSH_MASK_CTL;
	dpu_hw_ctl_trigger_flush_v1(ctx);
	dpu_hw_ctl_trigger_start(ctx);
	dpu_hw_ctl_clear_pending_flush(ctx);

	pr_info("boot CTL%d cleared: layer0=%#x layer1=%#x fetch=%#x\\n",
		ctx->idx - CTL_0, DPU_REG_READ(c, CTL_LAYER(LM_0)),
		DPU_REG_READ(c, CTL_LAYER(LM_1)), DPU_REG_READ(c, CTL_FETCH_PIPE_ACTIVE));
	return 0;
}

'''
p.write_text(text.replace(marker,helper+marker))
p=base/'dpu_hw_ctl.h'
text=p.read_text()
pos=text.rindex('#endif')
text=text[:pos]+'''/**
 * dpu_hw_ctl_clear_boot_config() - stop inherited DPU 5 command-mode data paths
 * @ctx: CTL context, with clocks enabled
 *
 * Return: 0 on success or a negative error if CTL reset times out.
 */
int dpu_hw_ctl_clear_boot_config(struct dpu_hw_ctl *ctx);

'''+text[pos:]
p.write_text(text)
p=base/'dpu_rm.c'
text=p.read_text()
marker='static bool _dpu_rm_needs_split_display'
assert text.count(marker)==1
helper='''int dpu_rm_clear_boot_config(struct dpu_rm *rm, const struct dpu_mdss_cfg *cat)
{
	int i, ret;

	for (i = 0; i < cat->ctl_count; i++) {
		struct dpu_hw_ctl *ctl;

		ctl = to_dpu_hw_ctl(rm->ctl_blks[cat->ctl[i].id - CTL_0]);
		ret = dpu_hw_ctl_clear_boot_config(ctl);
		if (ret)
			return ret;
	}

	return 0;
}

'''
p.write_text(text.replace(marker,helper+marker))
p=base/'dpu_rm.h'
text=p.read_text()
pos=text.rindex('#endif')
text=text[:pos]+'''/**
 * dpu_rm_clear_boot_config() - quiesce inherited command-mode CTLs on SM8150
 * @rm: Initialized resource manager
 * @cat: SM8150 hardware catalog
 *
 * Return: 0 on success or a negative reset error.
 */
int dpu_rm_clear_boot_config(struct dpu_rm *rm, const struct dpu_mdss_cfg *cat);

'''+text[pos:]
p.write_text(text)
p=base/'dpu_kms.c'
text=p.read_text()
old='''	rc = _dpu_kms_mmu_init(dpu_kms);
	if (rc) {
		DPU_ERROR("dpu_kms_mmu_init failed: %d\\n", rc);
		goto err_pm_put;
	}

'''
assert text.count(old)==1
text=text.replace(old,'',1)
marker='\tdpu_kms->hw_mdp = dpu_hw_mdptop_init(dev,\n'
assert text.count(marker)==1
replacement='''	/* The boot framebuffer uses physical addresses in the identity domain. */
	if (of_device_is_compatible(dev->dev->of_node, "qcom,sm8150-dpu")) {
		rc = dpu_rm_clear_boot_config(&dpu_kms->rm, dpu_kms->catalog);
		if (rc) {
			DPU_ERROR("boot CTL shutdown failed: %d\\n", rc);
			goto err_pm_put;
		}
	}

'''+old+marker
p.write_text(text.replace(marker,replacement,1))
print('Prepared bounded SM8150 command-mode CTL shutdown before IOMMU attachment.')
