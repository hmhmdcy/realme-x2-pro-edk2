/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual Gamma/LSC driver bodies, with shared-DMI and inactive-bank checks. */
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
#include <linux/videodev2.h>
#include <linux/v4l2-mediabus.h>
#include <linux/qcom-camss-config.h>

typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t u8;
#define BIT(n) (1u << (n))
#define GENMASK(h,l) ((~0u << (l)) & (~0u >> (31-(h))))
#define FIELD_PREP(mask,v) (((u32)(v) << __builtin_ctz(mask)) & (mask))
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
#define DIV_ROUND_UP(a,b) (((a)+(b)-1)/(b))
#define CAMSS_8150 8150
#define MSM_VFE_PAD_SINK 0
struct device { int unused; };
struct mock_camss_res { int version; };
struct mock_vfe_res { bool is_lite; };
struct camss { struct mock_camss_res *res; };
struct vfe_device {
 void *base;
 struct mock_vfe_res *res;
 struct camss *camss;
 struct { bool gamma_enabled, lsc_enabled; u8 lsc_bank; } pixel175;
};
struct vfe_line { struct v4l2_mbus_framefmt fmt[1]; };
static void *memchr_inv(const void *p,int value,size_t n)
{ const unsigned char *v=p;for(size_t i=0;i<n;i++)if(v[i]!=(unsigned char)value)return (void *)(v+i);return NULL; }
#include "camss-vfe-175-gamma.h"
#include "camss-vfe-175-lsc.h"
static u32 memory[1024],ram[256][256],before[1024],saved_ram[256][256];
static unsigned writes,barriers;
static unsigned address(const void *p)
{
 ptrdiff_t offset=(const char *)p-(const char *)memory;
 assert(offset>=0 && (size_t)offset<sizeof(memory) && offset%4==0);
 return (unsigned)offset;
}
static u32 readl_relaxed(const void *p) { return memory[address(p)/4]; }
static void writel_relaxed(u32 value,void *p)
{
 unsigned off=address(p);writes++;
 if(off==0xc30){
  u32 selector=memory[0xc24/4]&255,index=memory[0xc28/4];assert(index<256);
  if(selector>=26 && selector<=31){
   unsigned ch=selector>=30?0:selector>=28?2:1;
   unsigned bank=selector&1;
   assert(memory[0x34/4]&8);assert(bank!=((memory[0x798/4]>>ch)&1));
   assert(index<64);
  }else{
   assert(selector==14||selector==15||selector==18||selector==19);
   assert(memory[0x2c/4]&256);
  }
  ram[selector][index]=value;
 }
 memory[off/4]=value;
}
#define writel writel_relaxed
#define wmb() do { barriers++; } while(0)
#include "gamma-driver-body-private.c"
#include "lsc-driver-body-private.c"

static void reset(unsigned bank)
{
 for(unsigned i=0;i<1024;i++)memory[i]=0xa5a55a5a^(i*0x12345u);
 memory[0x798/4]=(memory[0x798/4]&~7u)|bank;
 for(unsigned s=0;s<256;s++)for(unsigned i=0;i<256;i++)ram[s][i]=0xf0000000u|s<<16|i;
 memcpy(before,memory,sizeof(memory));memcpy(saved_ram,ram,sizeof(ram));writes=barriers=0;
}
static void check_gamma(const struct camss_params_ife_gamma *b,unsigned initial,bool enabled)
{
 const unsigned selectors[3]={30,26,28};
 for(unsigned ch=0;ch<3;ch++)for(unsigned bank=0;bank<2;bank++)for(unsigned i=0;i<256;i++){
  unsigned s=selectors[ch]+bank;u32 expected=saved_ram[s][i];
  if(i<64 && bank!=((initial>>ch)&1)){
   const struct camss_ife_gamma_segment *v=&b->segments[ch][i];
   /* Independent signed representation rather than driver bitfield helpers. */
   expected=v->base+(u32)(v->delta<0?v->delta+1024:v->delta)*1024;
  }
  assert(ram[s][i]==expected);
 }
 u32 wanted[1024];memcpy(wanted,before,sizeof(wanted));
 wanted[0x798/4]^=7;wanted[0x48/4]=(wanted[0x48/4]&~8u)|(enabled?8:0);
 wanted[0xc30/4]=memory[0xc30/4];assert(!memcmp(memory,wanted,sizeof(memory)));
 assert(barriers>=2);
}
int main(int argc,char **argv)
{
 assert(argc==2);assert(sizeof(struct camss_params_ife_gamma)==776);
 struct mock_camss_res camss_res={CAMSS_8150};
 struct vfe_device vfe={.base=memory};
 struct mock_vfe_res res={false};
 struct camss camss={&camss_res};
 vfe.res=&res;vfe.camss=&camss;
 FILE *input=fopen(argv[1],"rb");assert(input);u32 words[64];assert(fread(words,sizeof(words),1,input)==1);assert(fgetc(input)==EOF);fclose(input);
 struct camss_params_ife_gamma b={.header={CAMSS_PARAMS_IFE_GAMMA,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(b)}};
 for(unsigned ch=0;ch<3;ch++)for(unsigned i=0;i<64;i++){
  u32 word=words[i];b.segments[ch][i].base=word&1023;
  b.segments[ch][i].delta=(word&0x80000)?(int)((word>>10)&1023)-1024:(int)((word>>10)&1023);
 }
 assert(!vfe_175_gamma_validate(NULL,&b.header));
 unsigned cases=0;
 for(unsigned mode=0;mode<3;mode++)for(unsigned banks=0;banks<8;banks++){
  reset(banks);vfe.pixel175.gamma_enabled=mode!=1;
  b.header.flags=mode==0?V4L2_ISP_PARAMS_FL_BLOCK_ENABLE:0;
  if(mode==2)for(unsigned ch=0;ch<3;ch++)for(unsigned i=0;i<64;i++){
   b.segments[ch][i].base=(i*17+ch*103)%1024;b.segments[ch][i].delta=(int)((i*97+ch*73)%1024)-512;
  }
  assert(!vfe_175_gamma_validate(NULL,&b.header));
  vfe_175_gamma_params(&vfe,&b.header);check_gamma(&b,banks,mode!=1);cases++;
 }
 for(unsigned at=0;at<3*64;at++)for(unsigned bad=0;bad<3;bad++){
  struct camss_params_ife_gamma invalid=b;
  struct camss_ife_gamma_segment *s=&invalid.segments[at/64][at%64];
  if(bad==0)s->base=1024;else s->delta=bad==1?-513:512;
  assert(vfe_175_gamma_validate(NULL,&invalid.header)==-EINVAL);
 }
 for(unsigned flags=0;flags<8;flags++){
  b.header.flags=flags;assert((vfe_175_gamma_validate(NULL,&b.header)==0)==(flags<3));
 }
 long page=sysconf(_SC_PAGESIZE);char *guard=mmap(NULL,page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);assert(guard!=MAP_FAILED);assert(!mprotect(guard+page,page,PROT_NONE));
 struct v4l2_isp_params_block_header *disable=(void *)(guard+page-sizeof(*disable));
 *disable=(struct v4l2_isp_params_block_header){CAMSS_PARAMS_IFE_GAMMA,V4L2_ISP_PARAMS_FL_BLOCK_DISABLE,sizeof(*disable)};
 reset(0);vfe.pixel175.gamma_enabled=true;assert(!vfe_175_gamma_validate(NULL,disable));vfe_175_gamma_params(&vfe,disable);
 before[0x48/4]&=~8u;assert(!memcmp(memory,before,sizeof(memory)));assert(!memcmp(ram,saved_ram,sizeof(ram)));assert(!vfe.pixel175.gamma_enabled);munmap(guard,page*2);
 /* Reopening uses the standard format and resets the previous bypass state. */
 struct v4l2_pix_format_mplane pix={.pixelformat=V4L2_PIX_FMT_NV12,.xfer_func=V4L2_XFER_FUNC_709};struct vfe_175_gamma_config config;
 assert(!vfe_175_gamma_from_format(&pix,&config));reset(5);assert(!vfe_175_gamma_configure(&vfe,&config));assert(vfe.pixel175.gamma_enabled);vfe_175_gamma_stop(&vfe);assert(!vfe.pixel175.gamma_enabled && !(memory[0x48/4]&8));
 /* Exercise both users of shared DMI consecutively, in either packet order. */
 struct camss_params_lsc lsc={.header={CAMSS_PARAMS_LSC,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(lsc)},.cell_width=144,.cell_height=144};
 for(unsigned ch=0;ch<4;ch++)for(unsigned i=0;i<CAMSS_LSC_MESH_POINTS;i++)lsc.gains[ch][i]=1024+ch*300+i;
 assert(!vfe_175_lsc_validate(NULL,&lsc.header));
 for(unsigned order=0;order<2;order++){
  reset(2);vfe_175_lsc_init(&vfe);b.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_ENABLE;
  u32 dmi_cfg=memory[0xc24/4],dmi_addr=memory[0xc28/4],color_clock=memory[0x34/4],lens_clock=memory[0x2c/4];
  if(order==0){vfe_175_gamma_params(&vfe,&b.header);vfe_175_lsc_params(&vfe,&lsc.header);}
  else{vfe_175_lsc_params(&vfe,&lsc.header);vfe_175_gamma_params(&vfe,&b.header);}
  assert(memory[0xc24/4]==dmi_cfg && memory[0xc28/4]==dmi_addr && memory[0x34/4]==color_clock && memory[0x2c/4]==lens_clock);
  assert(memory[0x48/4]&8);assert(memory[0x40/4]&256);
 }
 printf("GAMMA_REGISTER_PASS cases=%u field_rejections=576 shared_dmi_orders=2 header_disable=1\n",cases);
 return 0;
}
