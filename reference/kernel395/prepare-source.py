from pathlib import Path
import difflib,hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
parent='64aaf4f78c05f0912e658780294fbded531d87ce';assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
relative='drivers/media/platform/qcom/camss/camss-icp-a5-boot.c';before=(source/relative).read_text();after=before
helper='''/* A forced reset must not leave the ICP/AHB bridge held in reset while
 * retiring its DMA aliases. Reuse the cold-start reset pulse, then prove
 * that releasing reset did not release the A5 CPU. A failed release/readback
 * retains ownership and is retried before any CSR access on the next stop.
 */
static int deassert_stopped_reset_locked(struct camss_a5 *a5)
{
	u32 control;
	int ret;

	ret = reset_control_deassert(a5->reset);
	if (ret)
		return ret;
	a5->reset_asserted = false;
	control = readl(a5->resources.sierra + A5_CONTROL);
	if (control & (A5_ENABLE | A5_WAKE)) {
		/* Treat an observed enabled CPU as live even after failed boot. */
		a5->cpu_enabled = true;
		a5->initialized = false;
		return -EIO;
	}
	return 0;
}

'''
a='static int quiesce_locked(struct camss_a5 *a5)\n';assert after.count(a)==1;after=after.replace(a,helper+a,1)
start=after.index('static int quiesce_locked(');end=after.index('\nstatic int stop_locked(',start);q=after[start:end]
a='\thrtimer_cancel(&a5->boot_timer);\n';assert q.count(a)==1;q=q.replace(a,a+'''	if (a5->reset_asserted) {
		ret = deassert_stopped_reset_locked(a5);
		if (ret)
			return ret;
		a5->cpu_enabled = false;
		a5->initialized = false;
	}
''',1)
a='''			/* Failed/uninitialized firmware needs a forced reset. A reset
			 * failure must retain the CPU, RAM and runtime-PM ownership.
			 */
			ret = reset_control_assert(a5->reset);
			if (ret)
				return ret;
			a5->reset_asserted = true;'''
b='''			/* Keep the forced reset guarantee for unknown completion,
			 * but reopen the bridge before IPE quiesce or DMA unmap.
			 * Every failed step keeps RAM/PM and any pending image DMA.
			 */
			ret = reset_control_assert(a5->reset);
			if (ret)
				return ret;
			a5->reset_asserted = true;
			a5->initialized = false;
			udelay(2); /* same verified pulse as the cold-start path */
			ret = deassert_stopped_reset_locked(a5);
			if (ret)
				return ret;
			dev_info(a5->dev, "A5 forced reset pulse complete; CPU enable/wake clear\\n");'''
assert q.count(a)==1;q=q.replace(a,b,1);after=after[:start]+q+after[end:]
a='''	 * A forced stop has asserted it already; resume releases it before
	 * enabling any clocks. The next explicit start owns the reset cycle.'''
b='''	 * A forced stop has pulsed reset and verified the CPU is disabled.
	 * Keep the bridge accessible through DMA retirement and power-down.'''
assert after.count(a)==1;after=after.replace(a,b,1)
for name in ['camss_a5_ipe_run_status','free_memory','free_imported_images','stop_locked']:
 pattern=r'(?:static )?(?:bool|int|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n'
 assert re.search(pattern,before,re.S|re.M).group()==re.search(pattern,after,re.S|re.M).group()
(P/'camss-icp-a5-boot.c.before').write_text(before);(P/'camss-icp-a5-boot.c.proposed').write_text(after)
(HERE/'forced-reset-pulse.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
r=dict(stage=395,parent=parent,changed=[relative],forced_reset_preserved=True,release_reset_and_check_cpu_disabled_before_ipe_and_dma_retirement=True,failed_release_retry_precedes_csr_access=True,transfer_and_free_functions_unchanged=True,no_board_userspace_or_factory_changes=True,installed=False,passed=True)
(HERE/'proposal-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
