"""Test actual maintained serializers and complete stock firmware preparation."""
from pathlib import Path
import ast,hashlib,importlib.util,json,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
k=module('storage284',HERE.parent/'kernel284/storage.py').mounted_build().parent/'source354';d=k/'drivers/media/platform/qcom/camss'
source=(d/'camss-icp-a5-ipe.c').read_text();header=(d/'camss-icp-a5-ipe.h').read_text()
def function(text,name):
 m=re.search(r'(?:static )?(?:int|bool|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert m,name;return m[0]
tree=ast.parse((HERE.parent/'kernel384/check-serializer.py').read_text());prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
prefix+='''
typedef uint64_t u64;
#define U32_MAX UINT32_MAX
#define CAMSS_A5_IPE_FRAME_BYTES 3816U
#define CAMSS_A5_IPE_IQ_BYTES 2584U
#define min(a,b) ((a)<(b)?(a):(b))
static u16 get_unaligned_le16(const void *p){u16 x;memcpy(&x,p,2);return x;}
static u32 get_unaligned_le32(const void *p){u32 x;memcpy(&x,p,4);return x;}
static void put_unaligned_le64(u64 v,void *p){u8 *d=p;for(unsigned i=0;i<8;i++)d[i]=v>>(8*i);}
struct camss_a5_pd10_layout {u32 width,height,stride,slice_height,bytes;};
struct camss_a5_ipe_ltm_geometry {bool data_collection,image_processing,mask_filter;};
'''
for name in ['camss_a5_ipe_buffer','camss_a5_ipe_frame']:
 match=re.search(r'struct '+name+r' \{.*?^\};',header,re.S|re.M);assert match;prefix+=match[0]+'\n'
names=['camss_a5_ipe_pd10_quarter','camss_a5_ipe_striping_bytes','valid_buffer','buffers_overlap','nv12_plane_bytes','camss_a5_ipe_encode_frame',
 'ipe_partitions','camss_a5_ipe_bypass_partitions','camss_a5_ipe_ltm_partitions','camss_a5_ipe_bypass_size','bypass_module_1d',
 'camss_a5_ipe_ltm_size','ipe_encode_striping','camss_a5_ipe_encode_ltm_striping','camss_a5_ipe_ltm_pd10_size','ltm_coarse_axis','camss_a5_ipe_encode_ltm_pd10_striping']
code=prefix+'\n'.join(function(source,n) for n in names)+(HERE/'runtime-contract.c').read_text();(P/'runtime-model.c').write_text(code);outputs=[]
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('runtime-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'runtime-model.c'),'-o',str(binary)],capture_output=True)
 (P/(arch+'-runtime-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
 q=subprocess.run([*launch,str(binary)],capture_output=True);(P/(arch+'-runtime-run.log')).write_bytes(q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
 (P/(arch+'-runtime-private.bin')).write_bytes(q.stdout);outputs.append(q.stdout)
assert outputs[0]==outputs[1] and len(outputs[0])==4140+3816+3516
stripe=outputs[0][:4140];frame=outputs[0][4140:7956]
assert struct.unpack_from('<I',frame,108)[0]==0x20800000
n=module('native425',HERE.parent/'kernel425/native-model.py');fw=module('firmware425',HERE.parent/'kernel425/firmware-model.py')
config=(P.parent/'kernel425/width-640-dc-1-config-private.bin').read_bytes();iq=(P.parent/'kernel424/coarse-width-640-dc-1-iq-private.bin').read_bytes()
native=n.Native();gold,bl,capacity=native.striping(config,640,480,2,iq)
model,job,cdm,meta=fw.prepare(config,stripe,iq,640,480,46080)
_,goldjob,goldcdm,_=fw.prepare(config,gold,iq,640,480,46080)
assert job==goldjob and cdm==goldcdm
(P/'actual-c-stripe-private.bin').write_bytes(stripe);(P/'actual-c-frame-private.bin').write_bytes(frame);(P/'actual-c-cdm-private.bin').write_bytes(cdm)
r=dict(stage=429,actual_maintained_c_functions=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
 host_asan_ubsan=True,aarch64_static_qemu=True,compared_bytes=len(outputs[0]),different_architecture_bytes=0,
 invalid_geometry_capacity_pointer_and_coarse_overlap_no_write=True,legacy_dc_off_full_pass_unchanged=True,
 complete_stock_hal_striping_and_firmware_preparation=True,job_identical=True,whole_command_bytes_compared=len(cdm),different_command_bytes=0,
 actual_frame_pd10_port1_address_encoded=True,scratch_bytes=meta['required_scratch_bytes'],minimum_command_bytes=bl,
 geometry_scope='640x480 NV12, display8, two cores, DC+IP+mask',hardware_execution_not_claimed=True,passed=True)
(HERE/'runtime-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
