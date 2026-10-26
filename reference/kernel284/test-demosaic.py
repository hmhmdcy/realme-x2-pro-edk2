"""Exercise actual Demosaic36, pixel preparation and 17x failure/stop paths."""
from pathlib import Path
import hashlib,json,re,subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel284')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
SOURCE=TREE/'drivers/media/platform/qcom/camss'
names=['camss-vfe-175-demosaic.c','camss-vfe-175-pixel.c']
texts={n:(SOURCE/n).read_text() for n in names}
structs=[]
for name,tag in [('camss-vfe-175-demosaic.h','vfe_175_demosaic_config'),('camss-vfe-175-pixel.h','vfe_175_pixel_state')]:
    structs.append(re.search(r'struct '+tag+r' \{.*?\};',(SOURCE/name).read_text(),re.S)[0])
transport=(SOURCE/'camss-vfe-17x.c').read_text()
def function(name,ret):
    match=re.search(r'static '+ret+' '+name+r'\(',transport);assert match
    return transport[match.start():transport.index('\n}',match.start())+2]
prelude=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define __counted_by(x)
#include <linux/qcom-camss-config.h>
typedef uint32_t u32;
typedef uint16_t u16;
typedef int16_t s16;
#define BIT(x) (1U << (x))
#define GENMASK(h,l) ((UINT32_MAX >> (31-(h))) & (UINT32_MAX << (l)))
#define FIELD_PREP(mask,val) (((u32)(val) << __builtin_ctz(mask)) & (mask))
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
struct device { int unused; };
struct v4l2_isp_params_block_type_info { size_t size; int (*block_validate)(struct device *,const struct v4l2_isp_block_header *); };
enum { CAMSS_8150=8150,CAMSS_8650=8650,MSM_VFE_PAD_SRC=1 };
'''
mocks=r'''
struct vfe_device;
struct vfe_line { bool is_pix; struct vfe_device *owner; };
struct vfe_hw_ops { int (*vfe_line_prepare)(struct vfe_line *); };
struct vfe_res { bool is_lite; const struct vfe_hw_ops *hw_ops; };
struct camss_res { int version; };
struct camss { struct camss_res *res; };
struct vfe_device { unsigned char *base; struct vfe_res *res; struct camss *camss;
 struct vfe_175_pixel_state pixel175; unsigned int stream_count,stream_lock; bool was_streaming; };
struct vfe_output { struct vfe_line *line; unsigned int pad; struct { unsigned int bus_client; } wm[2]; };
#define to_vfe(line) ((line)->owner)
int vfe_175_demosaic_prepare(struct vfe_line *);
void vfe_175_demosaic_stop(struct vfe_device *);
static unsigned char bank[0x1000];
static unsigned int reads,writes,barriers,trace[32],nt,locked,puts_count,start_count,raw_stops,full_stops,queued;
static int get_error,start_error;
static u32 readl_relaxed(const void *p)
{ u32 v;assert((const unsigned char *)p>=bank && (const unsigned char *)p<=bank+sizeof(bank)-4);memcpy(&v,p,4);reads++;return v; }
static void writel_relaxed(u32 v,void *p)
{ assert((unsigned char *)p>=bank && (unsigned char *)p<=bank+sizeof(bank)-4);memcpy(p,&v,4);writes++;if(nt<32)trace[nt++]=(unsigned char *)p-bank; }
static void wmb(void) { barriers++;if(nt<32)trace[nt++]=0xffff; }
static void mutex_lock(unsigned int *l) { (void)l;assert(!locked);locked=1; }
static void mutex_unlock(unsigned int *l) { (void)l;assert(locked);locked=0; }
static void vfe_enable_irq_common(struct vfe_device *v) { (void)v;assert(locked); }
static int vfe_get_output_v2(struct vfe_line *l) { (void)l;return get_error; }
static void vfe_put_output(struct vfe_line *l) { (void)l;puts_count++; }
static int vfe_enable_output_v2(struct vfe_line *l) { (void)l;assert(!locked);start_count++;return start_error; }
static void vfe_params_apply_queued(struct vfe_device *v,struct vfe_line *l)
{ (void)v;assert(l->is_pix && !locked);queued++; }
static void vfe_175_full_stop(struct vfe_device *v,struct vfe_output *o) { (void)v;(void)o;full_stops++; }
static void vfe_wm_stop(struct vfe_device *v,unsigned int wm,struct vfe_line *line) { (void)v;assert(wm==2 && !line->is_pix);raw_stops++; }
'''
tests=r'''
static u32 get(unsigned int address) { u32 v;memcpy(&v,bank+address,4);return v; }
static void reset_trace(void) { writes=reads=barriers=nt=0; }
int main(void)
{
 struct camss_res soc={CAMSS_8150};struct camss camss={&soc};
 const struct vfe_hw_ops ops={.vfe_line_prepare=vfe_175_pixel_prepare};
 struct vfe_res res={.hw_ops=&ops};struct vfe_device v={.base=bank,.res=&res,.camss=&camss};
 struct vfe_line pix={true,&v},rdi={false,&v};
 struct vfe_175_demosaic_config c={.lambda_g=128,.classifier_a=128,.classifier_w=102,.dynamic_g_clamp=true,.enabled=true};
 memset(bank,0,sizeof(bank));assert(vfe_175_demosaic_configure(&v,&c)==0);
 assert(writes==4 && barriers==1 && nt==5);
 assert(trace[0]==0x6f8 && trace[1]==0x71c && trace[2]==0x720 && trace[3]==0xffff && trace[4]==0x40);
 assert(get(0x6f8)==0x100 && get(0x71c)==0x8000 && get(0x720)==0x08000066 && get(0x40)==0x400);
 /* Independent field oracles, including the hardware's signed classifier. */
 for(int w=-32768;w<=32767;w++) {
  c.classifier_w=w;reset_trace();int ret=vfe_175_demosaic_configure(&v,&c);
  if(w < -512 || w > 511)assert(ret==-EINVAL && !writes && !reads && !barriers);
  else { assert(!ret);assert((get(0x720)&1023)==(unsigned int)((w+1024)%1024)); }
 }
 c.classifier_w=102;
 for(unsigned int a=0;a<=65535;a++) {
  c.classifier_a=a;reset_trace();int ret=vfe_175_demosaic_configure(&v,&c);
  if(a>400)assert(ret==-EINVAL && !writes && !reads);
  else assert(!ret && (get(0x720)>>20)==a);
 }
 c.classifier_a=128;
 for(unsigned int g=0;g<256;g++) {
  c.lambda_g=g;c.lambda_rb=255-g;reset_trace();assert(!vfe_175_demosaic_configure(&v,&c));
  assert((get(0x71c)&0xff00ff00)==(g*256+(255-g)*16777216U));
 }
 c.lambda_g=256;reset_trace();assert(vfe_175_demosaic_configure(&v,&c)==-EINVAL && !reads && !writes);
 c.lambda_g=128;c.lambda_rb=65535;assert(vfe_175_demosaic_configure(&v,&c)==-EINVAL && !writes);
 c.lambda_rb=0;
 for(unsigned int flags=0;flags<64;flags++) {
  c.directional_g_disable=flags&1;c.directional_rb_disable=flags&2;c.cosited_rgb=flags&4;
  c.dynamic_g_clamp=flags&8;c.dynamic_rb_clamp=flags&16;c.enabled=flags&32;
  memset(bank,0xa5,sizeof(bank));reset_trace();assert(!vfe_175_demosaic_configure(&v,&c));
  unsigned int mode=(flags&1)+((flags&2)?2:0)+((flags&4)?16:0)+((flags&8)?256:0)+((flags&16)?512:0)+((flags&32)?0:2048);
  assert(get(0x6f8)==((0xa5a5a5a5U&~0xb13U)|mode));
  assert((get(0x71c)&0x00ff00ff)==(0xa5a5a5a5U&0x00ff00ff));
  assert((get(0x720)&0x000ffc00)==(0xa5a5a5a5U&0x000ffc00));
  assert(get(0x40)==((0xa5a5a5a5U&~1024U)|((flags&32)?1024U:0)));
 }
 reset_trace();assert(vfe_175_demosaic_configure(&v,NULL)==-EINVAL && !reads && !writes);
 res.is_lite=true;assert(vfe_175_demosaic_prepare(&pix)==-EINVAL && !writes);vfe_175_demosaic_stop(&v);assert(!writes);
 res.is_lite=false;soc.version=CAMSS_8650;assert(vfe_175_pixel_prepare(&pix)==-EINVAL && !writes);vfe_175_pixel_stop(&v);assert(!writes);
 soc.version=CAMSS_8150;assert(vfe_175_pixel_prepare(&rdi)==0 && !writes);
 assert(vfe_175_pixel_prepare(&pix)==0 && writes==8 && v.pixel175.wb_enabled);
 assert((get(0x6fc)&0x0fff0fff)==0x00800080 && (get(0x700)&4095)==128);
 vfe_175_pixel_stop(&v);assert(!(get(0x40)&1024));
 /* Actual 17x enable and output-stop callbacks use the processing cleanup. */
 memset(bank,0,sizeof(bank));reset_trace();start_error=-EIO;
 assert(vfe_enable(&pix)==-EIO && v.stream_count==0 && !v.was_streaming && puts_count==1 && queued==1 && !(get(0x40)&1024));
 start_error=0;reset_trace();assert(vfe_enable(&pix)==0 && v.stream_count==1 && v.was_streaming && queued==2 && (get(0x40)&1024));
 struct vfe_output full={.line=&pix,.pad=MSM_VFE_PAD_SRC};
 vfe_output_stop_175(&v,&full);assert(full_stops==1 && !(get(0x40)&1024));
 assert(vfe_175_demosaic_prepare(&pix)==0);full.pad=5;vfe_output_stop_175(&v,&full);assert(full_stops==2 && (get(0x40)&1024));
 struct vfe_output raw={.line=&rdi,.wm={{2}}};reset_trace();vfe_output_stop_175(&v,&raw);assert(raw_stops==1 && !writes);
 v.stream_count=0;v.was_streaming=false;get_error=-EBUSY;reset_trace();unsigned int q=queued;
 assert(vfe_enable(&pix)==-EBUSY && !writes && v.stream_count==0 && queued==q);
 get_error=0;soc.version=CAMSS_8650;reset_trace();unsigned int starts=start_count;
 assert(vfe_enable(&pix)==-EINVAL && !writes && start_count==starts && !locked);
 puts("PASS: Demosaic36 fields, exhaustive classifier bounds, masks/order, RDI isolation and actual enable/stop rollback");
}
'''
code=prelude+'\n'.join(structs)+mocks
code+='\n'.join('\n'.join(l for l in texts[n].splitlines() if not l.startswith('#include')) for n in names)
code+=function('vfe_enable','int')+'\n'+function('vfe_output_stop_175','void')+tests
path=PRIVATE/'demosaic-host-tests-private.c';path.write_text(code)
command=['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-D__EXPORTED_HEADERS__',
         '-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-I'+str(TREE/'include/uapi'),
         str(path),'-o',str(PRIVATE/'demosaic-host-tests-private')]
compile_result=subprocess.run(command,text=True,capture_output=True)
(PRIVATE/'demosaic-host-compile-private.log').write_text(compile_result.stdout+compile_result.stderr)
assert compile_result.returncode==0,compile_result.stderr
result=subprocess.run([str(PRIVATE/'demosaic-host-tests-private')],text=True,capture_output=True)
(PRIVATE/'demosaic-host-tests-private.log').write_text(result.stdout+result.stderr)
assert result.returncode==0,result.stdout+result.stderr
report=dict(stage=284,exit=0,asan_ubsan=True,source_sha256={n:hashlib.sha256(t.encode()).hexdigest() for n,t in texts.items()},
            harness_sha256=hashlib.sha256(code.encode()).hexdigest(),classifier_w_inputs=65536,classifier_a_inputs=65536,
            masks_and_configuration_order=True,actual_enable_and_stop_functions_tested=True,
            hardware_mmio_simulated=True,not_deployed=True,output=result.stdout.strip())
(ROOT/'demosaic-host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
