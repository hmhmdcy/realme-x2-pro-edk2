"""Select single/dual-pass firmware sessions from the validated request program."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage431kernel',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);k=m.mounted_build().parent/'source354'
git=lambda *a:subprocess.check_output(['git','-C',str(k),*a])
parent=git('rev-parse','HEAD').decode().strip();assert parent=='d4ac27ac5cf595c9fc7c612dfdfdbcc1a002675a' and not git('status','--porcelain')
if git('branch','--show-current').decode().strip()!='samurai-ipe-request-coarse431':subprocess.run(['git','-C',str(k),'switch','-c','samurai-ipe-request-coarse431'],check=True)
rel='drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c';p=k/rel;t=p.read_text()
def replace(a,b):
 global t
 assert t.count(a)==1,(a,t.count(a));t=t.replace(a,b)
replace('static int ensure_session(struct ipe_context *ctx)','static int ensure_session(struct ipe_context *ctx, bool use_coarse)')
replace('if (ctx->session.configured)\n\t\treturn 0;','''if (ctx->session.configured) {
		if (!!ctx->session.coarse.bytes == use_coarse)
			return 0;
		/* A bootstrap/held request can legitimately contain no LTM program.
		 * Switch only after the previous transfer retired; destroy keeps
		 * its existing uncertain-completion ownership checks.
		 */
		ret = camss_a5_ipe_destroy(dev->a5, &ctx->session);
		if (ret)
			return ret;
	}''')
replace('if (!ret && ctx->coarse) {\n\t\tret = camss_a5_ipe_pd10_quarter','if (!ret && use_coarse) {\n\t\tret = camss_a5_ipe_pd10_quarter')
replace('bool queue_error = false;','bool queue_error = false, use_coarse = false;')
replace('\tinput = image_buffer(&src->vb2_buf, 0);','''	/* QN10 always owns both submitted planes. Import the second plane for
	 * hardware only when this validated program requests a DC pass.
	 */
	use_coarse = ctx->coarse && params && (params->flags & QCOM_IPE_A5_LTM) &&
		     params->ltm.iq.data_collection;
	input = image_buffer(&src->vb2_buf, 0);''')
replace('\tif (ctx->coarse) {\n\t\tcoarse_buffer','\tif (use_coarse) {\n\t\tcoarse_buffer')
replace('ret = ensure_session(ctx);','ret = ensure_session(ctx, use_coarse);')
replace('frame_params_run(ctx, &job, ctx->coarse ? &coarse : NULL, params, &result)','frame_params_run(ctx, &job, use_coarse ? &coarse : NULL, params, &result)')
replace('if (!ret && ctx->coarse) {','if (!ret && use_coarse) {')
p.write_text(t);subprocess.run(['git','-C',str(k),'add','--',rel],check=True);subprocess.run(['git','-C',str(k),'commit','-m','media: camss: match paired-source sessions to request DC use'],check=True)
commit=git('rev-parse','HEAD').decode().strip();(HERE/'request-coarse.patch').write_bytes(git('diff',parent,commit))
r=dict(stage=431,parent_commit=parent,commit=commit,branch='samurai-ipe-request-coarse431',source_hashes=[dict(path=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest())],user_abi_and_dma_release_policy_unchanged=True,no_mmio_added=True,installed=False,passed=True)
(HERE/'kernel-source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
