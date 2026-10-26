"""Stop the inherited controller before changing the PHY/PLL, once per host."""
from pathlib import Path
import difflib,hashlib,json,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel157')
out=Path('/mnt/e/edk2-samurai-out/kernel157');out.mkdir(exist_ok=True)
names=['drivers/gpu/drm/msm/dsi/dsi_host.c','drivers/gpu/drm/msm/dsi/dsi_manager.c','drivers/gpu/drm/msm/dsi/dsi.h']
assert hashlib.sha256((k/names[0]).read_bytes()).hexdigest()=='f6eaf35bc05aeb913ea65954b0a4787ac6fbe26c0aedf74477f27076897e2adf'
base156=json.loads((ref.parent/'kernel156/build-package-validation.json').read_text())
for n,sha in base156['source_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==sha,n
before={n:(k/n).read_text() for n in names}
assert not (out/'source-before-private.json').exists()
(out/'source-before-private.json').write_text(json.dumps(before,indent=2))
(out/'config-before-private').write_bytes((k/'.config').read_bytes())
other=subprocess.check_output(['git','diff','--binary','--','.']+[':(exclude)'+n for n in names],cwd=k)
(out/'other-diff-before-private.patch').write_bytes(other)
host=before[names[0]]
needle='\tbool power_on;'
assert host.count(needle)==1
host=host.replace(needle,needle+'\n\tbool firmware_quiesced;',1)
needle='int msm_dsi_host_power_on(struct mipi_dsi_host *host,'
assert host.count(needle)==1
func='''/* Quiesce firmware output before the manager reconfigures the PHY/PLL. */
int msm_dsi_host_quiesce_firmware(struct mipi_dsi_host *host)
{
	struct msm_dsi_host *msm_host = to_msm_dsi_host(host);
	struct device *dev = &msm_host->pdev->dev;
	u32 before, after;
	int ret = 0;

	mutex_lock(&msm_host->dev_mutex);
	if (msm_host->firmware_quiesced || msm_host->power_on)
		goto unlock;

	/* Runtime resume enables the bus clocks needed for controller MMIO. */
	ret = pm_runtime_resume_and_get(dev);
	if (ret < 0)
		goto unlock;

	before = dsi_read(msm_host, REG_DSI_CTRL);
	dsi_ctrl_disable(msm_host);
	wmb(); /* Stop output before the later PHY reset and PLL rate change. */
	after = dsi_read(msm_host, REG_DSI_CTRL);
	if (after & DSI_CTRL_ENABLE) {
		dev_err(dev, "firmware controller stop failed: CTRL=0x%x\\n", after);
		ret = -EIO;
	} else {
		msm_host->firmware_quiesced = true;
		dev_info(dev, "DSI firmware stop before PHY: CTRL=0x%x -> 0x%x\\n",
			 before, after);
		ret = 0;
	}
	pm_runtime_put_sync(dev);
unlock:
	mutex_unlock(&msm_host->dev_mutex);
	return ret;
}

'''
host=host.replace(needle,func+needle,1)
manager=before[names[1]]
needle='\tret = dsi_mgr_phy_enable(id, phy_shared_timings);'
assert manager.count(needle)==1
manager=manager.replace(needle,'''	ret = msm_dsi_host_quiesce_firmware(host);
	if (ret)
		goto phy_en_fail;
	if (is_bonded_dsi && msm_dsi1) {
		ret = msm_dsi_host_quiesce_firmware(msm_dsi1->host);
		if (ret)
			goto phy_en_fail;
	}

'''+needle,1)
header=before[names[2]]
needle='int msm_dsi_host_power_on(struct mipi_dsi_host *host,'
assert header.count(needle)==1
header=header.replace(needle,'int msm_dsi_host_quiesce_firmware(struct mipi_dsi_host *host);\n'+needle,1)
after=dict(zip(names,[host,manager,header]))
for n,s in after.items():(k/n).write_text(s)
patch='Subject: [PATCH] drm/msm/dsi: stop firmware host before initial PHY setup\n\n'+\
    'Stop the inherited controller with runtime bus clocks before touching\n'+\
    'its PHY and PLL. Check readback, balance runtime references on failures,\n'+\
    'and skip the operation after the first successful handoff. Retain the\n'+\
    'existing native power-on reset and first-frame backlight policy.\n\n---\n\n'
for n in names:
    patch+='diff --git a/'+n+' b/'+n+'\n'+''.join(difflib.unified_diff(before[n].splitlines(True),after[n].splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'early-host-stop.patch').write_text(patch)
report=dict(stage=157,baseline_kernel=156,modified_files=names,
    before_sha256={n:hashlib.sha256(s.encode()).hexdigest() for n,s in before.items()},
    after_sha256={n:hashlib.sha256(s.encode()).hexdigest() for n,s in after.items()},
    first_frame156_preserved=True,dsi152_worker_changes_absent=True,
    config_unchanged=(k/'.config').read_bytes()==(out/'config-before-private').read_bytes(),
    hardware_root_cause_hypothesis=True,deployed=False)
(ref/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
