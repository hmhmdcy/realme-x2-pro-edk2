"""Exercise the actual BLS/WB callbacks and generic parser with exact payloads."""
from pathlib import Path
import hashlib,json,re,resource,subprocess,sys
import host
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
HERE=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
D=TREE/'drivers/media/platform/qcom/camss';parent='--parent' in sys.argv
srcdir=host.PRIVATE/'source-before298' if parent else D
source=(srcdir/'camss-vfe-175-pixel.c').read_text();header=(srcdir/'camss-vfe-175-pixel.h').read_text()
def function(name):
 m=re.search(r'(?:static )?(?:int|void|u32) '+name+r'\(.*?\n\}',source,re.S);assert m,name;return m[0]
parser_path=TREE/'drivers/media/v4l2-core/v4l2-isp.c';p=parser_path.read_text();a=p.index('int v4l2_isp_params_validate_buffer_size(');b=p.index('EXPORT_SYMBOL_GPL(v4l2_isp_params_validate_buffer);')
parser=re.sub(r'EXPORT_SYMBOL_GPL\([^;]+;','',p[a:b])
state=re.search(r'struct vfe_175_pixel_state \{.*?\};',header,re.S)[0]
prelude=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <errno.h>
#define __counted_by(x)
#include <linux/qcom-camss-config.h>
typedef uint32_t u32;typedef uint16_t u16;
#define GENMASK(h,l) ((UINT32_MAX>>(31-(h)))&(UINT32_MAX<<(l)))
#define BIT(n) (1U<<(n))
#define FIELD_PREP(m,v) (((u32)(v)<<__builtin_ctz(m))&(m))
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define dev_dbg(...) ((void)0)
struct device{int unused;};
struct vb2_buffer{size_t payload;};
static size_t vb2_get_plane_payload(struct vb2_buffer*b,unsigned i){assert(!i);return b->payload;}
struct v4l2_isp_params_block_type_info{size_t size;int(*block_validate)(struct device*,const struct v4l2_isp_block_header*);};
struct vfe_175_stats_state{u16 left,top,width,height;bool enabled;};
'''
mocks=r'''
struct vfe_device;
struct vfe_line{bool is_pix;struct vfe_device*owner;struct{struct{struct{struct{int pix_mp;}fmt;}active_fmt;}video_out;}output[1];struct{unsigned code;}fmt[1];};
struct vfe_device{unsigned char*base;struct vfe_175_pixel_state pixel175;};
#define MSM_VFE_PAD_SINK 0
static struct vfe_device*to_vfe(struct vfe_line*l){return l->owner;}
static uint32_t bank[0x1000/4];static unsigned writes,stats_calls,stop_calls;static int prepare_error;
static u32 readl_relaxed(const void*p){assert((const char*)p>=(const char*)bank&&(const char*)p<=(const char*)bank+sizeof(bank)-4);return *(const u32*)p;}
static void writel_relaxed(u32 v,void*p){assert((char*)p>=(char*)bank&&(char*)p<=(char*)bank+sizeof(bank)-4);*(u32*)p=v;writes++;}
static int vfe_175_bhist_validate(struct device*d,const struct v4l2_isp_block_header*b){(void)d;(void)b;return 0;}
static void vfe_175_stats_params(struct vfe_device*v,struct vfe_line*l,const struct v4l2_isp_block_header*b){(void)v;(void)l;(void)b;stats_calls++;}
static int vfe_175_stats_prepare(struct vfe_line*l){(void)l;return 0;}
#define MODULE_STUB(n,e) struct vfe_175_##n##_config{int unused;};static int vfe_175_##n##_configure(struct vfe_device*v,const struct vfe_175_##n##_config*c){(void)v;(void)c;return e;}static void vfe_175_##n##_stop(struct vfe_device*v){(void)v;stop_calls++;}
MODULE_STUB(cst,0) MODULE_STUB(gamma,prepare_error) MODULE_STUB(demux,0) MODULE_STUB(mnds,0)
static int vfe_175_cst_from_format(const void*f,struct vfe_175_cst_config*c){(void)f;(void)c;return 0;}
static int vfe_175_gamma_from_format(const void*f,struct vfe_175_gamma_config*c){(void)f;(void)c;return 0;}
static int vfe_175_demux_from_code(unsigned code,struct vfe_175_demux_config*c){(void)code;(void)c;return 0;}
static int vfe_175_mnds_from_line(struct vfe_line*l,struct vfe_175_mnds_config*c){(void)l;(void)c;return 0;}
static int vfe_175_demosaic_prepare(struct vfe_line*l){(void)l;return 0;}
static int vfe_175_round_prepare(struct vfe_line*l){(void)l;return 0;}
static void vfe_175_demosaic_stop(struct vfe_device*v){(void)v;stop_calls++;}
static void vfe_175_round_stop(struct vfe_device*v){(void)v;stop_calls++;}
void vfe_175_pixel_stop(struct vfe_device*v);
'''
# Retain the real descriptor table as well as callbacks; omit only includes.
body='\n'.join(l for l in source.splitlines() if not l.startswith('#include'))
tests=r'''
static int submit(struct vfe_device*v,struct vfe_line*l,const void*b,size_t bytes,bool apply){
 struct v4l2_isp_buffer*p=malloc(sizeof(*p)+bytes);assert(p);p->version=1;p->data_size=bytes;memcpy(p->data,b,bytes);
 struct vb2_buffer vb={.payload=sizeof(*p)+bytes};
 int ret=v4l2_isp_params_validate_buffer_size(NULL,&vb,sizeof(*p)+CAMSS_PARAMS_IFE_MAX_PAYLOAD);
 if(!ret)ret=v4l2_isp_params_validate_buffer(NULL,&vb,p,vfe_175_params_info,6);
 if(!ret&&apply)vfe_175_params_apply(v,l,p);free(p);return ret;
}
static unsigned independent_level(unsigned in){uint64_t n=(uint64_t)in*16383;return n/65535+((n%65535)*2>=65535);}
static void check(unsigned level,bool enabled){
 unsigned actual=(enabled?independent_level(level):0);
 if ((bank[0x6b0/4]&0x3fff)!=actual) fprintf(stderr,"level=%u enabled=%u expected=%u reg=%08x\n",level,enabled,actual,bank[0x6b0/4]);
 assert((bank[0x6b0/4]&0x3fff)==actual);
 assert((bank[0x6b0/4]>>15)==2048);
 assert((bank[0x6b0/4]&0x4000)==(0xa5a5a5a5U&0x4000));
 assert((bank[0x40/4]&0x800)==(actual?0x800:0));
 assert((bank[0x40/4]&~0x800U)==(0xa5a5a5a5U&~0x800U));
 assert((bank[0x6b4/4]&0x3fff3fff)==0&&(bank[0x6b8/4]&0x3fff3fff)==0);
 assert((bank[0x6b4/4]&0xc000c000)==(0xa5a5a5a5U&0xc000c000));
 assert((bank[0x6b8/4]&0xc000c000)==(0xa5a5a5a5U&0xc000c000));
}
int main(void){
 struct vfe_device v={.base=(unsigned char*)bank};struct vfe_line pix={.is_pix=true,.owner=&v},rdi={.owner=&v};
 memset(bank,0xa5,sizeof(bank));assert(!vfe_175_pixel_prepare(&rdi)&&writes==0);
 struct camss_params_wb_gain w={.header={CAMSS_PARAMS_WB_GAIN,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(w)},.g_gain=1024,.b_gain=2048,.r_gain=3072,.g_sub=4096,.b_sub=4096,.r_sub=4096};
 /* Old callbacks reject the newly required equal-channel public input. */
 assert(!submit(&v,&pix,&w,sizeof(w),true));check(4096,true);
 for(unsigned i=0;i<=65535;i++){
  w.g_sub=w.b_sub=w.r_sub=i;assert(!submit(&v,&pix,&w,sizeof(w),true));check(i,true);
 }
 assert(independent_level(0)==0&&independent_level(65535)==16383&&independent_level(4096)==1024);
 for(unsigned i=0;i<32768;i++){
  w.g_gain=i;w.b_gain=32767-i;w.r_gain=(i*97)%32768;assert(!submit(&v,&pix,&w,sizeof(w),true));
  unsigned g=(w.g_gain+4)/8,b=(w.b_gain+4)/8,r=(w.r_gain+4)/8;
  assert((bank[0x6fc/4]&0xfff0fff)==((g>4095?4095:g)|((b>4095?4095:b)<<16)));
  assert((bank[0x700/4]&0xfff)==(r>4095?4095:r));
 }
 w.g_gain=w.b_gain=w.r_gain=1024;w.g_sub=w.b_sub=w.r_sub=4096;
 struct v4l2_isp_block_header disable={CAMSS_PARAMS_WB_GAIN,V4L2_ISP_PARAMS_FL_BLOCK_DISABLE,sizeof(disable)};
 assert(!submit(&v,&pix,&disable,sizeof(disable),true));check(4096,false);
 assert(!v.pixel175.wb_enabled&&v.pixel175.black_level==65535);
 w.header.flags=0;w.g_sub=w.b_sub=w.r_sub=8192;assert(!submit(&v,&pix,&w,sizeof(w),true));check(8192,false);
 assert(v.pixel175.black_level==8192&&!v.pixel175.wb_enabled);
 w.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_ENABLE;assert(!submit(&v,&pix,&w,sizeof(w),true));check(8192,true);
 unsigned before=writes;assert(!submit(&v,&rdi,&w,sizeof(w),true)&&writes==before);
 u16*bad[]={&w.g_sub,&w.b_sub,&w.r_sub,&w.g_add,&w.b_add,&w.r_add,&w._pad[0],&w._pad[1],&w._pad[2]};
 for(unsigned i=0;i<9;i++){u16 old=*bad[i];*bad[i]=1;assert(submit(&v,&pix,&w,sizeof(w),true)==-EINVAL);*bad[i]=old;}
 for(unsigned i=32768;i<=65535;i++){w.g_gain=i;assert(submit(&v,&pix,&w,sizeof(w),true)==-EINVAL);}w.g_gain=1024;
 for(unsigned i=1;i<sizeof(w);i++){w.header.size=i;assert(submit(&v,&pix,&w,i,true)==-EINVAL);}w.header.size=sizeof(w);
 w.header.flags=3;assert(submit(&v,&pix,&w,sizeof(w),true)==-EINVAL);w.header.flags=4;assert(submit(&v,&pix,&w,sizeof(w),true)==-EINVAL);w.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_ENABLE;
 assert(before==writes);
 struct camss_params_aec_bhist h={.header={CAMSS_PARAMS_AEC_BHIST,1,sizeof(h)},.width=4,.height=2};
 unsigned char mixed[sizeof(w)+sizeof(h)];memcpy(mixed,&w,sizeof(w));memcpy(mixed+sizeof(w),&h,sizeof(h));
 assert(!submit(&v,&pix,mixed,sizeof(mixed),true)&&stats_calls==1);check(8192,true);
 vfe_175_pixel_stop(&v);assert(!(bank[0x40/4]&0x800));
 assert(!vfe_175_pixel_prepare(&pix));check(0,true);assert(v.pixel175.black_level==0);
 assert(!submit(&v,&pix,&w,sizeof(w),true));prepare_error=-EIO;assert(vfe_175_pixel_prepare(&pix)==-EIO);assert(!(bank[0x40/4]&0x800));
 puts("BLC_PUBLIC_OFFSET_CONTRACTS_PASSED");
}
'''
# The parent state lacks the new field; it must compile and fail at acceptance.
if parent:state=state.replace('bool wb_enabled;','u16 black_level;\n\tbool wb_enabled;')
harness=prelude+state+mocks+body+parser+tests
tag='parent' if parent else 'fixed';path=host.PRIVATE/f'blc-{tag}-host-private.c';path.write_text(harness);binary=host.PRIVATE/f'blc-{tag}-host-private'
q=subprocess.run(['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation','-D__EXPORTED_HEADERS__','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I'+str(TREE/'include/uapi'),str(path),'-o',str(binary)],capture_output=True)
(host.PRIVATE/f'blc-{tag}-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run([str(binary)],capture_output=True);(host.PRIVATE/f'blc-{tag}-run-private.log').write_bytes(q.stdout+q.stderr)
if parent:assert q.returncode!=0 and b'Assertion' in q.stderr
else:assert q.returncode==0,(q.stdout+q.stderr).decode()
report=dict(stage=298,parent_negative_control=parent,expected_outcome_observed=True,exit_code=q.returncode,asan_ubsan=True,
 actual_common_parser_and_pixel_callbacks=True,offset_cases=0 if parent else 65536,gain_cases=0 if parent else 32768,
 preserves_unowned_register_bits=not parent,header_only_disable_exact_allocation=not parent,disabled_cache_update_and_reenable=not parent,
 stop_and_prepare_failure_disable_blc=not parent,reopen_defaults_and_rdi_isolation=not parent,
 unchanged_uapi=True,physical_validation_pending=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),harness_sha256=hashlib.sha256(harness.encode()).hexdigest())
(HERE/f'blc-{tag}-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
