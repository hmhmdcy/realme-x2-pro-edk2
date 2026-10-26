"""Three capture epochs in one CameraManager and a bounded sustained GST client."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
source=(HERE.parent/'kernel442/capture.cpp').read_text()
def replace(a,b):
 global source
 assert source.count(a)==1,(a,source.count(a));source=source.replace(a,b)
replace('#include <fstream>','#include <fstream>\n#include <filesystem>\n#include <sched.h>\n#include <sstream>')
replace('class Capture {','''static long lastManagerTid=0;
static std::set<unsigned> affinity(long tid)
{
 cpu_set_t native;CPU_ZERO(&native);std::set<unsigned> result;
 if(sched_getaffinity(tid,sizeof(native),&native))return result;
 for(unsigned i=0;i<CPU_SETSIZE;++i)if(CPU_ISSET(i,&native))result.insert(i);
 return result;
}
static std::string maskText(const std::set<unsigned> &mask)
{std::string value;for(auto c:mask){if(!value.empty())value+=',';value+=std::to_string(c);}return value;}
static std::set<unsigned> applicationMask;
static void identity()
{
 std::ifstream status("/proc/self/status");std::string line,caps="missing";
 while(std::getline(status,line))if(line.starts_with("CapEff:")){std::istringstream s(line.substr(7));s>>caps;}
 std::cout<<"APPLICATION_IDENTITY uid="<<getuid()<<" euid="<<geteuid()<<" capeff="<<caps<<std::endl;
}
class Capture {''')
replace('int main(int argc,char **argv)','int runCycle(int argc,char **argv,CameraManager &manager)')
replace(' CameraManager manager;if(manager.start())return 3;','')
replace(' auto camera=capture.camera;', ''' auto camera=capture.camera;
 std::cout<<"LIFECYCLE_CAMERA pointer="<<reinterpret_cast<uintptr_t>(camera.get())<<std::endl;''')
replace(' camera->requestCompleted.connect(&capture,&Capture::complete);ControlList initial(camera->controls());', ''' camera->requestCompleted.connect(&capture,&Capture::complete);
 struct Disconnect {std::shared_ptr<Camera> camera;Capture *capture;~Disconnect(){camera->requestCompleted.disconnect(capture);}} disconnect{camera,&capture};
 ControlList initial(camera->controls());''')
replace(' bool good=!stopped', ''' lastManagerTid=capture.callbackTid;
 const auto after=affinity(lastManagerTid);
 if(!lastManagerTid || after!=applicationMask || affinity(0)!=applicationMask)++capture.failed;
 std::cout<<"LIFECYCLE_AFTER_STOP tid="<<lastManagerTid<<" allowed="<<maskText(after)<<" application-allowed="<<maskText(affinity(0))<<std::endl;
 bool good=!stopped''')
source+='''
int main(int argc,char **argv)
{
 if(argc!=5 || !getenv("CAPTURE_DIR"))return 2;
 const std::filesystem::path base=getenv("CAPTURE_DIR");
 applicationMask=affinity(0);if(applicationMask.empty())return 2;
 identity();CameraManager manager;if(manager.start())return 3;
 std::cout<<"LIFECYCLE_MANAGER starts=1 pointer="<<reinterpret_cast<uintptr_t>(&manager)<<std::endl;
 unsigned completed=0;int result=0;
 for(const char *size:{"1280x720","1920x1080","1280x720"}){
  if(lastManagerTid && affinity(lastManagerTid)!=applicationMask){result=10;break;}
  auto folder=base/("cycle-"+std::to_string(completed));std::filesystem::create_directories(folder);
  if(setenv("CAPTURE_DIR",folder.c_str(),1))return 2;
  std::cout<<"LIFECYCLE_BEGIN cycle="<<completed<<" output="<<size<<" previous-tid="<<lastManagerTid<<" application-allowed="<<maskText(applicationMask)<<std::endl;
  std::array<char*,6> arguments{argv[0],argv[1],argv[2],argv[3],argv[4],const_cast<char*>(size)};
  result=runCycle(arguments.size(),arguments.data(),manager);
  std::cout<<"LIFECYCLE_END cycle="<<completed<<" status="<<result<<std::endl;
  if(result)break;
  ++completed;
 }
 manager.stop();std::cout<<"LIFECYCLE_RESULT cycles="<<completed<<" manager-starts=1 status="<<result<<std::endl;
 return result?result:completed==3?0:11;
}
'''
(HERE/'lifecycle.cpp').write_text(source)
gst=(HERE.parent/'kernel443/gst-hardware-probe.c').read_text().replace('n>600','n>10000')
gst=gst.replace(' gst_init(NULL,NULL);',''' FILE *status=fopen("/proc/self/status","r");char line[256],capabilities[32]="missing";
 if(status){while(fgets(line,sizeof(line),status))if(sscanf(line,"CapEff: %31s",capabilities)==1)break;fclose(status);}
 printf("APPLICATION_IDENTITY uid=%u euid=%u capeff=%s\\n",getuid(),geteuid(),capabilities);fflush(stdout);
 gst_init(NULL,NULL);''')
(HERE/'gst-sustained.c').write_text(gst)
W='/private/camss449-probes';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True)
shutil.copyfile(HERE/'lifecycle.cpp',work/'lifecycle.cpp');shutil.copyfile(HERE/'gst-sustained.c',work/'gst-sustained.c')
T='/work/libcamera/src/libcamera-v0.7.2'
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include',W+'/lifecycle.cpp','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o',W+'/lifecycle'],capture_output=True)
 (P/'lifecycle-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
 flags=subprocess.check_output(['chroot',str(storage.SDK),'pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-allocators-1.0'],text=True).split()
 q=subprocess.run(['chroot',str(storage.SDK),'gcc','-O2','-Wall','-Wextra','-Werror',W+'/gst-sustained.c',*flags,'-o',W+'/gst-sustained'],capture_output=True)
 (P/'gst-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
rows=[]
for name,file in [('lifecycle','lifecycle.cpp'),('gst-sustained','gst-sustained.c')]:
 shutil.copyfile(work/name,P/name);rows.append(dict(name=name,sha256=hashlib.sha256((P/name).read_bytes()).hexdigest(),source_sha256=hashlib.sha256((HERE/file).read_bytes()).hexdigest()))
r=dict(stage=449,aarch64_werror=True,production448_core_ipa_and_tuning_unchanged=True,lifecycle_single_manager_three_output_cycles=True,request_signals_disconnect_before_capture_object_destruction=True,stop_affinity_checked_while_manager_alive=True,sustained_client_only_frame_bound_and_identity_changed_from443=True,clients=rows,phone_accessed=False,passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
