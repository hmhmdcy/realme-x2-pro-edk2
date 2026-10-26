"""Prepare a temporary fixed-matrix adapter and native pixel client."""
from pathlib import Path
import difflib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
normal=(P/'camss-icp-a5-m2m.c.before').read_text()
code='''
#ifdef CAMSS_A5_TEST_COLOUR
/* Temporary offline test adapter only; absent from the normal build. */
static unsigned int test_cc_mode;
module_param(test_cc_mode, uint, 0600);
MODULE_PARM_DESC(test_cc_mode, "Temporary fixed matrix: 0 bypass, 1 identity, 2 zero, 3 half");

static int test_colour_run(struct camss_a5 *a5, struct camss_a5_session *session,
			   const struct camss_a5_ipe_job *job,
			   enum camss_a5_ipe_result *result)
{
	struct camss_a5_ipe_cc cc = {};
	u32 mode = READ_ONCE(test_cc_mode);

	if (!mode)
		return camss_a5_ipe_run_status(a5, session, job, result);
	if (mode > 3)
		return -EINVAL;
	if (mode != 2)
		cc.matrix[0] = cc.matrix[4] = cc.matrix[8] = mode == 1 ? 128 : 64;
	dev_info(a5->dev, "COLOUR_TEST mode=%u request=%u\\n", mode, job->request_id);
	return camss_a5_ipe_run_colour_status(a5, session, job, &cc, result);
}
#endif
'''
needle='#define IPE_IMAGE_MAX (64U * 1024U * 1024U)';assert normal.count(needle)==1
test=normal.replace(needle,needle+'\n'+code)
needle='ret = camss_a5_ipe_run_status(dev->a5, &ctx->session, &job, &result);';assert test.count(needle)==1
test=test.replace(needle,'''#ifdef CAMSS_A5_TEST_COLOUR
	ret = test_colour_run(dev->a5, &ctx->session, &job, &result);
#else
	'''+needle+'''
#endif''')
(P/'camss-icp-a5-m2m.c.normal').write_text(normal);(P/'camss-icp-a5-m2m.c.test').write_text(test)
(HERE/'temporary-colour-adapter.patch').write_text(''.join(difflib.unified_diff(normal.splitlines(True),test.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c',tofile='b/drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c')))
build=(HERE.parent/'kernel395/build-test-core.py').read_text().replace('stage=395','stage=397').replace('CAMSS_A5_TEST_DROP_FRAME_ACK','CAMSS_A5_TEST_COLOUR').replace('camss-icp-a5-boot.c','camss-icp-a5-m2m.c').replace("modules=[camss/'qcom-camss-icp-a5-core.ko']","modules=[camss/'qcom-camss-icp-a5-core.ko',camss/'camss-icp-a5-m2m.ko']").replace('temporary_ack_loss_core=True,source_restored_to_normal395=True','temporary_fixed_colour_adapter=True,source_restored_to_normal397=True')
build=build.replace('runtime_modules=set(modules)','''runtime_modules=set(modules)
modules += [v4l2/'v4l2-mem2mem.ko',v4l2/'v4l2-isp.ko']
modules += [vb2/(n+'.ko') for n in ['videobuf2-common','videobuf2-v4l2','videobuf2-memops','videobuf2-vmalloc','videobuf2-dma-sg']]''')
(HERE/'build-test-adapter.py').write_text(build)
print(json.dumps(dict(temporary_adapter_prepared=True,fixed_modes=4,no_fault_injection=True,production_adapter_unchanged=True)))
