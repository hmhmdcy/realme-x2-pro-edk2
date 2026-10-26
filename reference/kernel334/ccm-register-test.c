/* SPDX-License-Identifier: GPL-2.0-only */
/* Compile the actual driver body against mock MMIO and retained register types. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <linux/qcom-camss-config.h>
#include "titan170_ife-private.h"
typedef uint32_t u32;
typedef uint16_t u16;
#define BIT(n) (1u << (n))
#define GENMASK(h, l) ((~0u << (l)) & (~0u >> (31 - (h))))
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
struct device { int unused; };
struct vfe_device { void *base; };
static uint32_t memory[1024], before[1024];
static u32 readl_relaxed(const void *pointer)
{
	ptrdiff_t delta=(const char *)pointer-(const char *)memory;
	assert(delta>=0 && (size_t)delta<sizeof(memory) && delta%4==0);
	return memory[delta/4];
}
static void writel_relaxed(u32 value, void *pointer)
{
	ptrdiff_t delta=(char *)pointer-(char *)memory;
	assert(delta>=0 && (size_t)delta<sizeof(memory) && delta%4==0);
	memory[delta/4]=value;
}
#include "ccm-driver-body-private.c"

static void check(const uint16_t *fields, bool enabled)
{
	uint32_t expected[1024];memcpy(expected,before,sizeof(expected));
	IFE_IFE_0_VFE_MODULE_COLOR_EN en={.u32All=expected[regIFE_IFE_0_VFE_MODULE_COLOR_EN/4]};
	en.bitfields.COLOR_CORRECT_EN=enabled;expected[regIFE_IFE_0_VFE_MODULE_COLOR_EN/4]=en.u32All;
	for(unsigned i=0;i<9;i++) {
	 unsigned offset=regIFE_IFE_0_VFE_COLOR_CORRECT_COEFF_0/4+i;
	 IFE_IFE_0_VFE_COLOR_CORRECT_COEFF_0 word={.u32All=expected[offset]};
	 word.bitfields.CN=fields[i];word.bitfields.RIGHT_CN=fields[i];expected[offset]=word.u32All;
	}
	for(unsigned i=0;i<3;i++) {
	 unsigned offset=regIFE_IFE_0_VFE_COLOR_CORRECT_OFFSET_0/4+i;
	 IFE_IFE_0_VFE_COLOR_CORRECT_OFFSET_0 word={.u32All=expected[offset]};
	 word.bitfields.KN=fields[9+i];word.bitfields.RIGHT_KN=fields[9+i];expected[offset]=word.u32All;
	}
	IFE_IFE_0_VFE_COLOR_CORRECT_COEFF_Q q={.u32All=expected[regIFE_IFE_0_VFE_COLOR_CORRECT_COEFF_Q/4]};
	q.bitfields.QFACTOR=fields[12];q.bitfields.RIGHT_QFACTOR=fields[12];expected[regIFE_IFE_0_VFE_COLOR_CORRECT_COEFF_Q/4]=q.u32All;
	assert(!memcmp(memory,expected,sizeof(expected)));
}
int main(int argc,char **argv)
{
	assert(argc==2);FILE *input=fopen(argv[1],"rb");assert(input);
	struct vfe_device vfe={.base=memory};uint16_t fields[13];unsigned cases=0;
	while(fread(fields,sizeof(fields),1,input)==1) {
	 for(unsigned i=0;i<1024;i++)memory[i]=0xa5a55a5a^(i*0x12345u);
	 memcpy(before,memory,sizeof(memory));
	 struct camss_params_color_correct block={.header={CAMSS_PARAMS_COLOR_CORRECT,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(block)}};
	 for(unsigned i=0;i<3;i++){block.a[i]=fields[i*3];block.b[i]=fields[i*3+1];block.c[i]=fields[i*3+2];block.k[i]=fields[9+i];}block.qfactor=fields[12];
	 assert(!vfe_175_ccm_validate(NULL,&block.header));vfe_175_ccm_params(&vfe,&block.header);check(fields,true);cases++;
	 memcpy(before,memory,sizeof(memory));block.header.flags=0;vfe_175_ccm_params(&vfe,&block.header);check(fields,true);
	 for(unsigned bad=0;bad<6;bad++) {
	  struct camss_params_color_correct invalid=block;
	  switch(bad){case 0:invalid.header.flags=3;break;case 1:invalid.header.flags=4;break;case 2:invalid._pad[1]=1;break;case 3:invalid.a[1]=4096;break;case 4:invalid.k[0]=2048;break;case 5:invalid.qfactor=4;break;}
	  assert(vfe_175_ccm_validate(NULL,&invalid.header)==-EINVAL);
	 }
	}
	fclose(input);assert(cases);
	long page=sysconf(_SC_PAGESIZE);char *guard=mmap(NULL,page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);assert(guard!=MAP_FAILED);
	assert(!mprotect(guard+page,page,PROT_NONE));
	struct v4l2_isp_params_block_header *disable=(void *)(guard+page-sizeof(*disable));
	*disable=(struct v4l2_isp_params_block_header){CAMSS_PARAMS_COLOR_CORRECT,V4L2_ISP_PARAMS_FL_BLOCK_DISABLE,sizeof(*disable)};
	assert(!vfe_175_ccm_validate(NULL,disable));memcpy(before,memory,sizeof(memory));vfe_175_ccm_params(&vfe,disable);
	before[regIFE_IFE_0_VFE_MODULE_COLOR_EN/4]&=~IFE_IFE_0_VFE_MODULE_COLOR_EN_COLOR_CORRECT_EN_MASK;
	assert(!memcmp(before,memory,sizeof(memory)));munmap(guard,page*2);
	uint16_t unity[13]={128,0,0,0,128,0,0,0,128,0,0,0,0};memcpy(before,memory,sizeof(memory));vfe_175_ccm_init(&vfe);check(unity,false);
	memory[regIFE_IFE_0_VFE_MODULE_COLOR_EN/4]|=2;memcpy(before,memory,sizeof(memory));vfe_175_ccm_stop(&vfe);before[regIFE_IFE_0_VFE_MODULE_COLOR_EN/4]&=~2u;assert(!memcmp(before,memory,sizeof(memory)));
	printf("CCM_REGISTER_PASS cases=%u header_only_disable=1 reserved_bits=1 lifecycle=1\n",cases);return 0;
}
