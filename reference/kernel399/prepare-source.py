"""Prepare typed CST/CC/CV programs within the existing request page."""
from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'native-leaf-validation.json').read_text())['passed']
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()=='8b1e8903a550ffc20a2d8f1de574c37f2260fff3'
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
base=source/'drivers/media/platform/qcom/camss'
for name in ['camss-icp-a5-colour.c','camss-icp-a5-colour.h','camss-icp-a5-ipe.h','camss-icp-a5-ipe.c','camss-icp-a5-boot.c']:(P/(name+'.before')).write_bytes((base/name).read_bytes())
h=(P/'camss-icp-a5-colour.h.before').read_text();at=h.index('\n#endif')
h=h[:at]+'''
/* Quantized target IPE component transform; matrix Q10, signed13.
 * Subtract is signed11; additive offsets and clamps are unsigned10.
 */
struct camss_a5_ipe_cst {
	s16 matrix[9];
	s16 subtract[3];
	u16 offset[3];
	u16 minimum[3];
	u16 maximum[3];
};

/* Target native CV leaf order, verified through its deserializer and Execute.
 * Coefficients are signed12/Q8; offsets have signed11 numerical range.
 * Chroma pairs are ap/am, bp/bm, cp/cm, dp/dm; cb/cr offsets follow packet order.
 */
struct camss_a5_ipe_cv {
	s16 luma[3];
	s16 y_offset;
	s16 chroma[8];
	s16 offset[2];
};

#define CAMSS_A5_IPE_COLOUR_CST 1U
#define CAMSS_A5_IPE_COLOUR_CC 2U
#define CAMSS_A5_IPE_COLOUR_CV 4U
#define CAMSS_A5_IPE_COLOUR_MODULES 7U

struct camss_a5_ipe_colour {
	u32 modules;
	struct camss_a5_ipe_cst cst;
	struct camss_a5_ipe_cc cc;
	struct camss_a5_ipe_cv cv;
};

#define CAMSS_A5_IPE_COLOUR_ARRAY_OFFSET 2592U
#define CAMSS_A5_IPE_COLOUR_PRE_OFFSET 32U
#define CAMSS_A5_IPE_COLOUR_POST_OFFSET 64U
#define CAMSS_A5_IPE_CST_PACKET_OFFSET 2720U
#define CAMSS_A5_IPE_COLOUR_CC_PACKET_OFFSET 2776U
#define CAMSS_A5_IPE_CV_PACKET_OFFSET 2820U
#define CAMSS_A5_IPE_COLOUR_IQ_BYTES 2860U

int camss_a5_ipe_colour_check(const struct camss_a5_ipe_colour *colour);
int camss_a5_ipe_encode_colour_iq(void *destination, u32 bytes, u32 iq_iova,
				const struct camss_a5_ipe_colour *colour);
'''+h[at:]
c=(P/'camss-icp-a5-colour.c.before').read_text()+'\n'+(HERE/'conversion-codec-tail.c').read_text()
header=(P/'camss-icp-a5-ipe.h.before').read_text();needle='int camss_a5_ipe_run(struct camss_a5 *a5, struct camss_a5_session *session,';at=header.index(needle)
header=header[:at]+'''/* Optional typed pre/post conversion and CCM; NULL retains the old bypass.
 * Enabled modules are copied/validated before allocation or firmware MAP.
 */
int camss_a5_ipe_run_colour_chain_status(struct camss_a5 *a5,
				       struct camss_a5_session *session,
				       const struct camss_a5_ipe_job *job,
				       const struct camss_a5_ipe_colour *colour,
				       enum camss_a5_ipe_result *result);
'''+header[at:]
boot=(P/'camss-icp-a5-boot.c.before').read_text();a=boot.index('static int run_colour_status(');b=boot.index('EXPORT_SYMBOL_GPL(camss_a5_ipe_run_status);',a);body=boot[a:b]
body=body.replace('const struct camss_a5_ipe_cc *cc,\n','const struct camss_a5_ipe_cc *cc,\n\t\t\t     const struct camss_a5_ipe_colour *chain,\n',1)
body=body.replace('struct camss_a5_ipe_cc colour;','struct camss_a5_ipe_cc colour;\n\tstruct camss_a5_ipe_colour configuration;')
body=body.replace('u32 iq_bytes = cc ? CAMSS_A5_IPE_CC_IQ_BYTES : CAMSS_A5_IPE_IQ_BYTES;','u32 iq_bytes = chain ? CAMSS_A5_IPE_COLOUR_IQ_BYTES :\n\t\tcc ? CAMSS_A5_IPE_CC_IQ_BYTES : CAMSS_A5_IPE_IQ_BYTES;')
body=body.replace('\tlocal_ready = true;','''	local_ready = true;
	if (cc && chain) {
		ret = -EINVAL;
		goto done;
	}
	if (chain) {
		configuration = *chain;
		ret = camss_a5_ipe_colour_check(&configuration);
		if (ret)
			goto done;
	}''')
needle='\tif (cc)\n\t\tret = camss_a5_ipe_encode_cc_iq'
assert needle in body
body=body.replace(needle,'''\tif (chain)
		ret = camss_a5_ipe_encode_colour_iq(a5->request.cpu + iq_offset, iq_bytes,
						  REQUEST_IOVA + iq_offset, &configuration);
	else if (cc)
		ret = camss_a5_ipe_encode_cc_iq''',1)
needle='\tif (cc) {\n\t\tput_unaligned_le32(REQUEST_IOVA + iq_offset + CAMSS_A5_IPE_CC_ARRAY_OFFSET,'
assert needle in body
body=body.replace(needle,'''\tif (chain) {
		put_unaligned_le32(REQUEST_IOVA + iq_offset + CAMSS_A5_IPE_COLOUR_ARRAY_OFFSET,
				   a5->request.cpu + 40);
		put_unaligned_le32(CAMSS_A5_IPE_COLOUR_PRE_OFFSET, a5->request.cpu + 44);
		put_unaligned_le32(CAMSS_A5_IPE_COLOUR_POST_OFFSET, a5->request.cpu + 48);
	} else if (cc) {
		put_unaligned_le32(REQUEST_IOVA + iq_offset + CAMSS_A5_IPE_CC_ARRAY_OFFSET,''',1)
body=body.replace('run_colour_status(a5, session, job, NULL, result)','run_colour_status(a5, session, job, NULL, NULL, result)')
boot=boot[:a]+body+boot[b:];boot=boot.replace('run_colour_status(a5, session, job, cc, result)','run_colour_status(a5, session, job, cc, NULL, result)')
needle='EXPORT_SYMBOL_GPL(camss_a5_ipe_run_colour_status);'
boot=boot.replace(needle,needle+'''

int camss_a5_ipe_run_colour_chain_status(struct camss_a5 *a5,
				       struct camss_a5_session *session,
				       const struct camss_a5_ipe_job *job,
				       const struct camss_a5_ipe_colour *colour,
				       enum camss_a5_ipe_result *result)
{
	return run_colour_status(a5, session, job, NULL, colour, result);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_run_colour_chain_status);''')
rows={'camss-icp-a5-colour.c':c,'camss-icp-a5-colour.h':h,'camss-icp-a5-ipe.h':header,'camss-icp-a5-boot.c':boot};patch=[]
for name,text in rows.items():
 old=(P/(name+'.before')).read_text();(P/(name+'.proposed')).write_text(text);patch.extend(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/'+name,tofile='b/drivers/media/platform/qcom/camss/'+name))
(HERE/'conversion-chain.patch').write_text(''.join(patch))
(HERE/'proposal-validation.json').write_text(json.dumps(dict(stage=399,files=list(rows),new_api='camss_a5_ipe_run_colour_chain_status',legacy_apis_and_old_job_layouts_retained=True,enabled_modules_copied_and_validated_before_allocation=True,iq_bytes=2860,existing_iq_page_bytes=4096,new_independent_dma_allocations=0,source_and_phone_changed=False),indent=2)+'\n')
print('Prepared typed conversion chain candidate; source and phone unchanged.')
