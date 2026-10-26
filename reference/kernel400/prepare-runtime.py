"""Prepare a private fixed-mode conversion adapter; normal source is restored."""
from pathlib import Path
import difflib,json,math,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for n in ['parcel-validation.json','transfer-validation.json','firmware-parcel-validation.json','intree-build-validation.json']:assert json.loads((HERE.parent/'kernel399'/n).read_text())['passed']
state=json.loads((HERE.parent/'kernel399/source-state.json').read_text());state['stage']=400;(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
build=json.loads((HERE.parent/'kernel399/intree-build-validation.json').read_text());build.update(stage=400,reused_unchanged_normal399_core=True);(HERE/'intree-build-validation.json').write_text(json.dumps(build,indent=2)+'\n')
profiles=json.loads((P.parent/'kernel399/mode-profiles-private.json').read_text());profile=next(p for p in profiles['sunny_imx319'] if p['sensor_mode_index']==0 and p['usecase']=='Preview')
cst=profile['modules']['cst12_ipe']['reserve'];node=profile['modules']['cv12_ipe']['core'][0]
while 'children' in node:node=node['children'][0]
cv=node['data'];f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0];rnd=lambda x:math.floor(x+.5) if x>=0 else math.ceil(x-.5);clip=lambda x,a,b:min(max(x,a),b)
matrix=[clip(rnd(f32(v*1024)),-4096,4095) for v in cst['m_tab']]
coeffs=[clip(rnd(f32(cv[k]*256)),-2048,2047) for k in ['r_to_y','g_to_y','b_to_y','ap','am','bp','bm','cp','cm','dp','dm']]
yo=clip(rnd(cv['y_offset']),-1024,1023);offset=[clip(rnd(cv[k]),-1024,1023) for k in ['kcb','kcr']]
def array(values):return '{'+','.join(map(str,values))+'}'
fixture='''/* Private retained factory diagnostic fixture; no runtime-leaf claim. */
static const struct camss_a5_ipe_colour fixed_chain = {
 .modules = CAMSS_A5_IPE_COLOUR_CST | CAMSS_A5_IPE_COLOUR_CV,
 .cst = { .matrix = MATRIX, .subtract = SUBTRACT, .offset = OFFSET,
          .minimum = MINIMUM, .maximum = MAXIMUM },
 .cv = { .luma = LUMA, .y_offset = YOFFSET, .chroma = CHROMA, .offset = UV }
};
'''
fixture=fixture.replace('YOFFSET',str(yo))
for key,values in [('MATRIX',matrix),('SUBTRACT',cst['s_tab']),('OFFSET',cst['o_tab']),('MINIMUM',cst['c_x0_tab']),('MAXIMUM',cst['c_x1_tab']),('LUMA',coeffs[:3]),('CHROMA',coeffs[3:]),('UV',offset)]:fixture=fixture.replace(key,array(values))
(P/'test-chain-fixture.h').write_text(fixture)
(P/'fixture-private.json').write_text(json.dumps(dict(variant='sunny_imx319',sensor_mode=0,usecase='Preview',cst_root=profile['modules']['cst12_ipe']['uid'],cv_root=profile['modules']['cv12_ipe']['uid'],cv_leaf_selection='first retained leaf in selected mode, diagnostic only',cst=cst,cv=cv,quantized_cst_matrix=matrix,quantized_cv_luma=coeffs[:3],quantized_cv_chroma=coeffs[3:],quantized_cv_y_offset=yo,quantized_cv_cb_cr_offset=offset),indent=2)+'\n')
code='''
#ifdef CAMSS_A5_TEST_CHAIN
#include "test-chain-fixture.h"
static unsigned int test_chain_mode;
module_param(test_chain_mode, uint, 0600);
MODULE_PARM_DESC(test_chain_mode, "Temporary fixed conversion/CC modes 0..7");
static int test_chain_run(struct camss_a5 *a5, struct camss_a5_session *session,
			  const struct camss_a5_ipe_job *job,
			  enum camss_a5_ipe_result *result)
{
	struct camss_a5_ipe_colour colour = fixed_chain;
	u32 mode = READ_ONCE(test_chain_mode);

	if (!mode)
		return camss_a5_ipe_run_status(a5, session, job, result);
	if (mode > 7)
		return -EINVAL;
	if (mode >= 2) {
		colour.modules |= CAMSS_A5_IPE_COLOUR_CC;
		if (mode != 3)
			colour.cc.matrix[0] = colour.cc.matrix[4] =
				colour.cc.matrix[8] = mode == 4 ? 64 : 128;
	}
	if (mode == 5) {
		colour.cc.matrix[0] = colour.cc.matrix[8] = 0;
		colour.cc.matrix[2] = colour.cc.matrix[6] = 128;
	}
	if (mode >= 6) {
		colour.cc.offset[0] = mode == 6 ? -64 : 64;
		colour.cc.offset[1] = mode == 6 ? 32 : -32;
		colour.cc.offset[2] = mode == 6 ? 96 : -96;
	}
	dev_info(a5->dev, "CHAIN_TEST mode=%u request=%u\\n", mode, job->request_id);
	return camss_a5_ipe_run_colour_chain_status(a5, session, job, &colour, result);
}
#endif
'''
normal=(P/'camss-icp-a5-m2m.c.before').read_text();needle='#define IPE_IMAGE_MAX (64U * 1024U * 1024U)';assert normal.count(needle)==1;test=normal.replace(needle,needle+'\n'+code)
needle='ret = camss_a5_ipe_run_status(dev->a5, &ctx->session, &job, &result);';assert test.count(needle)==1
test=test.replace(needle,'#ifdef CAMSS_A5_TEST_CHAIN\n\tret = test_chain_run(dev->a5, &ctx->session, &job, &result);\n#else\n\t'+needle+'\n#endif')
(P/'camss-icp-a5-m2m.c.normal').write_text(normal);(P/'camss-icp-a5-m2m.c.test').write_text(test)
(HERE/'temporary-chain-adapter.patch').write_text(''.join(difflib.unified_diff(normal.splitlines(True),test.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c',tofile='b/drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c')))
build=(HERE.parent/'kernel397/build-test-adapter.py').read_text().replace('stage=397','stage=400').replace('CAMSS_A5_TEST_COLOUR','CAMSS_A5_TEST_CHAIN').replace('temporary_fixed_colour_adapter=True,source_restored_to_normal397=True','temporary_fixed_chain_adapter=True,source_restored_to_normal399=True')
build=build.replace("assert path.read_bytes()==(P/'camss-icp-a5-m2m.c.normal').read_bytes()","assert path.read_bytes()==(P/'camss-icp-a5-m2m.c.normal').read_bytes()\nfixture=path.parent/'test-chain-fixture.h';assert not fixture.exists()")
build=build.replace(" path.write_bytes((P/'camss-icp-a5-m2m.c.test').read_bytes())"," fixture.write_bytes((P/'test-chain-fixture.h').read_bytes())\n path.write_bytes((P/'camss-icp-a5-m2m.c.test').read_bytes())")
build=build.replace(" path.write_bytes((P/'camss-icp-a5-m2m.c.normal').read_bytes())"," path.write_bytes((P/'camss-icp-a5-m2m.c.normal').read_bytes())\n if fixture.exists():fixture.unlink()")
(HERE/'build-test-adapter.py').write_text(build)
print(json.dumps(dict(stage=400,fixed_modes=8,private_factory_fixture=True,no_fault_injection=True,source_not_yet_changed=True,passed=True)))
