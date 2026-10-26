"""Exercise the actual ownership predicate, including a freed stopped request."""
from pathlib import Path
import hashlib,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
p=storage.candidate()/'src/libcamera-v0.7.2/src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
text=p.read_text();start=text.index('    const uint64_t frameEpoch = epoch_;');end=text.index('    };',start)+7
actual=text[start:end]
finish=text[text.index('void CamssVfeData::finish('):text.index('void CamssVfeData::imageProcessed(')]
assert finish.count('if (!ownsFrame()) return;')==3
for name in ['frameMetadata','processFocus','prepareIpeParameters']:
 after=finish.split('ipa_->'+name,1)[1].split(';',1)[1]
 assert after.lstrip().startswith('if (!ownsFrame()) return;') or (name=='processFocus' and 'if (!ownsFrame()) return;' in after[:150])
code='''#include <cassert>
#include <cstdint>
#include <map>
struct Request {uint32_t n;uint32_t sequence() const{return n;}};
struct Frame {void *ifeImage;};
int main(){
 bool running_=true;uint64_t epoch_=8;int image,other;void *buffer=&image;
 Request *request=new Request{42};std::map<Request*,Frame> requests_;
 requests_[request]={buffer};
ACTUAL
 assert(ownsFrame());
 running_=false;assert(!ownsFrame());running_=true;
 ++epoch_;assert(!ownsFrame());--epoch_;
 requests_.at(request).ifeImage=&other;assert(!ownsFrame());requests_.at(request).ifeImage=buffer;
 ++request->n;assert(!ownsFrame());--request->n;
 requests_.clear();assert(!ownsFrame());delete request;assert(!ownsFrame());
 return 0;
}
'''.replace('ACTUAL',actual)
(P/'reentry-predicate.cpp').write_text(code)
q=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie',str(P/'reentry-predicate.cpp'),'-o',str(P/'reentry-predicate')],capture_output=True);(P/'reentry-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(P/'reentry-predicate')],capture_output=True);(P/'reentry-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
r=dict(stage=441,actual_production_ownership_predicate_tested=True,host_asan_ubsan=True,live_stop_epoch_buffer_request_reuse_erased_and_freed_cases=True,three_synchronous_finish_calls_guarded=True,actual_full_pipeline_reentry_requires_hardware_validation=True,production_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),phone_accessed=False,passed=True)
(HERE/'reentry-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
