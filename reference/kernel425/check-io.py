"""Compare actual maintained C layout/IO with native PD10 and config transport."""
from pathlib import Path
import importlib.util,json,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
storage=module('storage284',HERE.parent/'kernel284/storage.py');kernel=storage.mounted_build().parent/'source354';camss=kernel/'drivers/media/platform/qcom/camss'
state=json.loads((HERE/'source-state.json').read_text());assert subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()==state['commit']
boot=(camss/'camss-icp-a5-boot.c').read_text();ipe=(camss/'camss-icp-a5-ipe.c').read_text()
old=subprocess.check_output(['git','-C',str(kernel),'show',state['parent_commit']+':drivers/media/platform/qcom/camss/camss-icp-a5-boot.c'],text=True)
def function(text,name):
 m=re.search(r'(?:static )?(?:int|bool|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert m,name;return m[0]
prefix='''#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint8_t u8;typedef uint32_t u32;typedef uint64_t u64;
#define U32_MAX UINT32_MAX
#define IPE_IO_CONFIG_BYTES 1216
struct camss_a5_nv12_layout {u32 width,height,stride,slice_height;bool uv_swap;};
struct camss_a5_ipe_io {struct camss_a5_nv12_layout input,output;u32 output_port;};
struct camss_a5_pd10_layout {u32 width,height,stride,slice_height,bytes;};
static void put_unaligned_le32(u32 v,void *p){u8 *d=p;for(unsigned i=0;i<4;i++)d[i]=v>>(8*i);}
'''
code=prefix+function(ipe,'camss_a5_ipe_pd10_quarter')+function(boot,'nv12_layout_valid')+function(boot,'encode_nv12_image')+function(boot,'camss_a5_ipe_encode_io')+function(old,'encode_ipe_io').replace('encode_ipe_io','old_encode_ipe_io')+(HERE/'io-cases.c').read_text()
(P/'io-model.c').write_text(code)
cases=[(w,h,port,swap,pad) for w,h in [(128,128),(282,210),(284,214),(640,480),(650,480),(1920,1080),(4608,3456),(8192,8192)] for port in [8,9] for swap in [0,1] for pad in [0,8]]
inputs=b''.join(struct.pack('<5I',*c) for c in cases);outputs=[]
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('io-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'io-model.c'),'-o',str(binary)],capture_output=True)
 (P/(arch+'-io-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2200:]
 q=subprocess.run([*launch,str(binary)],input=inputs,capture_output=True);(P/(arch+'-io-run.log')).write_bytes(q.stderr);assert not q.returncode,q.stderr.decode()
 (P/(arch+'-io-private.bin')).write_bytes(q.stdout);outputs.append(q.stdout)
assert outputs[0]==outputs[1] and len(outputs[0])==len(cases)*2452
n=module('native425',HERE/'native-model.py');native=n.Native();cache={};rows=[]
for index,(w,h,port,swap,pad) in enumerate(cases):
 at=index*2452;layout=struct.unpack_from('<5I',outputs[0],at);qw,qh=((w+7)//4)&~1,((h+7)//4)&~1
 if (qw,qh) not in cache:cache[qw,qh]=native.pd10(qw,qh)
 image,descriptor=cache[qw,qh];stride,slice_h=struct.unpack_from('<2I',descriptor,52);bytes_=struct.unpack_from('<Q',image,56)[0]
 assert layout==(qw,qh,stride,slice_h,bytes_)
 config=bytearray(1216)
 for p,multiple in [(0,1),(port,2)]:
  off=p*84;struct.pack_into('<3I',config,off,20,w,h);struct.pack_into('<I',config,off+24,swap);struct.pack_into('<4I',config,off+52,w+multiple*pad,h+multiple*pad,w+multiple*pad,(h+multiple*pad)//2)
 config[84:168]=descriptor;struct.pack_into('<I',config,1192,1)
 assert bytes(config)==outputs[0][at+20:at+1236]
 config[84:168]=bytes(84);assert bytes(config)==outputs[0][at+1236:at+2452]
 rows.append(dict(width=w,height=h,port=port,uv_swap=bool(swap),padding=pad,quarter_width=qw,quarter_height=qh,pd10_stride=stride,pd10_slice_height=slice_h,pd10_bytes=bytes_))
r=dict(stage=425,cases=len(cases),invalid_preserve_cases_per_architecture=24,host_asan_ubsan=True,aarch64_static_qemu=True,
 actual_candidate_function_bodies=True,native_pd10_initialize_and_config_io_executed=True,compared_bytes=len(outputs[0]),different_bytes=0,
 legacy_null_coarse_bytes_unchanged=True,input_sizes_strictly_checked=True,native_compact_pd10_not_new_reference_256_32_alignment=True,
 rows=rows,phone_accessed=False,coarse_pixel_producer_and_runtime_not_claimed=True,passed=True)
(HERE/'io-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
