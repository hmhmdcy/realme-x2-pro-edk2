from pathlib import Path
import difflib,hashlib,json,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel153')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel153')
out.mkdir(mode=0o700,exist_ok=True)
name='drivers/gpu/drm/panel/panel-samsung-sofef03f.c'
before=(k/name).read_text()
assert not (out/'panel-before147-private.c').exists()
(out/'panel-before147-private.c').write_text(before)
previous=json.loads((ref.parent/'kernel152/source-validation.json').read_text())
assert hashlib.sha256((k/'drivers/gpu/drm/msm/dsi/dsi_host.c').read_bytes()).hexdigest()==previous['before_sha256']
(out/'config-before-private').write_bytes((k/'.config').read_bytes())
other=subprocess.check_output(['git','diff','--binary'],cwd=k)
(out/'other-diff-before-private.patch').write_bytes(other)
helper='''/* Configure outputs only after KMS has stopped the firmware scanout. */
static int sofef03f_init_gpios(struct sofef03f *ctx)
{
	int ret;

	ret = gpiod_direction_output(ctx->reset, 1);
	if (ret)
		return ret;
	ret = gpiod_direction_output(ctx->vddd, 0);
	if (ret)
		return ret;
	return gpiod_direction_output(ctx->vci, 0);
}

'''
after=before.replace('static int sofef03f_prepare(struct drm_panel *panel)',helper+'static int sofef03f_prepare(struct drm_panel *panel)',1)
old='\tret = sofef03f_supply_enable(ctx, 0);'
assert after.count(old)==1
after=after.replace(old,'\tret = sofef03f_init_gpios(ctx);\n\tif (ret)\n\t\treturn ret;\n\n'+old,1)
for label,flag in [('reset','GPIOD_OUT_HIGH'),('vci-enable','GPIOD_OUT_LOW'),('vddd-enable','GPIOD_OUT_LOW')]:
    old=f'devm_gpiod_get(dev, "{label}", {flag})'
    assert after.count(old)==1
    after=after.replace(old,f'devm_gpiod_get(dev, "{label}", GPIOD_ASIS)')
comment='\tctx->reset = devm_gpiod_get'
after=after.replace(comment,'\t/* mipi_dsi_attach() must quiesce the boot frame before panel reset. */\n'+comment,1)
(k/name).write_text(after)
patch='''Subject: [PATCH] drm/panel: sofef03f: defer GPIO shutdown until prepare

The panel probe precedes DPU boot scanout quiescence via mipi_dsi_attach.
Driving reset and both enable GPIOs at probe can cut a DSC frame short
before the inherited CTL is stopped. Preserve firmware pin state while
acquiring the GPIOs, then configure directions and off levels in prepare.
Retain native power sequencing, DSC setup and error teardown.

---

diff --git a/'''+name+' b/'+name+'\n'+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(ref/'panel-gpio-handoff.patch').write_text(patch)
assert subprocess.check_output(['git','diff','--binary'],cwd=k)==other
report=dict(stage=153,baseline_kernel=147,modified_files=[name],
    baseline_sha256=hashlib.sha256(before.encode()).hexdigest(),candidate_sha256=hashlib.sha256(after.encode()).hexdigest(),
    dsi152_candidate_not_included=True,other_tracked_source_unchanged=True,
    dtb_and_configuration_unchanged=True,probe_preserves_firmware_gpio=True,
    native_panel_sequence_retained=True,hardware_root_cause_confirmed=False,deployed=False)
(ref/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
