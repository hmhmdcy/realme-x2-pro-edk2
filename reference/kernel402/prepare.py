"""Prepare fixed Gamma diagnostics using the existing native V4L2 transaction."""
from pathlib import Path
import ast,difflib,importlib.util,json,subprocess,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;old=HERE.parent/'kernel400'
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';state=json.loads((HERE.parent/'kernel401/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
state.update(stage=402,maintained_source_stage=401,source_unchanged_from401=True,temporary_adapter_source_restored=False);(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
build=json.loads((HERE.parent/'kernel401/intree-build-validation.json').read_text());build.update(stage=402,reused_unchanged_normal401_core=True);(HERE/'intree-build-validation.json').write_text(json.dumps(build,indent=2)+'\n')
normal=(source/'drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c').read_text();(P/'camss-icp-a5-m2m.c.normal').write_text(normal)
# Reuse the unchanged private conversion pair already exercised physically400.
fixture=(P.parent/'kernel400/test-chain-fixture.h').read_text()
# Factory first retained curve is deliberately diagnostic, not runtime interpolation.
raw=(P.parent/'kernel401/gamma-lut-oracle-private.bin').read_bytes();assert len(raw)==97*1024
words=struct.unpack('<256I',raw[:1024]);base=[v&1023 for v in words];delta=[((v>>10)&1023)-1024 if v&(1<<19) else (v>>10)&1023 for v in words]
fixture+='\nstatic const u16 factory_base[256] = {'+','.join(map(str,base))+'};\nstatic const s16 factory_delta[256] = {'+','.join(map(str,delta))+'};\n'
(P/'test-chain-fixture.h').write_text(fixture)
code=r'''
#ifdef CAMSS_A5_TEST_GAMMA
#include "test-chain-fixture.h"
static unsigned int test_gamma_mode;
module_param(test_gamma_mode, uint, 0600);
MODULE_PARM_DESC(test_gamma_mode, "Temporary fixed Gamma modes 0..9");
static int test_gamma_run(struct camss_a5 *a5, struct camss_a5_session *session,
			  const struct camss_a5_ipe_job *job,
			  enum camss_a5_ipe_result *result)
{
	struct camss_a5_ipe_colour colour = fixed_chain;
	struct camss_a5_ipe_gamma *gamma;
	u32 mode = READ_ONCE(test_gamma_mode), bank, i;
	int ret;

	if (!mode)
		return camss_a5_ipe_run_status(a5, session, job, result);
	if (mode > 9)
		return -EINVAL;
	colour.modules |= CAMSS_A5_IPE_COLOUR_CC;
	colour.cc.matrix[0] = colour.cc.matrix[4] = colour.cc.matrix[8] = 128;
	dev_info(a5->dev, "GAMMA_TEST mode=%u request=%u\n", mode, job->request_id);
	if (mode == 1)
		return camss_a5_ipe_run_colour_chain_status(a5, session, job, &colour, result);
	gamma = kzalloc(sizeof(*gamma), GFP_KERNEL);
	if (!gamma)
		return -ENOMEM;
	for (bank = 0; bank < 3; bank++) {
		for (i = 0; i < 256; i++) {
			u32 base = 4 * i, delta = i == 255 ? 3 : 4;

			if (mode == 3 || (mode >= 5 && mode <= 7 && bank != mode - 5))
				base = delta = 0;
			else if (mode == 4) {
				base = 2 * i;
				delta = 2;
			} else if (mode == 8) {
				base = factory_base[i];
				delta = factory_delta[i];
			} else if (mode == 9) {
				base = 512;
				delta = 0;
			}
			gamma->base[bank][i] = base;
			gamma->delta[bank][i] = delta;
		}
	}
	ret = camss_a5_ipe_run_gamma_status(a5, session, job, &colour, gamma, result);
	kfree(gamma);
	return ret;
}
#endif
'''
needle='#define IPE_IMAGE_MAX (64U * 1024U * 1024U)';assert normal.count(needle)==1;test=normal.replace(needle,needle+'\n'+code)
needle='ret = camss_a5_ipe_run_status(dev->a5, &ctx->session, &job, &result);';assert test.count(needle)==1
test=test.replace(needle,'#ifdef CAMSS_A5_TEST_GAMMA\n\tret = test_gamma_run(dev->a5, &ctx->session, &job, &result);\n#else\n\t'+needle+'\n#endif')
(P/'camss-icp-a5-m2m.c.test').write_text(test)
(HERE/'temporary-gamma-adapter.patch').write_text(''.join(difflib.unified_diff(normal.splitlines(True),test.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c',tofile='b/drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c')))
text=(old/'build-test-adapter.py').read_text().replace('stage=400','stage=402').replace('CAMSS_A5_TEST_CHAIN','CAMSS_A5_TEST_GAMMA').replace('temporary_fixed_chain_adapter=True,source_restored_to_normal399=True','temporary_fixed_gamma_adapter=True,source_restored_to_normal401=True')
(HERE/'build-test-adapter.py').write_text(text)
text=(old/'inspect-current.py').read_text().replace('de94e65e7ab4ae2ec23ee1665f981d0aeb7395e7',state['commit']).replace("['test_cc_mode','test_chain_mode']","['test_cc_mode','test_chain_mode','test_gamma_mode']")
(HERE/'inspect-current.py').write_text(text)
tail=(old/'chain-client-tail.c').read_text().replace('set_chain_mode','set_gamma_mode').replace('test_chain_mode','test_gamma_mode').replace('mode<8','mode<10').replace('mode==1)memcpy','mode==1)memcpy').replace('if(mode==2)assert(!pairdiff);','/* Identity quantization is analyzed on the host; no assumed exact equality. */').replace('+16','+20').replace('fixed-conversion-chain','fixed-gamma-chain').replace('frames\\\":16','frames\\\":20')
(HERE/'gamma-client-tail.c').write_text(tail)
text=(old/'build-client.py').read_text().replace('chain-client-tail.c','gamma-client-tail.c').replace('chain-client.c','gamma-client.c').replace('stage=400','stage=402').replace('fixed_modes=8','fixed_modes=10').replace('frames=16','frames=20').replace('pair_and_identity_byte_equality_checked=True','identity_gamma_comparison_recorded=True')
(HERE/'build-client.py').write_text(text)
text=(old/'runtime-worker-body.py').read_text().replace('test_chain_mode','test_gamma_mode').replace('len(rows)==17','len(rows)==21').replace('rows[:16]','rows[:20]').replace('range(8)','range(10)').replace("==16","==20")
assert "direct_completed']==20" in text
(HERE/'runtime-worker-body.py').write_text(text)
for name in ['stage-runtime.py','runtime.py']:
 text=(old/name).read_text().replace('stage=400','stage=402').replace("'stage':400","'stage':402").replace('k400-chain-r1','k402-gamma-r1').replace('test_chain_mode','test_gamma_mode')
 if name=='stage-runtime.py':
  start=text.index("runtime=(HERE.parent/'kernel397/runtime.py')");text=text[:start]+"print(q.stdout.decode())\n"
 ast.parse(text);(HERE/name).write_text(text)
report=dict(stage=402,fixed_modes=10,frames=20,formats=['NV12','NV21'],conversion_pair_unchanged_from400=True,mode8_first_retained_original_lut_diagnostic_only=True,no_fault_injection=True,source_not_changed=True,passed=True)
(HERE/'preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
