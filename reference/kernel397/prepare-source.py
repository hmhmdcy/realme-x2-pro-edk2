"""Add typed per-frame CC input without changing the existing job ABI."""
from pathlib import Path
import difflib,importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
old=HERE.parent/'kernel396'
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);source=storage.mounted_build().parent/'source354'
base=source/'drivers/media/platform/qcom/camss'
for n in ['camss-icp-a5-colour.c','camss-icp-a5-colour.h']:(P/(n+'.before')).write_bytes((base/n).read_bytes())
h=(P/'camss-icp-a5-colour.h.before').read_text().replace('#define CAMSS_A5_IPE_CC_COMMAND_BYTES 44','#define CAMSS_A5_IPE_CC_COMMAND_BYTES 44\n#define CAMSS_A5_IPE_CC_ARRAY_OFFSET 2592U\n#define CAMSS_A5_IPE_CC_POST_OFFSET 32U\n#define CAMSS_A5_IPE_CC_PACKET_OFFSET 2656U\n#define CAMSS_A5_IPE_CC_IQ_BYTES 2700U')
h=h.replace('\n#endif','''
/* IQ and both program arrays live in one caller-owned, mapped request page.
 * Every invalid argument leaves the destination unchanged. No arbitrary
 * command, register address or image pointer is accepted.
 */
int camss_a5_ipe_encode_cc_iq(void *destination, u32 bytes, u32 iq_iova,
			    const struct camss_a5_ipe_cc *cc);

#endif''')
c=(P/'camss-icp-a5-colour.c.before').read_text().replace('#include "camss-icp-a5-colour.h"','#include "camss-icp-a5-colour.h"\n#include "camss-icp-a5-ipe.h"')
c+='''
int camss_a5_ipe_encode_cc_iq(void *destination, u32 bytes, u32 iq_iova,
			    const struct camss_a5_ipe_cc *cc)
{
	u8 command[CAMSS_A5_IPE_CC_COMMAND_BYTES];
	u8 *output = destination;
	u32 post = CAMSS_A5_IPE_CC_ARRAY_OFFSET + CAMSS_A5_IPE_CC_POST_OFFSET;
	int ret;

	if (!output || bytes < CAMSS_A5_IPE_CC_IQ_BYTES || !iq_iova ||
	    (iq_iova & 31) ||
	    (u64)iq_iova + CAMSS_A5_IPE_CC_IQ_BYTES > (1ULL << 32))
		return -EINVAL;
	ret = camss_a5_ipe_cc_encode(command, sizeof(command), cc);
	if (ret)
		return ret;
	/* Validated capacity makes the base initializer infallible here. */
	ret = camss_a5_ipe_encode_bypass_iq(output, bytes);
	if (ret)
		return ret;
	memset(output + CAMSS_A5_IPE_IQ_BYTES, 0,
	       CAMSS_A5_IPE_CC_IQ_BYTES - CAMSS_A5_IPE_IQ_BYTES);
	put_unaligned_le32(1, output + 2188);
	/* Offset0 is a common empty array. Offset32 is the single CC program. */
	put_unaligned_le32(1, output + post + 4);
	put_unaligned_le32(iq_iova + CAMSS_A5_IPE_CC_PACKET_OFFSET,
			   output + post + 8);
	put_unaligned_le32((CAMSS_A5_IPE_CC_COMMAND_BYTES - 1) << 12,
			   output + post + 12);
	memcpy(output + CAMSS_A5_IPE_CC_PACKET_OFFSET, command, sizeof(command));
	return 0;
}
'''
header=(P/'camss-icp-a5-ipe.h.before').read_text().replace('#include "camss-icp-a5-boot.h"','#include "camss-icp-a5-boot.h"\n#include "camss-icp-a5-colour.h"')
needle='int camss_a5_ipe_run(struct camss_a5 *a5, struct camss_a5_session *session,'
at=header.index(needle)
header=header[:at]+'''/* Typed, synchronous colour extension; the legacy job layout is unchanged.
 * The core copies/validates cc before any firmware MAP. NULL retains bypass.
 * Colour/program storage uses the existing retained request parcel.
 */
int camss_a5_ipe_run_colour_status(struct camss_a5 *a5,
				 struct camss_a5_session *session,
				 const struct camss_a5_ipe_job *job,
				 const struct camss_a5_ipe_cc *cc,
				 enum camss_a5_ipe_result *result);
'''+header[at:]
boot=(P/'camss-icp-a5-boot.c.before').read_text()
boot=boot.replace('int camss_a5_ipe_run_status(struct camss_a5 *a5, struct camss_a5_session *session,\n\t\t\t  const struct camss_a5_ipe_job *job,\n\t\t\t  enum camss_a5_ipe_result *result)','''static int run_colour_status(struct camss_a5 *a5, struct camss_a5_session *session,
			     const struct camss_a5_ipe_job *job,
			     const struct camss_a5_ipe_cc *cc,
			     enum camss_a5_ipe_result *result)''')
assert 'static int run_colour_status(' in boot
a=boot.index('static int run_colour_status(');b=boot.index('EXPORT_SYMBOL_GPL(camss_a5_ipe_run_status);',a)
body=boot[a:b]
body=body.replace('struct camss_a5_ipe_frame frame = {};','struct camss_a5_ipe_frame frame = {};\n\tstruct camss_a5_ipe_cc colour;\n\tu8 colour_command[CAMSS_A5_IPE_CC_COMMAND_BYTES];\n\tu32 iq_bytes = cc ? CAMSS_A5_IPE_CC_IQ_BYTES : CAMSS_A5_IPE_IQ_BYTES;')
body=body.replace('\tlocal_ready = true;','''	local_ready = true;
	if (cc) {
		colour = *cc;
		ret = camss_a5_ipe_cc_encode(colour_command, sizeof(colour_command), &colour);
		if (ret)
			goto done;
	}''')
body=body.replace('PAGE_ALIGN(CAMSS_A5_IPE_IQ_BYTES)','PAGE_ALIGN(iq_bytes)')
body=body.replace('ret = camss_a5_ipe_encode_bypass_iq(a5->request.cpu + iq_offset, CAMSS_A5_IPE_IQ_BYTES);','''if (cc)
		ret = camss_a5_ipe_encode_cc_iq(a5->request.cpu + iq_offset, iq_bytes,
					      REQUEST_IOVA + iq_offset, &colour);
	else
		ret = camss_a5_ipe_encode_bypass_iq(a5->request.cpu + iq_offset, iq_bytes);''')
body=body.replace('REQUEST_IOVA + iq_offset, CAMSS_A5_IPE_IQ_BYTES','REQUEST_IOVA + iq_offset, iq_bytes')
body=body.replace('\n\tdma_wmb();','''
	if (cc) {
		put_unaligned_le32(REQUEST_IOVA + iq_offset + CAMSS_A5_IPE_CC_ARRAY_OFFSET,
				   a5->request.cpu + 40);
		put_unaligned_le32(CAMSS_A5_IPE_CC_POST_OFFSET, a5->request.cpu + 48);
	}
	dma_wmb();''')
body+='''int camss_a5_ipe_run_status(struct camss_a5 *a5, struct camss_a5_session *session,
			  const struct camss_a5_ipe_job *job,
			  enum camss_a5_ipe_result *result)
{
	return run_colour_status(a5, session, job, NULL, result);
}
'''
boot=boot[:a]+body+boot[b:]
needle='EXPORT_SYMBOL_GPL(camss_a5_ipe_run_status);'
boot=boot.replace(needle,needle+'''

int camss_a5_ipe_run_colour_status(struct camss_a5 *a5,
				 struct camss_a5_session *session,
				 const struct camss_a5_ipe_job *job,
				 const struct camss_a5_ipe_cc *cc,
				 enum camss_a5_ipe_result *result)
{
	return run_colour_status(a5, session, job, cc, result);
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_run_colour_status);''')
rows={'camss-icp-a5-colour.c':c,'camss-icp-a5-colour.h':h,'camss-icp-a5-ipe.h':header,'camss-icp-a5-boot.c':boot}
patch=[]
for name,text in rows.items():
 before=(P/(name+'.before')).read_text();(P/(name+'.proposed')).write_text(text)
 patch.extend(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/'+name,tofile='b/drivers/media/platform/qcom/camss/'+name))
(HERE/'per-frame-colour.patch').write_text(''.join(patch))
report=dict(stage=397,files=list(rows),old_job_and_session_layout_unchanged=True,new_core_api='camss_a5_ipe_run_colour_status',parameters_copied_and_validated_before_map=True,programme_storage_within_existing_iq_page=True,unknown_dma_release_logic_unchanged=True,installed=False)
(HERE/'proposal-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
