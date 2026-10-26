"""Prepare typed LTM IQ/LUT encoding in the existing retained request."""
from pathlib import Path
import difflib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
h=(P/'camss-icp-a5-colour.h.before').read_text();assert h.endswith('#endif\n');h=h[:-7]+(HERE/'ltm-types.h').read_text()+'\n#endif\n'
c=(P/'camss-icp-a5-colour.c.before').read_text().replace('#include <linux/errno.h>', '#include <linux/errno.h>\n#include <linux/kernel.h>')+'\n'+(HERE/'ltm-codec-tail.c').read_text()
ih=(P/'camss-icp-a5-ipe.h.before').read_text();at=ih.index('int camss_a5_ipe_run(struct camss_a5 *a5, struct camss_a5_session *session,')
ih=ih[:at]+'''/* Optional quantized LTM with independent colour and Gamma. Large LUTs are
 * copied to temporary CPU memory under the engine lock, checked before DMA
 * allocation/MAP, then encoded into the same retained request as geometry.
 * Caller owns input-domain/tuning selection; this is not automatic tuning.
 * NULL LTM preserves the existing Gamma/colour path.
 */
int camss_a5_ipe_run_ltm_status(struct camss_a5 *a5,
			      struct camss_a5_session *session,
			      const struct camss_a5_ipe_job *job,
			      const struct camss_a5_ipe_colour *colour,
			      const struct camss_a5_ipe_gamma *gamma,
			      const struct camss_a5_ipe_ltm *ltm,
			      enum camss_a5_ipe_result *result);
'''+ih[at:]
boot=(P/'camss-icp-a5-boot.c.before').read_text();a=boot.index('static int run_colour_status(');b=boot.index('/* Preserve existing in-kernel callers',a);body=boot[a:b]
body=body.replace('const struct camss_a5_ipe_gamma *gamma,','const struct camss_a5_ipe_gamma *gamma,\n\t\t\t     const struct camss_a5_ipe_ltm *ltm,',1)
body=body.replace('struct camss_a5_ipe_gamma *gamma_copy = NULL;','struct camss_a5_ipe_gamma *gamma_copy = NULL;\n\tstruct camss_a5_ipe_ltm *ltm_copy = NULL;\n\tstruct camss_a5_ipe_ltm_geometry geometry = {};',1)
body=body.replace('u32 iq_bytes = gamma ?', 'u32 iq_bytes = ltm ? CAMSS_A5_IPE_LTM_IQ_BYTES : gamma ?',1).replace('cc && (chain || gamma)','cc && (chain || gamma || ltm)',1)
needle='\tif (cc) {\n\t\tcolour = *cc;';assert needle in body
body=body.replace(needle,'''\tif (ltm) {
		ltm_copy = kmemdup(ltm, sizeof(*ltm), GFP_KERNEL);
		if (!ltm_copy) {
			ret = -ENOMEM;
			goto done;
		}
		ret = camss_a5_ipe_ltm_check(ltm_copy);
		if (ret)
			goto done;
		geometry.data_collection = ltm_copy->iq.data_collection;
		geometry.image_processing = ltm_copy->iq.image_processing;
		geometry.mask_filter = ltm_copy->iq.mask_filter;
	}
'''+needle,1)
needle='\tret = camss_a5_ipe_bypass_size(&session->io, job->max_cores, &stripe_bytes);';assert needle in body
body=body.replace(needle,'''\tret = ltm_copy ?
		camss_a5_ipe_ltm_size(&session->io, job->max_cores, &geometry, &stripe_bytes) :
		camss_a5_ipe_bypass_size(&session->io, job->max_cores, &stripe_bytes);''',1)
needle='\tret = camss_a5_ipe_encode_bypass_striping(a5->request.cpu + PAGE_SIZE,';assert needle in body
body=body.replace(needle,'''\tif (ltm_copy)
		ret = camss_a5_ipe_encode_ltm_striping(a5->request.cpu + PAGE_SIZE,
						      stripe_bytes, &session->io,
						      job->max_cores, &geometry, &stripe_bytes);
	else
		ret = camss_a5_ipe_encode_bypass_striping(a5->request.cpu + PAGE_SIZE,''',1)
needle='\tif (gamma)\n\t\tret = camss_a5_ipe_encode_gamma_iq';assert needle in body
body=body.replace(needle,'''\tif (ltm_copy)
		ret = camss_a5_ipe_encode_ltm_iq(a5->request.cpu + iq_offset, iq_bytes,
					      REQUEST_IOVA + iq_offset,
					      chain ? &configuration : NULL,
					      gamma_copy, ltm_copy);
	else if (gamma)
		ret = camss_a5_ipe_encode_gamma_iq''',1)
needle='\tif (gamma || chain) {';assert needle in body
body=body.replace(needle,'''\tif (ltm_copy) {
		put_unaligned_le32(REQUEST_IOVA + iq_offset + CAMSS_A5_IPE_COLOUR_ARRAY_OFFSET,
				   a5->request.cpu + 40);
		put_unaligned_le32(CAMSS_A5_IPE_LTM_PRE_OFFSET, a5->request.cpu + 44);
		put_unaligned_le32(CAMSS_A5_IPE_LTM_POST_OFFSET, a5->request.cpu + 48);
	} else if (gamma || chain) {''',1)
body=body.replace('\tkfree(gamma_copy);','\tkfree(ltm_copy);\n\tkfree(gamma_copy);',1)
for old,new in [('job, NULL, NULL, NULL, result','job, NULL, NULL, NULL, NULL, result'),('job, cc, NULL, NULL, result','job, cc, NULL, NULL, NULL, result'),('job, NULL, colour, NULL, result','job, NULL, colour, NULL, NULL, result'),('job, NULL, colour, gamma, result','job, NULL, colour, gamma, NULL, result')]:
 assert old in body;body=body.replace(old,new)
body+='''int camss_a5_ipe_run_ltm_status(struct camss_a5 *a5,
			      struct camss_a5_session *session,
			      const struct camss_a5_ipe_job *job,
			      const struct camss_a5_ipe_colour *colour,
			      const struct camss_a5_ipe_gamma *gamma,
			      const struct camss_a5_ipe_ltm *ltm,
			      enum camss_a5_ipe_result *result)
{
	return run_colour_status(a5, session, job, NULL, colour, gamma, ltm, result);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_run_ltm_status);

'''
boot=boot[:a]+body+boot[b:]
rows={'camss-icp-a5-colour.h':h,'camss-icp-a5-colour.c':c,'camss-icp-a5-ipe.h':ih,'camss-icp-a5-boot.c':boot};patch=[]
for name,text in rows.items():
 (P/(name+'.proposed')).write_text(text);patch.extend(difflib.unified_diff((P/(name+'.before')).read_text().splitlines(True),text.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/'+name,tofile='b/drivers/media/platform/qcom/camss/'+name))
(P/'camss-icp-a5-ipe.c.proposed').write_bytes((P/'camss-icp-a5-ipe.c.before').read_bytes())
(HERE/'ltm-ownership.patch').write_text(''.join(patch))
print(json.dumps(dict(stage=405,proposal_written=True,files=list(rows),iq_bytes=8944,iq_allocation=12288,geometry_from_checked_copy=True,source_or_phone_mutated=False)))
