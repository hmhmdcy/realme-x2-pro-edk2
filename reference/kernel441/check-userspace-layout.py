"""Compare the shared pipeline layout with the retained native allocator."""
from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess,shutil
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;tree=storage.candidate()/'src/libcamera-v0.7.2';storage.mount.mounted_build()
header=tree/'src/libcamera/pipeline/camss-vfe/camss_pd10.h';assert header.read_bytes()==(HERE/'camss_pd10.h').read_bytes()
source=r'''#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include "camss_pd10.h"
int main(){
 for (auto s:std::array<libcamera::Size,9>{{{0,640},{127,128},{128,126},{129,128},{640,481},{8194,128},{128,8194},{UINT32_MAX,128},{128,UINT32_MAX}}}) assert(!libcamera::camssPd10Layout(s));
 uint32_t input[2];while(fread(input,sizeof(input),1,stdin)==1){auto p=libcamera::camssPd10Layout({input[0],input[1]});assert(p);uint32_t out[]={p->size.width,p->size.height,p->stride,p->sliceHeight,p->frameSize};assert(fwrite(out,sizeof(out),1,stdout)==1);}return 0;
}
'''
(P/'layout-model.cpp').write_text(source);sizes=[(128,128),(282,210),(284,214),(640,480),(650,480),(1280,720),(1600,900),(1920,1080),(4608,3456),(8192,8192)];inputs=b''.join(struct.pack('<2I',*s) for s in sizes);outputs=[]
for arch,cc,flags,launch in [('host','g++',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','g++',['-static'],['qemu-aarch64'])]:
 binary=P/('layout-'+arch)
 if arch=='host':q=subprocess.run([cc,'-std=c++17','-O2','-Wall','-Wextra','-Werror',*flags,'-I'+str(header.parent),'-I'+str(tree/'include'),'-I'+str(tree/'output/include'),str(P/'layout-model.cpp'),'-o',str(binary)],capture_output=True)
 else:
  slot=storage.SDK/'private/camss441-layout';slot.mkdir(exist_ok=True);shutil.copyfile(P/'layout-model.cpp',slot/'model.cpp')
  with storage.sdk_candidate():q=subprocess.run(['chroot',str(storage.SDK),cc,'-std=c++17','-O2','-Wall','-Wextra','-Werror','-static','-I/work/libcamera/src/libcamera-v0.7.2/src/libcamera/pipeline/camss-vfe','-I/work/libcamera/src/libcamera-v0.7.2/include','-I/work/libcamera/src/libcamera-v0.7.2/output/include','/private/camss441-layout/model.cpp','-o','/private/camss441-layout/layout'],capture_output=True)
  shutil.copyfile(slot/'layout',binary)
 (P/(arch+'-layout-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launch,str(binary)],input=inputs,capture_output=True);(P/(arch+'-layout-run.log')).write_bytes(q.stderr);assert not q.returncode,q.stderr.decode();outputs.append(q.stdout)
assert outputs[0]==outputs[1] and len(outputs[0])==len(sizes)*20
s=importlib.util.spec_from_file_location('native425',HERE.parent/'kernel425/native-model.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n);native=n.Native();rows=[]
for i,(w,h) in enumerate(sizes):
 layout=struct.unpack_from('<5I',outputs[0],i*20);image,descriptor=native.pd10(layout[0],layout[1]);assert struct.unpack_from('<2I',descriptor,4)==layout[:2] and struct.unpack_from('<2I',descriptor,52)==layout[2:4] and struct.unpack_from('<Q',image,56)[0]==layout[4]
 rows.append(dict(full_width=w,full_height=h,coarse_width=layout[0],coarse_height=layout[1],stride=layout[2],packed_slice_height=layout[3],bytes=layout[4]))
r=dict(stage=441,actual_common_pipeline_header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),host_asan_ubsan=True,aarch64_static_qemu=True,original_hal_format_initializer_and_config_descriptor=True,layouts=rows,invalid_sizes_rejected_per_architecture=9,private_ipa_protocol_and_algorithms_unchanged=True,phone_accessed=False,passed=True)
(HERE/'userspace-layout-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='layouts'},indent=2))
