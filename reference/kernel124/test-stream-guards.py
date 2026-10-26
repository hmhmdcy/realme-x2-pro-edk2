from pathlib import Path
import runpy,re,subprocess,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'))
base=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel/drivers/media/platform/qcom/camss');out=Path('/mnt/e/edk2-samurai-out/kernel124/c-contracts')
def function(n,name):
 t=(base/n).read_text();m=re.search(r'^static int '+name+r'\(',t,re.M);assert m;start=m.start();b=t.index('{',m.end());i=b+1;depth=1
 while depth:depth+=(t[i]=='{')-(t[i]=='}');i+=1
 return t[start:i]
s='''#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
#include <stdio.h>
typedef uint8_t u8;typedef uint32_t u32;typedef int64_t s64;
#define BIT(n) (1U<<(n))
#define MSM_CSIPHY_PAD_SINK 0
#define MEDIA_LNK_FL_ENABLED 1
#define MEDIA_PAD_FL_SINK 1
#define MEDIA_PAD_FL_SOURCE 2
#define CSID_PAYLOAD_MODE_DISABLED 0
#define TPG_GRP_ID 2
#define dev_err(...) ((void)0)
#define dev_dbg(dev,...) ((void)(dev))
struct device {int unused;};struct camss {struct device *dev;};struct media_entity {void *sd;};struct media_pad {struct media_entity *entity;int flags,index;};
struct v4l2_subdev {struct media_entity entity;int grp_id;void *data;};
struct csiphy_lane {u8 pos,pol;};struct csiphy_lanes_cfg {bool is_cphy;int num_data;struct csiphy_lane *data;};struct csi2 {struct csiphy_lanes_cfg lane_cfg;};struct csiphy_config {struct csi2 *csi2;int combo_mode,csid_id;};
struct csiphy_device;struct ops {u8(*get_lane_mask)(struct csiphy_lanes_cfg*);void(*lanes_enable)(struct csiphy_device*,struct csiphy_config*,s64,u8);};struct formats {int formats,nformats;};struct res {struct formats *formats;struct ops *hw_ops;};struct regs {void *cphy_regs[3];};
struct csiphy_device {struct csiphy_config cfg;struct res *res;struct regs *regs;struct v4l2_subdev subdev;struct {int code;} fmt[1];struct camss *camss;void *base_clk_mux;int id;};
static int mask_calls,freq_calls,enable_calls,mmio_calls;
static u8 csiphy_get_bpp(int f,int n,int code){return 10;}
static s64 camss_get_link_freq(struct media_entity*e,int b,int n,bool c){freq_calls++;return 420000000;}
static u8 mask(struct csiphy_lanes_cfg*l){mask_calls++;return 1;}
static void enable(struct csiphy_device*d,struct csiphy_config*c,s64 f,u8 m){enable_calls++;}
static u32 readl_relaxed(void*p){mmio_calls++;return 0;}static void writel_relaxed(u32 val,void*p){mmio_calls++;}static void wmb(void){}
'''+function('camss-csiphy.c','csiphy_stream_on')+'''
struct csid_phy_config {bool is_cphy;int lane_cnt,csiphy_id;u32 lane_assign,en_vc;bool need_vc_update;};
struct csid_device {struct csid_phy_config phy;struct {int nmodes;}testgen;struct {struct {int val;}cur;} *testgen_mode;bool tpg_linked;struct camss *camss;};
struct tpg_device {struct {int lane_cnt;} *res;int id;};
static void *media_pad_remote_pad_first(const struct media_pad*p){return NULL;}
static struct v4l2_subdev *media_entity_to_v4l2_subdev(struct media_entity*e){return e->sd;}
static void *v4l2_get_subdevdata(struct v4l2_subdev*s){return s->data;}
static u32 csid_get_lane_assign(struct csiphy_lanes_cfg*l,int n){return l?0x20:0x3210;}
'''+function('camss-csid.c','csid_link_setup')+'''
int main(void){struct csi2 csi={.lane_cfg={.is_cphy=true,.num_data=2}};struct ops ops={mask,enable};struct formats formats={0};struct res res={&formats,&ops};struct device d={0};struct camss camss={&d};struct regs regs={0};struct csiphy_device phy={.cfg={.csi2=&csi},.res=&res,.camss=&camss};
 assert(csiphy_stream_on(&phy)==-EOPNOTSUPP);assert(mask_calls==0&&freq_calls==0&&enable_calls==0&&mmio_calls==0);
 phy.regs=&regs;assert(csiphy_stream_on(&phy)==-EOPNOTSUPP);assert(mask_calls==0&&freq_calls==0&&enable_calls==0&&mmio_calls==0);
 regs.cphy_regs[0]=&regs;assert(csiphy_stream_on(&phy)==0);assert(mask_calls==1&&freq_calls==1&&enable_calls==1&&mmio_calls==0);
 csi.lane_cfg.is_cphy=false;phy.regs=NULL;assert(csiphy_stream_on(&phy)==0);assert(mask_calls==2&&freq_calls==2&&enable_calls==2&&mmio_calls==0);
 csi.lane_cfg.is_cphy=true;struct csid_device csid={.camss=&camss};struct v4l2_subdev csid_sd={.data=&csid},phy_sd={.data=&phy,.grp_id=1};struct media_entity entity={&csid_sd},remote_entity={&phy_sd};struct media_pad local={&entity,MEDIA_PAD_FL_SINK,0},remote={&remote_entity,0,0};
 assert(csid_link_setup(&entity,&local,&remote,MEDIA_LNK_FL_ENABLED)==0);assert(csid.phy.is_cphy&&csid.phy.lane_cnt==2&&!csid.tpg_linked);
 typeof(((struct tpg_device*)0)->res[0]) tpg_res={4};struct tpg_device tpg={&tpg_res,1};struct v4l2_subdev tpg_sd={.data=&tpg,.grp_id=TPG_GRP_ID};remote_entity.sd=&tpg_sd;
 assert(csid_link_setup(&entity,&local,&remote,MEDIA_LNK_FL_ENABLED)==0);assert(!csid.phy.is_cphy&&csid.phy.lane_cnt==4&&csid.phy.lane_assign==0x3210&&csid.tpg_linked);
 remote_entity.sd=&phy_sd;phy.cfg.csi2=NULL;assert(csid_link_setup(&entity,&local,&remote,MEDIA_LNK_FL_ENABLED)==-EPERM);
 puts("UNSUPPORTED_STREAM_BEFORE_MMIO_AND_TPG_SELECTOR_PASS");return 0;}
'''
p=out/'stream-tpg-guards.c';p.write_text(s);args=['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-Wno-missing-field-initializers','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-o',str(out/'stream-tpg-guards'),str(p)]
cp=subprocess.run(args,capture_output=True,timeout=60);(out/'stream-tpg-guards-compile.txt').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr.decode()[:4000]
cp=subprocess.run([str(out/'stream-tpg-guards')],capture_output=True,timeout=30);(out/'stream-tpg-guards-run.txt').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr.decode()[:4000]
report=dict(actual_stream_on_and_link_setup_functions_extracted_without_body_rewrite=True,unsupported_null_regs_and_null_table_no_mask_frequency_mmio_or_enable=True,supported_cphy_stream_dispatch=True,dphy_null_regs_legacy_regression=True,cphy_then_tpg_clears_stale_selector=True,unlinked_sensor_rejected=True,asan_ubsan_pass=True,cases=7,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),host_stubs_not_hardware_test=True)
(r/'reference/kernel124/stream-guard-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('CPHY124_ACTUAL_STREAM_AND_TPG_GUARD_ASAN_UBSAN_PASS')
