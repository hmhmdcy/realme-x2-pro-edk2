from pathlib import Path
import difflib,hashlib,json,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel158')
out=Path('/mnt/e/edk2-samurai-out/kernel158');out.mkdir(exist_ok=True)
base=json.loads((ref.parent/'kernel157/build-package-validation.json').read_text())
for n,h in base['source_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==h,n
names=['drivers/gpu/drm/msm/dsi/dsi.c','drivers/gpu/drm/msm/msm_drv.h','drivers/gpu/drm/msm/disp/dpu1/dpu_kms.c']
before={n:(k/n).read_text() for n in names}
if (out/'source-before-private.json').exists():
    assert json.loads((out/'source-before-private.json').read_text())==before
(out/'source-before-private.json').write_text(json.dumps(before,indent=2))
(out/'config-before-private').write_bytes((k/'.config').read_bytes())
(out/'other-diff-before-private.patch').write_bytes(subprocess.check_output(['git','diff','--binary','--','.']+[':(exclude)'+n for n in names],cwd=k))
dsi=before[names[0]];needle='bool msm_dsi_is_cmd_mode(struct msm_dsi *msm_dsi)'
assert dsi.count(needle)==1
dsi=dsi.replace(needle,'''int msm_dsi_quiesce_firmware(struct msm_dsi *msm_dsi)
{
	return msm_dsi_host_quiesce_firmware(msm_dsi->host);
}

'''+needle,1)
header=before[names[1]];needle='bool msm_dsi_is_cmd_mode(struct msm_dsi *msm_dsi);'
assert header.count(needle)==1
header=header.replace(needle,'int msm_dsi_quiesce_firmware(struct msm_dsi *msm_dsi);\n'+needle,1)
needle='static inline bool msm_dsi_is_cmd_mode(struct msm_dsi *msm_dsi)'
assert header.count(needle)==1
header=header.replace(needle,'''
static inline int msm_dsi_quiesce_firmware(struct msm_dsi *msm_dsi)
{
	return 0;
}
'''+needle,1)
kms=before[names[2]];needle='static int dpu_kms_hw_init(struct msm_kms *kms)\n{'
assert kms.count(needle)==1
kms=kms.replace(needle,'''static int dpu_kms_quiesce_boot_dsi(struct msm_kms *kms)
{
	unsigned int i;
	int ret;

	for (i = 0; i < ARRAY_SIZE(kms->dsi); i++) {
		if (!kms->dsi[i])
			continue;
		ret = msm_dsi_quiesce_firmware(kms->dsi[i]);
		if (ret)
			return ret;
	}
	return 0;
}

'''+needle,1)
needle='\t\trc = dpu_rm_clear_boot_config(&dpu_kms->rm, dpu_kms->catalog);'
assert kms.count(needle)==1
kms=kms.replace(needle,'''		/* Stop the firmware DSI consumer before resetting its CTL producer. */
		rc = dpu_kms_quiesce_boot_dsi(kms);
		if (rc) {
			DPU_ERROR("DSI firmware stop failed: %d\\n", rc);
			goto err_pm_put;
		}
'''+needle,1)
after=dict(zip(names,[dsi,header,kms]))
for n,s in after.items():(k/n).write_text(s)
patch='Subject: [PATCH] drm/msm/dpu: quiesce firmware DSI before boot CTL reset\n\n'+\
    'The initial DPU boot CTL reset can fail before a native modeset runs.\n'+\
    'Stop each bound DSI host with runtime bus clocks before clearing the\n'+\
    'SM8150 boot configuration. Reuse the checked, one-shot host handoff\n'+\
    'and keep the later before-PHY call as an idempotent fallback.\n\n---\n\n'
for n in names:patch+='diff --git a/'+n+' b/'+n+'\n'+''.join(difflib.unified_diff(before[n].splitlines(True),after[n].splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'before-ctl-stop.patch').write_text(patch)
report=dict(stage=158,baseline_kernel=157,modified_files=names,
    before_sha256={n:hashlib.sha256(s.encode()).hexdigest() for n,s in before.items()},
    after_sha256={n:hashlib.sha256(s.encode()).hexdigest() for n,s in after.items()},
    first_frame156_and_host157_functions_preserved=True,sm8150_boot_cleanup_scope=True,
    config_unchanged=(k/'.config').read_bytes()==(out/'config-before-private').read_bytes(),deployed=False)
(ref/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
