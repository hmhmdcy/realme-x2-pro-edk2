"""Prepare explicit, conservative per-job recovery classification in the core."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')=='a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07' and not git('status','--porcelain')
relative='drivers/media/platform/qcom/camss/';before={n:(source/relative/n).read_text() for n in ['camss-icp-a5-boot.c','camss-icp-a5-ipe.h','camss-icp-a5-m2m.c']};after=before.copy()
def edit(n,a,b):
 assert after[n].count(a)==1,(n,a);after[n]=after[n].replace(a,b)
edit('camss-icp-a5-ipe.h','int camss_a5_ipe_run(struct camss_a5 *a5,', '''/* A negative errno alone cannot distinguish a local input rejection from
 * an uncertain firmware command. RESET_REQUIRED is the fail-closed default.
 * REJECTED proves no transfer MAP was attempted and all transient backing
 * was released; it never permits retiring unknown hardware DMA ownership.
 */
enum camss_a5_ipe_result {
	CAMSS_A5_IPE_RESET_REQUIRED,
	CAMSS_A5_IPE_REJECTED,
	CAMSS_A5_IPE_COMPLETE,
};
int camss_a5_ipe_run_status(struct camss_a5 *a5, struct camss_a5_session *session,
			  const struct camss_a5_ipe_job *job,
			  enum camss_a5_ipe_result *result);
int camss_a5_ipe_run(struct camss_a5 *a5,''')
edit('camss-icp-a5-boot.c','int camss_a5_ipe_run(struct camss_a5 *a5, struct camss_a5_session *session,\n\t\t     const struct camss_a5_ipe_job *job)\n{', '''static bool transfer_released(struct camss_a5 *a5)
{
	return !a5->session_uncertain && !a5->ipe_dma_pending &&
	       !a5->config_fw_mapped && !a5->request_fw_mapped &&
	       !a5->request_owner && !a5->watchdogs && !a5->protocol_errors &&
	       !a5->request.cpu && !a5->request.mapped &&
	       !a5->image_input.cpu && !a5->image_input.mapped &&
	       !a5->image_output.cpu && !a5->image_output.mapped &&
	       !a5->dma_input.buffer && !a5->dma_output.buffer;
}

int camss_a5_ipe_run_status(struct camss_a5 *a5, struct camss_a5_session *session,
			  const struct camss_a5_ipe_job *job,
			  enum camss_a5_ipe_result *result)
{''')
# Edit only the new run function, avoiding similarly named earlier locals.
mark=after['camss-icp-a5-boot.c'].index('int camss_a5_ipe_run_status(');prefix=after['camss-icp-a5-boot.c'][:mark];run=after['camss-icp-a5-boot.c'][mark:]
run=run.replace('\tbool direct;\n\tint ret, cleanup;','\tbool direct, local_ready = false, firmware_attempted = false;\n\tint ret, cleanup = 0;\n\n\tif (result)\n\t\t*result = CAMSS_A5_IPE_RESET_REQUIRED;',1)
a='''	direct = job->input_dma || job->output_dma;
	if ((direct && (!job->input_dma || !job->output_dma || job->input || job->output)) ||
	    (!direct && (!job->input || !job->output || job->input_offset || job->output_offset)) ||
	    !job->bl_bytes || job->bl_bytes < 32 ||
	    !job->max_cores || job->max_cores > 2 || !job->target_time_ns)
		return -EINVAL;
'''
assert run.count(a)==1;run=run.replace(a,'\tdirect = job->input_dma || job->output_dma;\n',1)
run=run.replace('!a5->initialized || !a5->cpu_enabled || !a5->engine_dma_capable)', '!a5->initialized || !a5->cpu_enabled || !a5->irq_enabled ||\n\t    !a5->engine_dma_capable)',1)
a='''	if (a5->session_uncertain || a5->ipe_dma_pending ||
	    a5->request.cpu || a5->image_input.cpu || a5->image_output.cpu ||
	    a5->dma_input.buffer || a5->dma_output.buffer) {'''
assert run.count(a)==1;run=run.replace(a,'\tif (!transfer_released(a5)) {',1)
a='\tif (!nv12_layout_valid(&session->io.input) ||'
b='''	/* Only a configured, coherent engine may reject a job locally. */
	local_ready = true;
	if ((direct && (!job->input_dma || !job->output_dma || job->input || job->output)) ||
	    (!direct && (!job->input || !job->output || job->input_offset || job->output_offset)) ||
	    !job->bl_bytes || job->bl_bytes < 32 ||
	    !job->max_cores || job->max_cores > 2 || !job->target_time_ns) {
		ret = -EINVAL;
		goto done;
	}
	if (!nv12_layout_valid(&session->io.input) ||'''
assert run.count(a)==1;run=run.replace(a,b,1)
a='\tret = transfer_region_locked(a5, session, true);'
assert run.count(a)==1;run=run.replace(a,'\t/* Any attempted firmware MAP crosses the conservative reset boundary. */\n\tfirmware_attempted = true;\n'+a,1)
a='''done:
	mutex_unlock(&a5->lock);
	return ret;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_run);'''
b='''done:
	if (result) {
		if (!ret)
			*result = CAMSS_A5_IPE_COMPLETE;
		else if (local_ready && !firmware_attempted && !cleanup &&
			 transfer_released(a5))
			*result = CAMSS_A5_IPE_REJECTED;
	}
	mutex_unlock(&a5->lock);
	return ret;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_run_status);

/* Preserve existing in-kernel callers and their conservative errno contract. */
int camss_a5_ipe_run(struct camss_a5 *a5, struct camss_a5_session *session,
		     const struct camss_a5_ipe_job *job)
{
	return camss_a5_ipe_run_status(a5, session, job, NULL);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_run);'''
assert run.count(a)==1;run=run.replace(a,b,1);after['camss-icp-a5-boot.c']=prefix+run
edit('camss-icp-a5-m2m.c','\tint ret = -ECANCELED;','\tenum camss_a5_ipe_result result = CAMSS_A5_IPE_RESET_REQUIRED;\n\tint ret = -ECANCELED;')
edit('camss-icp-a5-m2m.c','ret = camss_a5_ipe_run(dev->a5, &ctx->session, &job);\n\tif (!ret)','ret = camss_a5_ipe_run_status(dev->a5, &ctx->session, &job, &result);\n\t/* A proven local rejection errors this queue, not the shared engine. */\n\tif (!ret || result == CAMSS_A5_IPE_REJECTED)')
for n,s in after.items():
 (P/(n+'.before')).write_text(before[n]);(P/(n+'.proposed')).write_text(s)
patch=''.join(''.join(difflib.unified_diff(before[n].splitlines(True),s.splitlines(True),fromfile='a/'+relative+n,tofile='b/'+relative+n)) for n,s in after.items())
(HERE/'local-job-errors.patch').write_text(patch)
report=dict(stage=393,parent=git('rev-parse','HEAD'),changed=list(after),explicit_core_result_not_errno_guess=True,default_reset_required=True,local_rejection_before_any_transfer_map_attempt=True,transient_backing_must_be_fully_released=True,legacy_core_api_kept=True,unknown_dma_retention_unchanged=True,installed=False,passed=True)
(HERE/'proposal-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
