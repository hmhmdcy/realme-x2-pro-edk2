/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <linux/errno.h>
#include "camss-icp-a5-colour.h"

int camss_a5_ipe_encode_bypass_iq(void *p, u32 bytes)
{ (void)p; (void)bytes; return 0; } /* Encoders are not exercised here. */

static unsigned cases;
static void check(struct qcom_ipe_a5_frame_params *p, int wanted)
{
	struct qcom_ipe_a5_frame_params before = *p;
	assert(camss_a5_ipe_frame_params_check(p) == wanted);
	assert(!memcmp(&before, p, sizeof(before)));
	cases++;
}

int main(void)
{
	struct qcom_ipe_a5_frame_params p = {};
	assert(camss_a5_ipe_frame_params_check(NULL) == -EINVAL);
	cases++;
	check(&p, 0);
	p.size = sizeof(p); check(&p, -EINVAL);
	p.version = 1; check(&p, 0);
	p.version = 2; check(&p, -EINVAL); p.version = 1;
	p.size--; check(&p, -EINVAL); p.size++;
	p.flags = 4; check(&p, -EINVAL); p.flags = 3;
	for (unsigned i=0;i<5;i++) {
		p.reserved[i]=1; check(&p,-EINVAL); p.reserved[i]=0;
	}
	p.colour.padding=1; check(&p,-EINVAL); p.colour.padding=0;
	p.colour.modules=8; check(&p,-EINVAL); p.colour.modules=7;
	check(&p,0);
	p.colour.cc.shift=4; check(&p,-EINVAL); p.colour.cc.shift=0;
	p.colour.cc.matrix[8]=2048; check(&p,-ERANGE); p.colour.cc.matrix[8]=2047;
	p.colour.cst.minimum[0]=1; check(&p,-ERANGE); p.colour.cst.minimum[0]=0;
	p.colour.cv.offset[1]=1024; check(&p,-ERANGE); p.colour.cv.offset[1]=0;
	p.gamma.base[2][255]=1024; check(&p,-ERANGE); p.gamma.base[2][255]=1023;
	p.gamma.delta[0][1]=-513; check(&p,-ERANGE); p.gamma.delta[0][1]=-512;
	p.ltm.iq.image_processing=2; check(&p,-ERANGE); p.ltm.iq.image_processing=1;
	p.ltm.iq.mask_kernel[5]=4; check(&p,-ERANGE); p.ltm.iq.mask_kernel[5]=3;
	p.ltm.la[1][63].base=4096; check(&p,-ERANGE); p.ltm.la[1][63].base=4095;
	p.ltm.scale[63].delta=2048; check(&p,-ERANGE); p.ltm.scale[63].delta=2047;
	p.ltm.reverse_gamma[4][63].base=16384; check(&p,-ERANGE); p.ltm.reverse_gamma[4][63].base=16383;
	check(&p,0);
	p.flags=0; p.gamma.base[0][0]=1024; check(&p,-ERANGE);
	printf("{\"cases\":%u,\"invalid_payload_unchanged\":true,\"inactive_tables_validated\":true,\"passed\":true}\n",cases);
	return 0;
}
