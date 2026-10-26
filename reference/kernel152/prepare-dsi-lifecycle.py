"""Save #147 source and apply a narrowly scoped DSI lifecycle fix."""
from pathlib import Path
import difflib, hashlib, json, subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel152')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel152')
out.mkdir(mode=0o700,exist_ok=True)
path='drivers/gpu/drm/msm/dsi/dsi_host.c'
p=k/path
before=p.read_text()
backup=out/'dsi_host.c.before147-private'
if backup.exists():
    assert backup.read_text()==before, 'Cannot resume against changed source'
else:
    backup.write_text(before)
(out/'config-before-private').write_bytes((k/'.config').read_bytes())
other=subprocess.check_output(['git','diff','--binary','--','.',':(exclude)'+path],cwd=k)
(out/'other-diff-before-private.patch').write_bytes(other)
after=before

def replace(old,new):
    global after
    assert after.count(old)==1, old
    after=after.replace(old,new)

replace('u32 status = msm_host->err_work_state;\n\n\ttrace_msm_dsi_error_work',
    'u32 status;\n\n\t/* Serialize reset with command DMA and host power/mode changes. */\n'
    '\tmutex_lock(&msm_host->cmd_mutex);\n\tstatus = msm_host->err_work_state;\n\n\ttrace_msm_dsi_error_work')
replace('\tif (status & DSI_ERR_STATE_MDP_FIFO_UNDERFLOW)\n\t\tdsi_sw_reset(msm_host);',
    '\tif (msm_host->power_on &&\n\t    (status & DSI_ERR_STATE_MDP_FIFO_UNDERFLOW))\n\t\tdsi_sw_reset(msm_host);')
replace('\t/* enable dsi error interrupt */\n\tdsi_intr_ctrl(msm_host, DSI_IRQ_MASK_ERROR, 1);\n\ttrace_msm_dsi_error_work(msm_host->id, status, true);',
    '\t/* A late worker must not touch registers after clocks are off. */\n'
    '\tif (msm_host->power_on)\n\t\tdsi_intr_ctrl(msm_host, DSI_IRQ_MASK_ERROR, 1);\n'
    '\ttrace_msm_dsi_error_work(msm_host->id, status, true);\n\tmutex_unlock(&msm_host->cmd_mutex);')
replace('\tif (!msg || !msm_host->power_on)\n\t\treturn -EINVAL;\n\n\tmutex_lock(&msm_host->cmd_mutex);\n\tret = msm_dsi_manager_cmd_xfer(msm_host->id, msg);',
    '\tif (!msg)\n\t\treturn -EINVAL;\n\n\tmutex_lock(&msm_host->cmd_mutex);\n'
    '\tif (!msm_host->power_on)\n\t\tret = -EINVAL;\n\telse\n'
    '\t\tret = msm_dsi_manager_cmd_xfer(msm_host->id, msg);')
replace('\tdisable_irq(msm_host->irq);\n}',
    '\tdisable_irq(msm_host->irq);\n'
    '\t/* No new error work can be queued; drain it while clocks are on. */\n'
    '\tcancel_work_sync(&msm_host->err_work);\n\tmsm_host->err_work_state = 0;\n}')
replace('int msm_dsi_host_enable(struct mipi_dsi_host *host)\n{\n\tstruct msm_dsi_host *msm_host = to_msm_dsi_host(host);\n\n\tdsi_op_mode_config',
    'int msm_dsi_host_enable(struct mipi_dsi_host *host)\n{\n\tstruct msm_dsi_host *msm_host = to_msm_dsi_host(host);\n\n'
    '\tmutex_lock(&msm_host->cmd_mutex);\n\tdsi_op_mode_config')
replace('\tmsm_host->enabled = true;\n\treturn 0;',
    '\tmsm_host->enabled = true;\n\tmutex_unlock(&msm_host->cmd_mutex);\n\treturn 0;')
replace('\tmsm_host->enabled = false;\n\tdsi_op_mode_config',
    '\tmutex_lock(&msm_host->cmd_mutex);\n\tmsm_host->enabled = false;\n\tdsi_op_mode_config')
replace('\tdsi_sw_reset(msm_host);\n\n\treturn 0;',
    '\tdsi_sw_reset(msm_host);\n\tmutex_unlock(&msm_host->cmd_mutex);\n\n\treturn 0;')
# Both power entry points consistently nest cmd_mutex inside dev_mutex.
assert after.count('\tmutex_lock(&msm_host->dev_mutex);\n')==2
after=after.replace('\tmutex_lock(&msm_host->dev_mutex);\n',
    '\tmutex_lock(&msm_host->dev_mutex);\n\tmutex_lock(&msm_host->cmd_mutex);\n')
assert after.count('\tmutex_unlock(&msm_host->dev_mutex);\n')==3
after=after.replace('\tmutex_unlock(&msm_host->dev_mutex);\n',
    '\tmutex_unlock(&msm_host->cmd_mutex);\n\tmutex_unlock(&msm_host->dev_mutex);\n')
p.write_text(after)
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
    fromfile='a/'+path,tofile='b/'+path))
(ref/'dsi-lifecycle.patch').write_text(patch)
assert subprocess.check_output(['git','diff','--binary','--','.',':(exclude)'+path],cwd=k)==other
assert (k/'.config').read_bytes()==(out/'config-before-private').read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
report=dict(stage=152,baseline_kernel=147,modified_files=[path],
    before_sha256=sha(before.encode()),after_sha256=sha(after.encode()),
    other_tracked_diffs_unchanged=True,config_unchanged=True,
    behavior='serialize error reset, DMA, mode and power; drain pending work before IRQ-off teardown',
    hardware_root_cause_confirmed=False,deployed=False)
(ref/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
