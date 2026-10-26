from pathlib import Path
import runpy,re,subprocess,json,itertools,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'))
k=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel');base=k/'drivers/media/platform/qcom/camss';out=Path('/mnt/e/edk2-samurai-out/kernel124/c-contracts');out.mkdir(exist_ok=True)
def block(t,marker):
 i=t.index(marker);b=t.index('{',i);j=b+1;depth=1
 while depth:depth+=(t[j]=='{')-(t[j]=='}');j+=1
 return t[b:j]
def func(n,name):
 t=(base/n).read_text();m=re.search(r'^(?:static )?(?:s64|int|u8|u16|void|bool) '+name+r'\(',t,re.M);assert m,name
 return t[m.start():t.index(block(t[m.start():],name),m.start())+len(block(t[m.start():],name))]
def records(t):return [(int(a,16),int(b,16),int(c,16),d) for a,b,c,d in re.findall(r'\{\s*(0x[\da-fA-F]+),\s*(0x[\da-fA-F]+),\s*(0x[\da-fA-F]+),\s*(CSIPHY_\w+)\s*\}',t)]
prefix='''#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32;
typedef int32_t s32; typedef uint64_t u64; typedef int64_t s64;
#define BIT(n) (1U << (n))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define GFP_KERNEL 0
'''
checks=[]
def compile_run(name,source,cases):
 p=out/(name+'.c');p.write_text(prefix+source)
 cp=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-Wno-missing-field-initializers','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-o',str(out/name),str(p)],capture_output=True,timeout=60)
 (out/(name+'-compile.txt')).write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,(name,cp.stderr.decode()[:4000])
 cp=subprocess.run([str(out/name)],capture_output=True,timeout=30);(out/(name+'-run.txt')).write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,(name,cp.stderr.decode()[:4000])
 checks.append(dict(name=name,actual_driver_functions_extracted_without_body_rewrite=True,compiler='gcc -Wall -Wextra -Werror ASan UBSan; kernel-style unused-parameter, sign-compare and missing-field-initializers exclusions',cases=cases,exit=cp.returncode,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
parser='''enum { V4L2_MBUS_CSI2_DPHY=4, V4L2_MBUS_CSI2_CPHY=1, V4L2_MBUS_CSI2_CPHY_LINE_ORDER_ABC=0 };
struct device { int unused; }; struct fwnode_handle { bool clock,polarities; };
struct csiphy_lane { u8 pos,pol; };
struct csiphy_lanes_cfg { bool is_cphy; int num_data; struct csiphy_lane *data; struct csiphy_lane clk; };
struct v4l2_mbus_config_mipi_csi2 { unsigned char clock_lane,num_data_lanes,data_lanes[8]; bool lane_polarities[9]; int line_orders[8]; };
struct v4l2_fwnode_endpoint { struct { unsigned int port; } base; int bus_type; union { struct v4l2_mbus_config_mipi_csi2 mipi_csi2; } bus; };
struct camss_async_subdev { struct { int csiphy_id; struct { struct csiphy_lanes_cfg lane_cfg; } csi2; } interface; };
static struct v4l2_fwnode_endpoint fixture; static int parse_fail,alloc_fail,allocations;
static int v4l2_fwnode_endpoint_parse(struct fwnode_handle *ep,struct v4l2_fwnode_endpoint *v) { *v=fixture; return parse_fail; }
static bool fwnode_property_present(struct fwnode_handle *ep,const char *key) { return strcmp(key,"clock-lanes")==0?ep->clock:ep->polarities; }
static void *devm_kcalloc(struct device *dev,int n,size_t size,int flags) { allocations++; return alloc_fail?NULL:calloc(n,size); }
'''+func('camss.c','camss_parse_endpoint_node')+'''
struct media_entity { bool sensor; }; struct media_pad { int unused; }; static struct media_pad pad;
static u64 pixel_rate=336000000; static s64 direct; static unsigned int got_mul,got_div;
static struct media_pad *camss_find_sensor_pad(struct media_entity *e) { return e->sensor?&pad:NULL; }
static s64 v4l2_get_link_freq(struct media_pad *p,unsigned int mul,unsigned int div) { got_mul=mul;got_div=div;return direct?direct:(s64)(pixel_rate*mul/div); }
'''+func('camss.c','camss_get_link_freq')+'''
static int parse(struct fwnode_handle ep) { struct camss_async_subdev csd={0}; struct device dev={0}; int ret=camss_parse_endpoint_node(&dev,&ep,&csd); if (!ret) { assert(csd.interface.csi2.lane_cfg.is_cphy==(fixture.bus_type==1)); assert(csd.interface.csi2.lane_cfg.num_data==fixture.bus.mipi_csi2.num_data_lanes); for (int i=0;i<csd.interface.csi2.lane_cfg.num_data;i++) assert(csd.interface.csi2.lane_cfg.data[i].pos==fixture.bus.mipi_csi2.data_lanes[i]); } free(csd.interface.csi2.lane_cfg.data);return ret; }
int main(void) {
 struct fwnode_handle ep={0};fixture.bus_type=1;fixture.bus.mipi_csi2.num_data_lanes=3;fixture.bus.mipi_csi2.data_lanes[0]=0;fixture.bus.mipi_csi2.data_lanes[1]=1;fixture.bus.mipi_csi2.data_lanes[2]=2;
 assert(parse(ep)==0);alloc_fail=1;assert(parse(ep)==-ENOMEM);alloc_fail=0;
 parse_fail=-EIO;assert(parse(ep)==-EIO);parse_fail=0;
 fixture.bus_type=99;assert(parse(ep)==-EINVAL);fixture.bus_type=1;
 fixture.bus.mipi_csi2.num_data_lanes=0;assert(parse(ep)==-EINVAL);fixture.bus.mipi_csi2.num_data_lanes=4;assert(parse(ep)==-EINVAL);fixture.bus.mipi_csi2.num_data_lanes=3;
 fixture.bus.mipi_csi2.data_lanes[2]=1;assert(parse(ep)==-EINVAL);fixture.bus.mipi_csi2.data_lanes[2]=3;assert(parse(ep)==-EINVAL);fixture.bus.mipi_csi2.data_lanes[2]=2;
 ep.clock=1;assert(parse(ep)==-EINVAL);ep.clock=0;ep.polarities=1;assert(parse(ep)==-EINVAL);ep.polarities=0;
 for (int v=1;v<6;v++){fixture.bus.mipi_csi2.line_orders[0]=v;assert(parse(ep)==-EINVAL);}fixture.bus.mipi_csi2.line_orders[0]=0;
 fixture.bus.mipi_csi2.lane_polarities[2]=1;assert(parse(ep)==-EINVAL);fixture.bus.mipi_csi2.lane_polarities[2]=0;
 for (int n=1;n<=3;n++){fixture.bus.mipi_csi2.num_data_lanes=n;assert(parse(ep)==0);}
 fixture.bus_type=4;fixture.bus.mipi_csi2.num_data_lanes=4;for(int i=0;i<4;i++)fixture.bus.mipi_csi2.data_lanes[i]=i+1;assert(parse(ep)==0);
 fixture.bus.mipi_csi2.data_lanes[0]=0;assert(parse(ep)==-EINVAL);fixture.bus.mipi_csi2.data_lanes[0]=1;fixture.bus.mipi_csi2.clock_lane=5;assert(parse(ep)==-EINVAL);
 struct media_entity e={true};
'''
frequency_cases=0
for cphy in [False,True]:
 for bpp in [8,10,12,14,16]:
  for lanes in range(1,4 if cphy else 5):
   val=336000000*bpp*(7 if cphy else 16)//(2*lanes*16)
   parser+=f' assert(camss_get_link_freq(&e,{bpp},{lanes},{int(cphy)})=={val});assert(got_mul=={bpp*(7 if cphy else 1)} && got_div=={2*lanes*(16 if cphy else 1)});\n';frequency_cases+=1
parser+=''' direct=150000000;assert(camss_get_link_freq(&e,10,3,true)==direct);assert(camss_get_link_freq(&e,10,4,false)==direct);
 assert(camss_get_link_freq(&e,0,1,false)==-EINVAL);assert(camss_get_link_freq(&e,65,1,true)==-EINVAL);assert(camss_get_link_freq(&e,10,0,false)==-EINVAL);assert(camss_get_link_freq(&e,10,4,true)==-EINVAL);assert(camss_get_link_freq(&e,10,5,false)==-EINVAL);e.sensor=false;assert(camss_get_link_freq(&e,10,1,false)==-ENODEV);
 puts("PARSER_AND_FREQUENCY_PASS");return 0; }
'''
compile_run('parser-frequency',parser,dict(parser_positive=5,parser_negative=18,frequency_oracle=frequency_cases,direct_frequency=2,frequency_invalid=6))
phy=(base/'camss-csiphy-3ph-1-0.c').read_text();native=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/drivers/media/platform/msm/camera_8150/cam_sensor_module/cam_csiphy/include/cam_csiphy_1_1_hwreg.h').read_text()
native_rows=records(block(native,'csiphy_3ph_v1_1_reg'));candidate_rows=records(block(phy,'lane_regs_sm8150_cphy'));assert candidate_rows==native_rows and len(native_rows)==129
defines=phy[phy.index('#define CSIPHY_3PH_LNn_CFG1'):phy.index('/* 5nm 2PH')];defines=defines[:defines.index('/* SM8150')]
table='static const struct csiphy_lane_regs lane_regs_sm8150_cphy[3][43] = '+block(phy,'lane_regs_sm8150_cphy')+';\n'
versions=re.findall(r'case (CAMSS_\w+):',block(phy,'static bool csiphy_is_gen2'));assert len(set(versions))==len(versions)
writer=defines+table+'enum { '+','.join(versions)+' };\n'+'''
struct csiphy_lane { u8 pos,pol; }; struct csiphy_lanes_cfg { bool is_cphy; int num_data;struct csiphy_lane *data;struct csiphy_lane clk;};
struct csiphy_csi2_cfg { struct csiphy_lanes_cfg lane_cfg; }; struct csiphy_config { struct csiphy_csi2_cfg *csi2; };
struct csiphy_device_regs { const struct csiphy_lane_regs *lane_regs;int lane_array_size;const struct csiphy_lane_regs *cphy_regs[3];int cphy_array_size;u32 offset; };
struct camss { struct {u32 version;} *res; };
struct csiphy_device { struct csiphy_device_regs *regs;struct camss *camss;unsigned char *base;u32 timer_clk_rate; };
static struct { unsigned int addr,val; } trace[512];static int traces,reset_delay,gen1_calls;
static unsigned char mmio[4096];
static void writel_relaxed(u32 val,void *p){assert(traces<512);assert((unsigned char*)p>=mmio && (unsigned char*)p<mmio+sizeof(mmio));trace[traces].addr=(unsigned char*)p-mmio;trace[traces++].val=val;}
static void udelay(unsigned int n){assert(n==0);}
static void usleep_range(unsigned int lo,unsigned int hi){assert(lo==1000 && hi==1100);reset_delay++;}
static u64 div_u64(u64 a,u32 b){assert(b);return a/b;} static u64 div64_u64(u64 a,u64 b){assert(b);return a/b;}
#define min_t(type,a,b) ((type)(a)<(type)(b)?(type)(a):(type)(b))
static void csiphy_gen1_config_lanes(struct csiphy_device *d,struct csiphy_config *cfg,u8 settle){gen1_calls++;}
'''+''.join(func('camss-csiphy-3ph-1-0.c',n)+'\n' for n in ['csiphy_settle_cnt_calc','csiphy_gen2_write_regs','csiphy_gen2_config_lanes','csiphy_get_lane_mask','csiphy_is_gen2','csiphy_lanes_enable'])
writer+='''int main(void){struct csiphy_lane lanes[3]={{0},{1},{2}};struct csiphy_csi2_cfg csi={.lane_cfg={.is_cphy=true,.data=lanes}};struct csiphy_config cfg={&csi};struct csiphy_device_regs regs={.cphy_regs={lane_regs_sm8150_cphy[0],lane_regs_sm8150_cphy[1],lane_regs_sm8150_cphy[2]},.cphy_array_size=43,.offset=0x800};typeof(((struct camss*)0)->res[0]) resource={.version=CAMSS_8150};struct camss camss={&resource};struct csiphy_device dev={&regs,&camss,mmio,300000000};
 assert(csiphy_settle_cnt_calc(0,300000000)==0);assert(csiphy_settle_cnt_calc(-1,300000000)==0);assert(csiphy_settle_cnt_calc(420000000,0)==0);assert(csiphy_settle_cnt_calc(420000000,19200000)==0);assert(csiphy_settle_cnt_calc(420000000,300000000)==21);assert(csiphy_settle_cnt_calc(1,300000000)==65535);assert(csiphy_settle_cnt_calc(INT64_MAX,300000000)==19);
'''
def expected(trios,settle):
 rr=[]
 for trio in trios:
  for addr,data,delay,ptype in native_rows[trio*43:(trio+1)*43]:
   if ptype in ['CSIPHY_DNP_PARAMS','CSIPHY_SKEW_CAL']:continue
   val=(settle&255) if ptype=='CSIPHY_SETTLE_CNT_LOWER_BYTE' else ((settle>>8)&255) if ptype=='CSIPHY_SETTLE_CNT_HIGHER_BYTE' else data;assert delay==0;rr.append((addr,val))
 return rr
permutations=[p for n in range(1,4) for p in itertools.permutations(range(3),n)]
for trios in permutations:
 writer+=f' traces=0;csi.lane_cfg.num_data={len(trios)};'
 for i,trio in enumerate(trios):writer+=f'lanes[{i}].pos={trio};'
 mask=sum(1<<trio for trio in trios);writer+=f'assert(csiphy_get_lane_mask(&csi.lane_cfg)=={mask});csiphy_gen2_config_lanes(&dev,&cfg,0xabcd);'
 rr=expected(trios,0xabcd);writer+=f'assert(traces=={len(rr)});'
 for i,(addr,val) in enumerate(rr):writer+=f'assert(trace[{i}].addr=={addr} && trace[{i}].val=={val});'
 writer+='\n'
# One complete actual enable trace, including ordered common reset and IRQ masks.
native_irq=records(block(native,'csiphy_irq_reg_1_1'));assert len(native_irq)==11
trios=(2,0);rr=[(0x814,0x22),(0x818,1),(0x81c,2),(0x800,1),(0x800,0)]+expected(trios,21)+[(a,b) for a,b,_,_ in native_irq]
writer+='traces=0;reset_delay=0;csi.lane_cfg.num_data=2;lanes[0].pos=2;lanes[1].pos=0;csiphy_lanes_enable(&dev,&cfg,420000000,5);'
writer+=f'assert(traces=={len(rr)} && reset_delay==1 && gen1_calls==0);'
for i,(a,b) in enumerate(rr):writer+=f'assert(trace[{i}].addr=={a} && trace[{i}].val=={b});'
writer+='csi.lane_cfg.is_cphy=false;assert(csiphy_get_lane_mask(&csi.lane_cfg)==0x85);puts("NATIVE_TABLE_TRACE_AND_SETTLE_PASS");return 0;}\n'
compile_run('native-trio-trace',writer,dict(native_tuples=129,ordered_trio_selections=len(permutations),enable_trace_writes=len(rr),settle_bounds=7,dphy_mask_regression=1))
power='''struct device {int unused;};struct camss {struct device *dev;};struct v4l2_subdev {void *data;};
struct csiphy_device;struct ops {void(*reset)(struct csiphy_device*);void(*hw_version_read)(struct csiphy_device*,struct device*);};struct resources {struct ops *hw_ops;};
struct csiphy_device {struct camss *camss;int num_supplies,supplies,nclocks,clock,irq;struct resources *res;};
static int failure,refs,supply_refs,clocks,irq_on,resets,versions;
static void *v4l2_get_subdevdata(struct v4l2_subdev *sd){return sd->data;}
static int pm_runtime_resume_and_get(struct device*d){if(failure==1)return -EIO;refs++;return 0;}
static void pm_runtime_put_sync(struct device*d){assert(refs==1);refs--;}
static int regulator_bulk_enable(int n,int s){assert(n==1);if(failure==2)return -EIO;supply_refs++;return 0;}
static void regulator_bulk_disable(int n,int s){assert(n==1 && supply_refs>=2);supply_refs--;}
static int csiphy_set_clock_rates(struct csiphy_device*d){return failure==3?-EIO:0;}
static int camss_enable_clocks(int n,int c,struct device*d){if(failure==4)return -EIO;clocks++;return 0;}
static void camss_disable_clocks(int n,int c){assert(clocks==1);clocks--;}
static void enable_irq(int n){irq_on++;}static void disable_irq(int n){assert(irq_on==1);irq_on--;}
static void reset(struct csiphy_device*d){resets++;}static void version(struct csiphy_device*d,struct device*v){versions++;}
'''+func('camss-csiphy.c','csiphy_set_power')+'''
int main(void){struct device dev={0};struct camss camss={&dev};struct ops ops={reset,version};struct resources res={&ops};struct csiphy_device phy={.camss=&camss,.num_supplies=1,.res=&res};struct v4l2_subdev sd={&phy};
 for(int f=1;f<=4;f++){failure=f;refs=clocks=irq_on=resets=versions=0;supply_refs=1;assert(csiphy_set_power(&sd,1)==-EIO);assert(refs==0 && supply_refs==1 && clocks==0 && irq_on==0 && resets==0 && versions==0);}
 failure=0;supply_refs=1;assert(csiphy_set_power(&sd,1)==0);assert(refs==1 && supply_refs==2 && clocks==1 && irq_on==1 && resets==1 && versions==1);assert(csiphy_set_power(&sd,0)==0);assert(refs==0 && supply_refs==1 && clocks==0 && irq_on==0);puts("SHARED_PHY_POWER_UNWIND_PASS");return 0;}
'''
compile_run('shared-power-faults',power,dict(injected_failure_points=4,full_on_off=1,existing_dsi_reference_preserved=True))
report=dict(actual_c_harnesses=checks,own_native_active_cphy_table_exact=True,reference_three_wrong_values_not_used=True,native_v11_data_rate_table_null_confirmed=True,source_only_not_hardware_test=True,settle_formula_hardware_unverified=True,cphy_clock_ratio_from_official_kernel_documentation=True,phone_unchanged=True)
(r/'reference/kernel124/cphy-c-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('CPHY124_ACTUAL_C_NATIVE_TABLE_FREQUENCY_POWER_ASAN_UBSAN_PASS')
