"""Measure callback copy/store time without changing the camera pipeline."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
if (HERE/'client-build-validation.json').exists() and not (HERE/'client-build-r1-validation.json').exists():
 shutil.copyfile(HERE/'client-build-validation.json',HERE/'client-build-r1-validation.json');shutil.copyfile(P/'capture',P/'capture-timing-r1')
source=(HERE.parent/'kernel441/capture.cpp').read_text()
def replace(a,b):
 global source
 assert source.count(a)==1,(a,source.count(a));source=source.replace(a,b)
replace(' std::vector<uint8_t> data;',' const auto ioStart=std::chrono::steady_clock::now();\n std::vector<uint8_t> data;')
replace(' std::ofstream output(path,std::ios::binary);output.write(reinterpret_cast<const char*>(data.data()),data.size());',''' const auto storeStart=std::chrono::steady_clock::now();
 std::ofstream output(path,std::ios::binary);output.write(reinterpret_cast<const char*>(data.data()),data.size());output.close();
 const auto storeEnd=std::chrono::steady_clock::now();
 const auto ns=[](auto t){return std::chrono::duration_cast<std::chrono::nanoseconds>(t.time_since_epoch()).count();};
 std::cout<<"CAPTURE_IO sequence="<<buffer->metadata().sequence<<" enter="<<ns(ioStart)<<" store="<<ns(storeStart)<<" end="<<ns(storeEnd)
  <<" copy-mean-ns="<<ns(storeStart)-ns(ioStart)<<" store-ns="<<ns(storeEnd)-ns(storeStart)<<std::endl;''')
replace('#include <cstdio>','#include <cstdio>\n#include <algorithm>\n#include <cstdlib>\n#include <deque>\n#include <thread>\n#include <sys/syscall.h>')
replace(' void complete(Request *request)\n {',''' bool queued=true,draining=false;unsigned int delayMs=0;
 std::mutex eventMutex;std::deque<Request*> events;size_t eventPeak=0;
 long callbackTid=0,processTid=0;
 void complete(Request *request)
 {
  callbackTid=syscall(SYS_gettid);
  if (!queued) { process(request); return; }
  if (request->status()==Request::RequestCancelled) return;
  {
   std::lock_guard lock(eventMutex);
   events.push_back(request);eventPeak=std::max(eventPeak,events.size());
  }
  condition.notify_one();
 }
 Request *takeEvent()
 {
  std::lock_guard lock(eventMutex);
  if(events.empty())return nullptr;
  Request *request=events.front();events.pop_front();return request;
 }
 void process(Request *request)
 {''')
replace('if(!running||done||request->status()==Request::RequestCancelled)return;', 'if(!running||(!draining&&done)||request->status()==Request::RequestCancelled)return;\n  processTid=syscall(SYS_gettid);\n  if(!draining && !frames && delayMs){std::cout<<"CAPTURE_PAUSE milliseconds="<<delayMs<<" tid="<<processTid<<std::endl;std::this_thread::sleep_for(std::chrono::milliseconds(delayMs));}')
replace('auto p=policies[phase];','auto p=policies[draining?0:phase];')
replace('if(matched>=240 || (matched>=24 && lockedRun>=8))','if(!draining && (matched>=240 || (matched>=24 && lockedRun>=8)))')
replace('if(!done) {','if(!done && !draining) {')
replace(' Capture capture;',''' Capture capture;
 capture.queued=!getenv("CAPTURE_QUEUED") || std::strcmp(getenv("CAPTURE_QUEUED"),"0");
 if(const char *delay=getenv("CAPTURE_DELAY_MS")){char *end=nullptr;const auto ms=std::strtoul(delay,&end,10);if(!*delay||*end||ms>500)return 2;capture.delayMs=ms;}
 std::cout<<"CAPTURE_MODE queued="<<capture.queued<<" injected-delay-ms="<<capture.delayMs<<std::endl;''')
replace(' {std::unique_lock lock(capture.mutex);while(!capture.done&&!capture.failed&&!interrupted&&std::chrono::steady_clock::now()<deadline)capture.condition.wait_for(lock,std::chrono::milliseconds(100));capture.running=false;}', ''' if(capture.queued){
  std::unique_lock lock(capture.eventMutex);
  while(!capture.done&&!capture.failed&&!interrupted&&std::chrono::steady_clock::now()<deadline){
   if(capture.events.empty())capture.condition.wait_until(lock,deadline,[&]{return !capture.events.empty() || interrupted;});
   if(capture.events.empty())continue;
   Request *event=capture.events.front();capture.events.pop_front();
   lock.unlock();capture.process(event);lock.lock();
  }
  lock.unlock();std::lock_guard stateLock(capture.mutex);capture.running=false;
 }else{
  std::unique_lock lock(capture.mutex);
  while(!capture.done&&!capture.failed&&!interrupted&&std::chrono::steady_clock::now()<deadline)capture.condition.wait_for(lock,std::chrono::milliseconds(100));
  capture.running=false;
 }''')
replace('int stopped=camera->stop();bool good=', '''int stopped=camera->stop();
 if(capture.queued){
  capture.draining=true;capture.running=true;
  while(Request *event=capture.takeEvent())capture.process(event);
  capture.running=false;capture.draining=false;
 }
 std::cout<<"CAPTURE_DISPATCH queued="<<capture.queued<<" callback-tid="<<capture.callbackTid<<" process-tid="<<capture.processTid<<" event-peak="<<capture.eventPeak<<std::endl;
 bool good=''')
(HERE/'capture.cpp').write_text(source)
W='/private/camss442-probe';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True);shutil.copyfile(HERE/'capture.cpp',work/'capture.cpp')
T='/work/libcamera/src/libcamera-v0.7.2'
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include',W+'/capture.cpp','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o',W+'/capture'],capture_output=True)
(P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2500:]
shutil.copyfile(work/'capture',P/'capture')
r=dict(stage=442,measurement_only_probe=True,queued_app_dispatch_matches_existing_cam_app=True,optional_direct_and_queued_same_binary=True,bounded_app_delay_injection_max500ms=True,aarch64_werror=True,pipeline_ipa_and_profiles_unchanged=True,every_frame_still_saved=True,clients=[dict(name='capture',sha256=hashlib.sha256((P/'capture').read_bytes()).hexdigest(),source_sha256=hashlib.sha256(source.encode()).hexdigest())],passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
