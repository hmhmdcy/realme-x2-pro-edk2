"""Compare actual PD10 layout and runtime MMIO with target producer controls."""
from pathlib import Path
import importlib.util,json,re,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
kernel=module('storage284',HERE.parent/'kernel284/storage.py').mounted_build().parent/'source354';D=kernel/'drivers/media/platform/qcom/camss'
stage=P/'runtime-includes/linux';(stage/'media').mkdir(parents=True,exist_ok=True)
shutil.copyfile(kernel/'include/uapi/linux/qcom-camss-config.h',stage/'qcom-camss-config.h');shutil.copyfile(kernel/'include/uapi/linux/media/v4l2-isp.h',stage/'media/v4l2-isp.h')
shutil.copyfile(kernel/'include/uapi/linux/media-bus-format.h',stage/'media-bus-format.h')
n=module('ds426',HERE.parent/'kernel426/ds4-model.py');m=n.Machine();layout_model=module('n425',HERE.parent/'kernel425/native-model.py').Native()
index=json.loads((P.parent/'kernel333/sunny_s5kgw1-index-private.json').read_text());raw=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
root=next(r for r in json.loads((P.parent/'kernel426/sunny_s5kgw1-ds4-reserves-private.json').read_text()) if r['tag']=='ds4to1v10_ife_full_dc4')
def blob(uid):
 e=index['entries'][str(uid)];return raw[index['base']+e['offset']:index['base']+e['offset']+e['bytes']]
data=blob(root['uid']);revision_uid=struct.unpack_from('<Q',data,32)[0];parsed,_=m.parse(root['tag'],root['uid'],data,revision_uid,blob(revision_uid))
inputs=[];expected=[];rows=[];node=n.h.DATA+0x100000;m.u.mem_map(node,0x40000)
for width,height in [(128,128),(284,214),(288,216),(640,480),(650,480),(1024,1024),(4096,3072)]:
 qw,qh=((width+7)//4)&~1,((height+7)//4)&~1
 image,io=layout_model.pd10(qw,qh);stride,slice_height=struct.unpack_from('<2I',io,52);size=struct.unpack_from('<Q',image,56)[0]
 regs,enable,_=m.execute(parsed,width,height);crop,rounding,packing,enable=m.producer_crops_and_round(width,height)
 assert packing==[(0xd6c,struct.pack('<I',0x300))]
 m.u.mem_write(node,bytes(0x40000));m.u.mem_write(node+0xff74,struct.pack('<2I',1,1));before=len(m.writes)
 assert m.call(0x2a8900,node,n.h.DATA+0x20000,phase='original-node-enable-aggregation')==0
 enables={a:b for a,b in m.writes[before:]};assert enables[0x4c]==struct.pack('<I',0x5518) and enables[0xd8c]==enables[0xdac]==struct.pack('<I',0xe00)
 expected.append(regs+packing[0][1]+b''.join(b for a,b in crop)+b''.join(b for a,b in rounding)+struct.pack('<4I',((qw*4+15)//16)*16,qh//2,stride,size)+enables[0xd8c]+enables[0xdac])
 inputs.append(struct.pack('<5I',width,height,*root['passes'][0][1:]));rows.append(dict(width=width,height=height,pd10_width=qw,pd10_height=qh,stride=stride,slice_height=slice_height,bytes=size,padded_slice_differs_from_active_rows=slice_height!=qh//2))
prefix='''#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <linux/videodev2.h>
#include <linux/media-bus-format.h>
#include <linux/qcom-camss-config.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;
#define U32_MAX UINT32_MAX
#define BIT(n) (1U<<(n))
#define GENMASK(h,l) ((UINT32_MAX<<(l)) & (UINT32_MAX>>(31-(h))))
#define FIELD_PREP(mask,val) (((u32)(val)<<__builtin_ctz(mask)) & (mask))
#define ALIGN(v,a) (((v)+(a)-1)&~((a)-1))
#define DIV_ROUND_UP(v,a) (((v)+(a)-1)/(a))
#define IS_ALIGNED(v,a) (!((v)&((a)-1)))
#define ARRAY_SIZE(v) (sizeof(v)/sizeof((v)[0]))
#define CAMSS_8150 8150
#define MSM_VFE_PAD_SRC_DS4 2
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define WARN_ON(v) ({bool task_bad=!!(v);assert(!task_bad);task_bad;})
#define wmb() do{}while(0)
static u32 mmio[0x4000/4];static unsigned writes;
static u32 rd(void *p){size_t i=(char*)p-(char*)mmio;assert(i<sizeof(mmio)&&!(i&3));return mmio[i/4];}
static void wr(u32 v,void *p){size_t i=(char*)p-(char*)mmio;assert(i<sizeof(mmio)&&!(i&3));if(i==0x2714)assert(mmio[0x2708/4]);mmio[i/4]=v;writes++;}
#define readl_relaxed rd
#define writel_relaxed wr
struct camss_res{unsigned version;};struct camss{struct camss_res *res;};struct vfe_res{bool is_lite;};
struct camss_video{struct v4l2_format active_fmt;};
struct vfe_line;struct vfe_output{struct vfe_line *line;u32 pad,wm_num,comp_group;struct {u32 bus_client,plane;}wm[2];struct camss_video video_out;};
struct vfe_line{struct vfe_device *owner;bool is_pix;struct vfe_output output[4];};
struct camss_buffer{u64 addr[3];};
struct vfe_device{void *base;struct camss *camss;struct vfe_res *res;struct {bool ds4_configured,ds4_running;u16 ds4_coefficient[3];}pixel175;};
'''
strip=lambda text:re.sub(r'^#include.*\n','',text,flags=re.M)
fmt=(D/'camss-format.c').read_text();match=re.search(r'int camss_format_pd10_layout\(.*?^\}',fmt,re.S|re.M);assert match
code=prefix+strip((D/'camss-format.h').read_text())+strip((D/'camss-vfe-175-ds4.h').read_text())+match[0]+'\n'+strip((D/'camss-vfe-175-ds4.c').read_text())+(HERE/'runtime-contract.c').read_text()
(P/'runtime-model.c').write_text(code);golden=b''.join(expected);inputs=b''.join(inputs);assert len(golden)==len(rows)*72
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('runtime-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-I'+str(stage.parent),*flags,str(P/'runtime-model.c'),'-o',str(binary)],capture_output=True)
 (P/(arch+'-runtime-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launch,str(binary)],input=inputs,capture_output=True);(P/(arch+'-runtime-run.log')).write_bytes(q.stderr);assert not q.returncode,q.stderr.decode();assert q.stdout==golden
 (P/(arch+'-runtime-output-private.bin')).write_bytes(q.stdout)
r=dict(stage=427,actual_maintained_layout_runtime_and_uapi_used=True,rows=rows,host_asan_ubsan=True,aarch64_static_qemu=True,
 native_precrop_ds4_depth_and_r2pd_match=True,complete_original_node_enable_aggregation_executed=True,ds4_local_crop_round_clamp_enables_match=True,original_gpl_wm_width_stride_and_frame_increment_match=True,shared_register_fields_preserved=True,
 wm_armed_before_address_fifo_write_enforced=True,coefficient_update_while_active_verified=True,invalid_layout_parameters_and_dma_ranges_rejected=True,
 dma_hardware_not_executed=True,phone_accessed=False,passed=True)
(HERE/'runtime-codec-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
