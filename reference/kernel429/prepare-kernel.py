"""Connect typed PD10 ownership, native two-pass geometry and frame port 1."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
source=m.mounted_build().parent/'source354';camss=source/'drivers/media/platform/qcom/camss'
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True)
base='906a6b9d26afe0e7c3f3758dad2fb5c0e778634e'
assert git('rev-parse','HEAD').strip()==base and not git('status','--porcelain')
subprocess.run(['git','-C',str(source),'switch','-c','samurai-ipe-pd10-runtime429'],capture_output=True,check=True)
def replace(text,a,b,count=1):
 assert text.count(a)==count,(a[:100],text.count(a),count)
 return text.replace(a,b)
names=['camss-icp-a5-boot.h','camss-icp-a5-ipe.h','camss-icp-a5-ipe.c','camss-icp-a5-boot.c']
before={n:(camss/n).read_text() for n in names}
t=before[names[0]]
t=replace(t,'\tu32 scratch_bytes;\n\tbool configured;','\tu32 scratch_bytes;\n\tstruct camss_a5_pd10_layout coarse;\n\tbool configured;')
t=replace(t,'struct camss_a5_dma_image dma_input, dma_output;','struct camss_a5_dma_image dma_input, dma_output, dma_coarse;')
t=replace(t,'bool camss_a5_backing_owned(','''int camss_a5_ipe_configure_nv12_pd10(struct camss_a5 *a5,
				    struct camss_a5_session *session,
				    const struct camss_a5_ipe_io *io,
				    const struct camss_a5_pd10_layout *coarse);
bool camss_a5_backing_owned(''');(camss/names[0]).write_text(t)
t=before[names[1]]
t=replace(t,'struct camss_a5_ipe_buffer striping, iq, scratch, bl, input, output;','struct camss_a5_ipe_buffer striping, iq, scratch, bl, input, output, coarse;')
t=replace(t,'int camss_a5_ipe_run(struct camss_a5 *a5,', '''/* Optional real PD10 input, matched to the configured FULL image by caller.
 * CPU pixels and DMA-BUF imports are mutually exclusive. The core retains
 * imported backing on uncertain DMA just like FULL input/output.
 * Diagnostic scratch copy is returned only after successful completion.
 */
struct camss_a5_ipe_coarse_input {
	const void *pixels;
	struct dma_buf *dma;
	u32 offset, bytes;
	void *scratch_output;
	u32 scratch_capacity;
};
int camss_a5_ipe_run_ltm_pd10_status(struct camss_a5 *a5,
				   struct camss_a5_session *session,
				   const struct camss_a5_ipe_job *job,
				   const struct camss_a5_ipe_colour *colour,
				   const struct camss_a5_ipe_gamma *gamma,
				   const struct camss_a5_ipe_ltm *ltm,
				   const struct camss_a5_ipe_coarse_input *coarse,
				   enum camss_a5_ipe_result *result);
int camss_a5_ipe_run(struct camss_a5 *a5,''')
t=replace(t,'\n#endif','''
int camss_a5_ipe_ltm_pd10_size(const struct camss_a5_ipe_io *io, u32 cores,
			     const struct camss_a5_ipe_ltm_geometry *ltm,
			     u32 *bytes);
int camss_a5_ipe_encode_ltm_pd10_striping(void *buffer, u32 capacity,
					const struct camss_a5_ipe_io *io,
					u32 cores,
					const struct camss_a5_ipe_ltm_geometry *ltm,
					u32 *used);
#endif''');(camss/names[1]).write_text(t)
t=before[names[2]]
t=replace(t,'const struct camss_a5_ipe_buffer *buffers[6];','const struct camss_a5_ipe_buffer *buffers[7];\n\tstruct camss_a5_pd10_layout expected;')
t=replace(t,'u32 input_y, output_y, used, i, j;','u32 input_y, output_y, used, i, j, count = 6;')
t=replace(t,'\tfor (i = 0; i < 6; i++) {','''	if (frame->coarse.bytes || frame->coarse.iova) {
		ret = camss_a5_ipe_pd10_quarter(&io->input, &expected);
		if (ret || frame->coarse.bytes != expected.bytes)
			return -EINVAL;
		buffers[count++] = &frame->coarse;
	}
	for (i = 0; i < count; i++) {''')
t=replace(t,'\tput_unaligned_le32(frame->input.iova + input_y, output + 96);','\tput_unaligned_le32(frame->input.iova + input_y, output + 96);\n\tif (frame->coarse.bytes)\n\t\tput_unaligned_le32(frame->coarse.iova, output + 108);')
t+='\n'+(HERE/'ltm-pd10-stripe.c').read_text().split('*/',1)[1].lstrip();(camss/names[2]).write_text(t)
t=before[names[3]]
t=replace(t,'int camss_a5_ipe_configure_nv12(struct camss_a5 *a5,\n\t\t\t       struct camss_a5_session *session,\n\t\t\t       const struct camss_a5_ipe_io *io)',
'''static int configure_ipe_io(struct camss_a5 *a5,
			    struct camss_a5_session *session,
			    const struct camss_a5_ipe_io *io,
			    const struct camss_a5_pd10_layout *coarse)''')
t=replace(t,'camss_a5_ipe_encode_io(a5->config.cpu, a5->config.bytes, io, NULL)','camss_a5_ipe_encode_io(a5->config.cpu, a5->config.bytes, io, coarse)')
t=replace(t,'\t\tsession->io = *io;','\t\tsession->io = *io;\n\t\tsession->coarse = coarse ? *coarse : (struct camss_a5_pd10_layout){};')
t=replace(t,'EXPORT_SYMBOL_GPL(camss_a5_ipe_configure_nv12);','''int camss_a5_ipe_configure_nv12(struct camss_a5 *a5,
			       struct camss_a5_session *session,
			       const struct camss_a5_ipe_io *io)
{
	return configure_ipe_io(a5, session, io, NULL);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_configure_nv12);

int camss_a5_ipe_configure_nv12_pd10(struct camss_a5 *a5,
				    struct camss_a5_session *session,
				    const struct camss_a5_ipe_io *io,
				    const struct camss_a5_pd10_layout *coarse)
{
	if (!coarse)
		return -EINVAL;
	return configure_ipe_io(a5, session, io, coarse);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_configure_nv12_pd10);''')
t=replace(t,'\tsession->scratch_bytes = 0;\n\ta5->session_count--;','\tsession->scratch_bytes = 0;\n\tmemset(&session->coarse, 0, sizeof(session->coarse));\n\ta5->session_count--;')
t=replace(t,'\t\tsession->scratch_bytes = 0;\n\t}','\t\tsession->scratch_bytes = 0;\n\t\tmemset(&session->coarse, 0, sizeof(session->coarse));\n\t}')
t=replace(t,'a5->dma_input.buffer || a5->dma_output.buffer;','a5->dma_input.buffer || a5->dma_output.buffer || a5->dma_coarse.buffer;')
t=replace(t,'!a5->dma_input.buffer && !a5->dma_output.buffer;','!a5->dma_input.buffer && !a5->dma_output.buffer && !a5->dma_coarse.buffer;')
t=replace(t,' ret = camss_a5_dma_image_release(&a5->dma_output);',' ret = camss_a5_dma_image_release(&a5->dma_coarse);\n if (ret)\n  return ret;\n ret = camss_a5_dma_image_release(&a5->dma_output);')
# Only the private implementation gains a typed optional argument. Legacy
# exported job layout and entry points remain unchanged.
a=t.index('static int run_colour_status(');z=t.index('int camss_a5_ipe_run_status(',a);run=t[a:z]
run=replace(run,'\t\t\t     enum camss_a5_ipe_result *result)','\t\t\t     const struct camss_a5_ipe_coarse_input *coarse,\n\t\t\t     enum camss_a5_ipe_result *result)')
run=replace(run,'u32 stripe_bytes, iq_offset, scratch_offset, bl_offset;','u32 stripe_bytes, iq_offset, scratch_offset, bl_offset, coarse_offset;')
run=replace(run,'\tret = ltm_copy ?\n\t\tcamss_a5_ipe_ltm_size', '''	if (!!coarse != !!session->coarse.bytes ||
	    (coarse && (!ltm_copy || coarse->bytes < session->coarse.bytes ||
	     (direct && (!coarse->dma || coarse->pixels)) ||
	     (!direct && (!coarse->pixels || coarse->dma || coarse->offset)) ||
	     (coarse->scratch_output && coarse->scratch_capacity < session->scratch_bytes) ||
	     (!coarse->scratch_output && coarse->scratch_capacity)))) {
		ret = -EINVAL;
		goto done;
	}
	ret = coarse ?
		camss_a5_ipe_ltm_pd10_size(&session->io, job->max_cores, &geometry, &stripe_bytes) :
		ltm_copy ?
		camss_a5_ipe_ltm_size''')
run=replace(run,'\tparcel = PAGE_ALIGN((u64)bl_offset + job->bl_bytes);','\tcoarse_offset = PAGE_ALIGN((u64)bl_offset + job->bl_bytes);\n\tparcel = coarse_offset + (coarse && !direct ? PAGE_ALIGN(session->coarse.bytes) : 0);')
run=replace(run,'\t} else {\n\t\tret = transfer_alloc(a5, &a5->image_input,', '''		if (!ret && coarse)
			ret = camss_a5_dma_image_map(a5->dev, &a5->dma_coarse, coarse->dma,
						     coarse->offset, session->coarse.bytes, DMA_TO_DEVICE);
		if (!ret && coarse)
			ret = camss_a5_dma_images_disjoint(&a5->dma_coarse, &a5->dma_input);
		if (!ret && coarse)
			ret = camss_a5_dma_images_disjoint(&a5->dma_coarse, &a5->dma_output);
	} else {
		ret = transfer_alloc(a5, &a5->image_input,''')
run=replace(run,'\tif (ltm_copy)\n\t\tret = camss_a5_ipe_encode_ltm_striping', '''	if (coarse)
		ret = camss_a5_ipe_encode_ltm_pd10_striping(a5->request.cpu + PAGE_SIZE,
				stripe_bytes, &session->io, job->max_cores, &geometry, &stripe_bytes);
	else if (ltm_copy)
		ret = camss_a5_ipe_encode_ltm_striping''')
run=replace(run,'\tframe.striping = (struct camss_a5_ipe_buffer)', '''	if (coarse) {
		memset(a5->request.cpu + scratch_offset, 0xa7, session->scratch_bytes);
		if (!direct)
			memcpy(a5->request.cpu + coarse_offset, coarse->pixels, session->coarse.bytes);
		frame.coarse = (struct camss_a5_ipe_buffer){
			direct ? a5->dma_coarse.iova : REQUEST_IOVA + coarse_offset,
			session->coarse.bytes };
	}
	frame.striping = (struct camss_a5_ipe_buffer)''')
run=replace(run,'\t\ta5->frames_completed++;\n\t\tdma_rmb();','''		a5->frames_completed++;
		dma_rmb();
		if (coarse && coarse->scratch_output)
			memcpy(coarse->scratch_output, a5->request.cpu + scratch_offset,
			       session->scratch_bytes);''')
t=t[:a]+run+t[z:]
for a,b in [('job, NULL, NULL, NULL, NULL, result','job, NULL, NULL, NULL, NULL, NULL, result'),
 ('job, cc, NULL, NULL, NULL, result','job, cc, NULL, NULL, NULL, NULL, result'),
 ('job, NULL, colour, NULL, NULL, result','job, NULL, colour, NULL, NULL, NULL, result'),
 ('job, NULL, colour, gamma, NULL, result','job, NULL, colour, gamma, NULL, NULL, result'),
 ('job, NULL, colour, gamma, ltm, result','job, NULL, colour, gamma, ltm, NULL, result')]:t=replace(t,a,b)
t+='''
int camss_a5_ipe_run_ltm_pd10_status(struct camss_a5 *a5,
				   struct camss_a5_session *session,
				   const struct camss_a5_ipe_job *job,
				   const struct camss_a5_ipe_colour *colour,
				   const struct camss_a5_ipe_gamma *gamma,
				   const struct camss_a5_ipe_ltm *ltm,
				   const struct camss_a5_ipe_coarse_input *coarse,
				   enum camss_a5_ipe_result *result)
{
	if (!coarse) {
		if (result)
			*result = CAMSS_A5_IPE_RESET_REQUIRED;
		return -EINVAL;
	}
	return run_colour_status(a5, session, job, NULL, colour, gamma, ltm, coarse, result);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_run_ltm_pd10_status);
''';(camss/names[3]).write_text(t)
subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',*[str(camss/n) for n in names]],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','media: camss: own explicit PD10 and prepare native LTM coarse/full passes'],check=True)
(HERE/'pd10-runtime.patch').write_text(git('diff',base,'HEAD'))
r=dict(stage=429,parent_commit=base,commit=git('rev-parse','HEAD').strip(),branch=git('branch','--show-current').strip(),
 source_hashes=[dict(path='drivers/media/platform/qcom/camss/'+n,sha256=hashlib.sha256((camss/n).read_bytes()).hexdigest()) for n in names],
 native_two_pass_initial_scope='640x480 NV12, display port8, two cores, DC+IP+mask',legacy_job_and_user_api_unchanged=True,
 direct_pd10_dma_reference_and_uncertain_completion_ownership=True,cpu_fixture_pd10_in_owned_request_parcel=True,
 hardware_validated=False,m2m_and_ipa_not_yet_connected=True,installed=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
