"""Execute the actual pipeline setupLinks method against changed kernel graphs."""
from pathlib import Path
import hashlib
import json
import os
import resource
import subprocess

R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel268/link-tests-r1');P.mkdir(mode=0o700,parents=True)
prefix=r'''
#include <cassert>
#include <cerrno>
#include <cstdio>
#include <vector>
#define MEDIA_LNK_FL_ENABLED 1
#define MEDIA_LNK_FL_IMMUTABLE 2
struct MediaLink;
struct MediaPad { std::vector<MediaLink *> list;const auto &links() const { return list; } };
struct MediaEntity { std::vector<MediaPad *> list;const auto &pads() const { return list; } };
static int calls,fail_at;static bool streaming;
struct MediaLink {
 unsigned int cached;bool actual;MediaLink *conflict;
 unsigned int flags() const { return cached; }
 int setEnabled(bool value) {
  calls++;if(calls==fail_at)return -EIO;
  if((cached&MEDIA_LNK_FL_IMMUTABLE)&&value!=actual)return -EINVAL;
  if(streaming&&value!=actual)return -EBUSY;
  if(value&&conflict&&conflict->actual)return -EBUSY;
  actual=value;cached=(cached&~1U)|(value?1U:0U);return 0;
 }
};
class SimpleCameraData {
public:
 struct Entity { MediaEntity *entity;MediaLink *sourceLink;bool supportsRouting;MediaPad *sink,*source; };
 std::vector<Entity> entities_;
 int setupLinks();
};
'''
main=r'''
int main() {
 unsigned int cases=0;
 for(unsigned int bits=0;bits<64;bits++) {
  MediaLink rear={bits&1U,!!(bits&8U),nullptr},front={(bits>>1)&1U,!!(bits&16U),&rear},output={(bits>>2)&1U,!!(bits&32U),nullptr};rear.conflict=&front;
  MediaPad input={{&rear,&front}},source={{&output}},sink={{&output}};
  MediaEntity phy,csid={{&input,&source}},vfe={{&sink}};
  SimpleCameraData data;data.entities_={{&phy,&rear,false,nullptr,nullptr},{&csid,&output,false,&input,&source},{&vfe,nullptr,false,&sink,nullptr}};
  calls=0;fail_at=-1;streaming=false;assert(data.setupLinks()==0);
  assert(rear.actual&&!front.actual&&output.actual);cases++;
 }
 for(int failure=1;failure<=4;failure++) {
  MediaLink rear={0,false,nullptr},front={0,true,&rear},output={0,false,nullptr};rear.conflict=&front;
  MediaPad input={{&rear,&front}},source={{&output}},sink={{&output}};
  MediaEntity phy,csid={{&input,&source}},vfe={{&sink}};
  SimpleCameraData data;data.entities_={{&phy,&rear,false,nullptr,nullptr},{&csid,&output,false,&input,&source},{&vfe,nullptr,false,&sink,nullptr}};
  calls=0;fail_at=failure;streaming=false;assert(data.setupLinks()==-EIO);assert(calls==failure);cases++;
 }
 MediaLink rear={0,false,nullptr},front={0,true,&rear},output={0,false,nullptr},immutable={3,true,nullptr},other={0,true,nullptr};rear.conflict=&front;
 MediaPad input={{&rear,&front,&immutable}},source={{&output}},sink={{&output}},unused={{&other}};
 MediaEntity phy,csid={{&input,&source,&unused}},vfe={{&sink}};
 SimpleCameraData data;data.entities_={{&phy,&rear,false,nullptr,nullptr},{&csid,&output,true,&input,&source},{&vfe,nullptr,false,&sink,nullptr}};
 calls=0;fail_at=-1;streaming=false;assert(data.setupLinks()==0);assert(immutable.actual&&other.actual);cases++;
 front.actual=true;rear.actual=false;front.cached=0;rear.cached=0;streaming=true;calls=0;
 assert(data.setupLinks()==-EBUSY);assert(front.actual&&!rear.actual);cases++;
 printf("{\"cases\":%u,\"cached_and_kernel_states_independent\":true,\"ioctl_errors_preserved\":true}\n",cases);return 0;
}
'''
def body(source):
    a=source.index('int SimpleCameraData::setupLinks()');b=source.index('int SimpleCameraData::setupFormats(',a)
    return prefix+source[a:b]+main
def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
results={}
for name,file in [('actual','simple.cpp'),('old-negative','simple-before.cpp')]:
    p=P/(name+'.cpp');p.write_text(body((R/file).read_text()));binary=p.with_suffix('')
    q=subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(p),'-o',str(binary)],capture_output=True)
    (P/(name+'-compile-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()[-1500:]
    q=subprocess.run([str(binary)],capture_output=True,preexec_fn=no_core,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1'))
    (P/(name+'-run-private.log')).write_bytes(q.stdout+q.stderr)
    if name=='actual':assert q.returncode==0 and not q.stderr,q.stderr.decode()[-1500:];results[name]=json.loads(q.stdout)
    else:assert q.returncode!=0 and b'Assertion' in q.stderr;results[name]=dict(rejected=True)
report=dict(stage=268,actual_setup_links_method_extracted=True,asan_ubsan=True,results=results,
 source_sha256=hashlib.sha256((R/'simple.cpp').read_bytes()).hexdigest(),real_kernel_concurrency_not_modelled=True)
(R/'link-test-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
