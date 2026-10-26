#ifdef CAMSS_A5_TEST_LTM
#include "test-chain-fixture.h"
static unsigned int test_ltm_mode;
module_param(test_ltm_mode, uint, 0600);
MODULE_PARM_DESC(test_ltm_mode, "Temporary fixed LTM diagnostic modes 0..12");
static int test_ltm_run(struct camss_a5 *a5, struct camss_a5_session *session,
			const struct camss_a5_ipe_job *job,
			enum camss_a5_ipe_result *result)
{
	struct camss_a5_ipe_colour colour = fixed_chain;
	struct camss_a5_ipe_ltm *ltm;
	struct camss_a5_ipe_gamma *gamma = NULL;
	u32 mode = READ_ONCE(test_ltm_mode), bank, i;
	int ret;

	if (!mode)
		return camss_a5_ipe_run_status(a5, session, job, result);
	if (mode > 12)
		return -EINVAL;
	colour.modules |= CAMSS_A5_IPE_COLOUR_CC;
	colour.cc.matrix[0] = colour.cc.matrix[4] = colour.cc.matrix[8] = 128;
	dev_info(a5->dev, "LTM_TEST mode=%u request=%u width=%u\n",
		 mode, job->request_id, session->io.input.width);
	if (mode == 1)
		return camss_a5_ipe_run_colour_chain_status(a5, session, job, &colour, result);
	ltm = kzalloc(sizeof(*ltm), GFP_KERNEL);
	if (!ltm)
		return -ENOMEM;
	ltm->iq.rgb2y[0] = 19;
	ltm->iq.rgb2y[1] = 38;
	ltm->iq.rgb2y[2] = 7;
	ltm->iq.y_ratio_max = 1023;
	ltm->iq.image_processing = mode != 2;
	ltm->iq.mask_filter = mode == 4 || mode >= 10;
	ltm->iq.data_collection = mode == 10;
	ltm->iq.local_adaptation = mode == 5 || mode == 6 || mode == 9;
	ltm->iq.reverse_gamma = mode == 7 || mode == 8;
	for (i = 0; i < 12; i++)
		ltm->weight[i] = 0x0101;
	for (bank = 0; bank < 2; bank++)
		for (i = 0; i < 64; i++)
			ltm->la[bank][i].base = mode == 6 ? 2048 : mode == 9 ? 1024 : 0;
	if (mode == 8)
		for (bank = 0; bank < 5; bank++)
			for (i = 0; i < 64; i++) {
				ltm->reverse_gamma[bank][i].base = 256 * i;
				ltm->reverse_gamma[bank][i].delta = i == 63 ? 255 : 256;
			}
	if (mode >= 11) {
		gamma = kzalloc(sizeof(*gamma), GFP_KERNEL);
		if (!gamma) {
			ret = -ENOMEM;
			goto done;
		}
		if (mode == 11)
			for (bank = 0; bank < 3; bank++)
				for (i = 0; i < 256; i++) {
					gamma->base[bank][i] = 4 * i;
					gamma->delta[bank][i] = i == 255 ? 3 : 4;
				}
	}
	ret = camss_a5_ipe_run_ltm_status(a5, session, job, &colour, gamma, ltm, result);
done:
	kfree(gamma);
	kfree(ltm);
	return ret;
}
#endif
