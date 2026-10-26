from pathlib import Path
import difflib, hashlib, json, subprocess

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel154')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel154')
out.mkdir(mode=0o700, exist_ok=True)
name = 'drivers/gpu/drm/msm/dsi/dsi_host.c'
before = (k/name).read_text()
assert hashlib.sha256(before.encode()).hexdigest() == '50d3ff181271d5fb7bc43f7138050446e95bccb12e80fd2c513622215ddd72d3'
panel = k/'drivers/gpu/drm/panel/panel-samsung-sofef03f.c'
assert hashlib.sha256(panel.read_bytes()).hexdigest() == '641b4a8e13230f28c095255ee9374ea746e8e55e9bba3c56b46b1d7886466cb3'
assert not (out/'dsi-before153-private.c').exists()
(out/'dsi-before153-private.c').write_text(before)
(out/'config-before-private').write_bytes((k/'.config').read_bytes())
other = subprocess.check_output(['git','diff','--binary','--','.',':(exclude)'+name],cwd=k)
(out/'other-diff-before-private.patch').write_bytes(other)
helper = '''/* Called only with the host link clocks enabled, before enabling its IRQ. */
static void dsi_log_power_on_state(struct msm_dsi_host *msm_host,
				   const char *phase)
{
	dev_info(&msm_host->pdev->dev,
		 "DSI power-on %s: CTRL=0x%x MDP2=0x%x DSC=0x%x TRIG=0x%x FIFO=0x%x\\n",
		 phase, dsi_read(msm_host, REG_DSI_CTRL),
		 dsi_read(msm_host, REG_DSI_CMD_MODE_MDP_CTRL2),
		 dsi_read(msm_host, REG_DSI_COMMAND_COMPRESSION_MODE_CTRL),
		 dsi_read(msm_host, REG_DSI_TRIG_CTRL),
		 dsi_read(msm_host, REG_DSI_FIFO_STATUS));
}

'''
mark = 'int msm_dsi_host_power_on(struct mipi_dsi_host *host,'
assert before.count(mark) == 1
after = before.replace(mark,helper+mark,1)
old = '\tdsi_timing_setup(msm_host, is_bonded_dsi);\n\tdsi_sw_reset(msm_host);'
assert after.count(old) == 1
after = after.replace(old,'''\tdsi_log_power_on_state(msm_host, "inherited");
	/* Do not resume a firmware command frame while replacing its timings. */
	dsi_ctrl_disable(msm_host);
	wmb(); /* Stop the inherited engine before changing its stream timing. */

'''+old,1)
old = '\tdsi_ctrl_enable(msm_host, phy_shared_timings, phy);'
assert after.count(old) == 1
after = after.replace(old,old+'\n\tdsi_log_power_on_state(msm_host, "native");',1)
(k/name).write_text(after)
patch='''Subject: [PATCH] drm/msm/dsi: stop inherited host before power-on timing setup

The first power-on may inherit an enabled firmware command engine. Writing
native timings before disabling it and letting soft reset restore its old
CTRL can resume a command frame without the native DPU being ready.
Disable the host with clocks available before timing setup and reset.
Keep the existing recovery reset semantics and normal native enable path.
Retain bounded power-on snapshots to compare first boot with normal DPMS.

---

diff --git a/'''+name+' b/'+name+'\n'+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(ref/'host-init.patch').write_text(patch)
assert subprocess.check_output(['git','diff','--binary','--','.',':(exclude)'+name],cwd=k) == other
report=dict(stage=154,baseline_kernel=153,modified_files=[name],
    baseline_sha256=hashlib.sha256(before.encode()).hexdigest(),candidate_sha256=hashlib.sha256(after.encode()).hexdigest(),
    panel153_retained=True,panel_sha256=hashlib.sha256(panel.read_bytes()).hexdigest(),
    dsi152_candidate_not_included=True,other_tracked_source_unchanged=True,
    clocks_enabled_before_mmio=True,irq_enabled_by_manager_after_power_on=True,
    error_reset_semantics_retained=True,hardware_root_cause_confirmed=False,deployed=False)
(ref/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
