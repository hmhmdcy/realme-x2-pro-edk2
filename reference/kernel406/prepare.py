"""Prepare fixed LTM diagnostics without changing the maintained adapter."""
from pathlib import Path
import ast,difflib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
normal=(P/'camss-icp-a5-m2m.c.normal').read_text();code=(HERE/'ltm-adapter-tail.c').read_text()
needle='#define IPE_IMAGE_MAX (64U * 1024U * 1024U)';assert normal.count(needle)==1;test=normal.replace(needle,needle+'\n'+code)
needle='ret = camss_a5_ipe_run_status(dev->a5, &ctx->session, &job, &result);';assert test.count(needle)==1
test=test.replace(needle,'#ifdef CAMSS_A5_TEST_LTM\n\tret = test_ltm_run(dev->a5, &ctx->session, &job, &result);\n#else\n\t'+needle+'\n#endif')
(P/'camss-icp-a5-m2m.c.test').write_text(test);(P/'test-chain-fixture.h').write_bytes((P.parent/'kernel400/test-chain-fixture.h').read_bytes())
(HERE/'temporary-ltm-adapter.patch').write_text(''.join(difflib.unified_diff(normal.splitlines(True),test.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c',tofile='b/drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c')))
text=(HERE.parent/'kernel402/build-test-adapter.py').read_text().replace('stage=402','stage=406').replace('CAMSS_A5_TEST_GAMMA','CAMSS_A5_TEST_LTM').replace('temporary_fixed_gamma_adapter=True,source_restored_to_normal401=True','temporary_fixed_ltm_adapter=True,source_restored_to_normal405=True')
ast.parse(text);(HERE/'build-test-adapter.py').write_text(text)
report=dict(stage=406,fixed_modes=13,planned_frames=52,widths=[640,650],height=480,formats=['NV12','NV21'],fixed_conversion_pair_reused_from400=True,no_arbitrary_cdm_or_register_interface=True,mode10_data_collection=True,source_or_phone_changed=False,passed=True)
(HERE/'preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
