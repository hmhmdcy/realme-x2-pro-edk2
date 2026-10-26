"""Prepare typed Gamma LUT ownership and correct original generic tags."""
from pathlib import Path
import difflib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'contract-validation.json').read_text())['passed']
h=(P/'camss-icp-a5-colour.h.before').read_text();at=h.index('\n#endif')
h=h[:at]+'''
/* Target LUT selector order is G, B, R. Values are quantized Gamma15
 * base10 and signed delta10, not arbitrary CDM words or device addresses.
 */
struct camss_a5_ipe_gamma {
	u16 base[3][256];
	s16 delta[3][256];
};

#define CAMSS_A5_IPE_PROGRAM_GENERIC 20U
#define CAMSS_A5_IPE_PROGRAM_GAMMA 12U
#define CAMSS_A5_IPE_GAMMA_CST_PACKET_OFFSET 2752U
#define CAMSS_A5_IPE_GAMMA_CC_PACKET_OFFSET 2808U
#define CAMSS_A5_IPE_GAMMA_CV_PACKET_OFFSET 2852U
#define CAMSS_A5_IPE_GAMMA_DMI_OFFSET 2896U
#define CAMSS_A5_IPE_GAMMA_LUT_OFFSET 2944U
#define CAMSS_A5_IPE_GAMMA_IQ_BYTES 6016U

int camss_a5_ipe_gamma_check(const struct camss_a5_ipe_gamma *gamma);
int camss_a5_ipe_encode_gamma_iq(void *destination, u32 bytes, u32 iq_iova,
			       const struct camss_a5_ipe_colour *colour,
			       const struct camss_a5_ipe_gamma *gamma);
'''+h[at:]
c=(P/'camss-icp-a5-colour.c.before').read_text()
needle='put_unaligned_le32((CAMSS_A5_IPE_CC_COMMAND_BYTES - 1) << 12,\n\t\t\t   output + post + 12);';assert needle in c
c=c.replace(needle,needle+'\n\tput_unaligned_le32(CAMSS_A5_IPE_PROGRAM_GENERIC, output + post + 16);')
needle='put_unaligned_le32((bytes - 1) << 12, descriptor + 4);';assert c.count(needle)==1;c=c.replace(needle,needle+'\n\tput_unaligned_le32(CAMSS_A5_IPE_PROGRAM_GENERIC, descriptor + 8);')
c+='\n'+(HERE/'gamma-codec-tail.c').read_text()
header=(P/'camss-icp-a5-ipe.h.before').read_text();at=header.index('int camss_a5_ipe_run(struct camss_a5 *a5, struct camss_a5_session *session,')
header=header[:at]+'''/* LUT input is copied into temporary CPU memory, validated before coherent
 * allocation, encoded in the retained request, then freed on every exit.
 * NULL Gamma retains the existing colour/bypass interface behaviour.
 */
int camss_a5_ipe_run_gamma_status(struct camss_a5 *a5,
				struct camss_a5_session *session,
				const struct camss_a5_ipe_job *job,
				const struct camss_a5_ipe_colour *colour,
				const struct camss_a5_ipe_gamma *gamma,
				enum camss_a5_ipe_result *result);
'''+header[at:]
boot=(P/'camss-icp-a5-boot.c.before').read_text();assert '#include <linux/slab.h>' in boot
a=boot.index('static int run_colour_status(');b=boot.index('EXPORT_SYMBOL_GPL(camss_a5_ipe_run_status);',a);body=boot[a:b]
body=body.replace('const struct camss_a5_ipe_colour *chain,','const struct camss_a5_ipe_colour *chain,\n\t\t\t     const struct camss_a5_ipe_gamma *gamma,',1)
body=body.replace('struct camss_a5_ipe_colour configuration;','struct camss_a5_ipe_colour configuration;\n\tstruct camss_a5_ipe_gamma *gamma_copy = NULL;',1)
body=body.replace('u32 iq_bytes = chain ? CAMSS_A5_IPE_COLOUR_IQ_BYTES :','u32 iq_bytes = gamma ? CAMSS_A5_IPE_GAMMA_IQ_BYTES :\n\t\tchain ? CAMSS_A5_IPE_COLOUR_IQ_BYTES :',1)
body=body.replace('if (cc && chain)', 'if (cc && (chain || gamma))',1)
needle='\tif (cc) {\n\t\tcolour = *cc;';assert needle in body
body=body.replace(needle,'''\tif (gamma) {
		gamma_copy = kmemdup(gamma, sizeof(*gamma), GFP_KERNEL);
		if (!gamma_copy) {
			ret = -ENOMEM;
			goto done;
		}
		ret = camss_a5_ipe_gamma_check(gamma_copy);
		if (ret)
			goto done;
	}
'''+needle,1)
needle='\tif (chain)\n\t\tret = camss_a5_ipe_encode_colour_iq';assert needle in body
body=body.replace(needle,'''\tif (gamma)
		ret = camss_a5_ipe_encode_gamma_iq(a5->request.cpu + iq_offset, iq_bytes,
						 REQUEST_IOVA + iq_offset,
						 chain ? &configuration : NULL, gamma_copy);
	else if (chain)
		ret = camss_a5_ipe_encode_colour_iq''',1)
body=body.replace('\tif (chain) {\n\t\tput_unaligned_le32(', '\tif (gamma || chain) {\n\t\tput_unaligned_le32(',1)
needle='\tmutex_unlock(&a5->lock);';assert body.count(needle)==1;body=body.replace(needle,'\tkfree(gamma_copy);\n'+needle)
body=body.replace('run_colour_status(a5, session, job, NULL, NULL, result)','run_colour_status(a5, session, job, NULL, NULL, NULL, result)')
boot=boot[:a]+body+boot[b:]
boot=boot.replace('run_colour_status(a5, session, job, cc, NULL, result)','run_colour_status(a5, session, job, cc, NULL, NULL, result)').replace('run_colour_status(a5, session, job, NULL, colour, result)','run_colour_status(a5, session, job, NULL, colour, NULL, result)')
needle='EXPORT_SYMBOL_GPL(camss_a5_ipe_run_colour_chain_status);';assert needle in boot
boot=boot.replace(needle,needle+'''

int camss_a5_ipe_run_gamma_status(struct camss_a5 *a5,
				struct camss_a5_session *session,
				const struct camss_a5_ipe_job *job,
				const struct camss_a5_ipe_colour *colour,
				const struct camss_a5_ipe_gamma *gamma,
				enum camss_a5_ipe_result *result)
{
	return run_colour_status(a5, session, job, NULL, colour, gamma, result);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_run_gamma_status);''')
rows={'camss-icp-a5-colour.c':c,'camss-icp-a5-colour.h':h,'camss-icp-a5-ipe.h':header,'camss-icp-a5-boot.c':boot};patch=[]
for name,text in rows.items():
 old=(P/(name+'.before')).read_text();(P/(name+'.proposed')).write_text(text);patch.extend(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/'+name,tofile='b/drivers/media/platform/qcom/camss/'+name))
(HERE/'gamma-ownership.patch').write_text(''.join(patch))
(HERE/'proposal-validation.json').write_text(json.dumps(dict(stage=401,files=list(rows),gamma_iq_bytes=6016,iq_allocation_bytes=8192,gamma_cpu_copy_bytes=3072,new_coherent_allocations=0,new_api='camss_a5_ipe_run_gamma_status',old_layouts_unchanged=True,generic_program_tag_corrected_to20=True,source_and_phone_changed=False),indent=2)+'\n')
print('Prepared typed Gamma ownership and descriptor correction; no source/phone mutation.')
