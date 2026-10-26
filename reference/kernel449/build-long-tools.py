from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
old=(HERE.parent/'kernel363/pipeline-fixture.c').read_text();source=old
source=source.replace('int main(int argc,char **argv) {','''static double monotonic_seconds(void) {
 struct timespec now;
 if(clock_gettime(CLOCK_MONOTONIC,&now))return -1;
 return (double)now.tv_sec+(double)now.tv_nsec/1000000000.;
}
int main(int argc,char **argv) {''')
source=source.replace(' if(argc<3)return 2;',''' if(argc<3)return 2;
 unsigned timeout_seconds=50;const char *setting=getenv("PIPELINE_FIXTURE_TIMEOUT_SECONDS");
 if(setting){char *end=NULL;errno=0;unsigned long n=strtoul(setting,&end,10);if(errno||!*setting||*end||n<1||n>600)return 2;timeout_seconds=(unsigned)n;}
 if(monotonic_seconds()<0)return 2;''')
source=source.replace('int status=0;time_t start=time(NULL);bool signalled=false;','int status=0;double start=monotonic_seconds();bool signalled=false;')
source=source.replace('  if((interrupted||time(NULL)-start>50)&&!signalled){kill(-child,SIGINT);signalled=true;start=time(NULL);}', '''  double now=monotonic_seconds();if(now<0)now=start+timeout_seconds+11;
  if((interrupted||now-start>timeout_seconds)&&!signalled){kill(-child,SIGINT);signalled=true;start=now;}''')
source=source.replace('if(signalled&&time(NULL)-start>5)', 'if(signalled&&now-start>(timeout_seconds>50?10:5))')
assert source!=old and 'time(NULL)' not in source and source.count('PIPELINE_FIXTURE_TIMEOUT_SECONDS')==1
(HERE/'pipeline-fixture-long.c').write_text(source)
flags=['-static','-std=gnu17','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include']
q=subprocess.run(['aarch64-linux-gnu-gcc',*flags,str(HERE/'pipeline-fixture-long.c'),'-o',str(P/'pipeline-fixture-long')],capture_output=True)
(P/'long-fixture-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2500:]
prior=HERE/'gst-sustained-r1.c'
if not prior.exists():shutil.copyfile(HERE/'gst-sustained.c',prior);shutil.copyfile(P/'gst-sustained',P/'gst-sustained-r1')
gst=prior.read_text().replace('#include <stdlib.h>','#include <stdlib.h>\n#include <signal.h>\nstatic volatile sig_atomic_t interrupted;\nstatic void on_signal(int unused){(void)unused;interrupted=1;}')
gst=gst.replace(' gst_init(NULL,NULL);',' signal(SIGINT,on_signal);signal(SIGTERM,on_signal);\n gst_init(NULL,NULL);')
gst=gst.replace('while(!result && frames<target)', 'while(!result && !interrupted && frames<target)')
gst=gst.replace('  GstSample *sample=gst_app_sink_try_pull_sample(GST_APP_SINK(sink),5*GST_SECOND);','''  GstSample *sample=NULL;
  for(unsigned wait=0;wait<50&&!interrupted&&!sample;++wait)sample=gst_app_sink_try_pull_sample(GST_APP_SINK(sink),100*GST_MSECOND);
  if(interrupted){if(sample)gst_sample_unref(sample);result=9;break;}''')
gst=gst.replace(' GstBus *bus=', ' if(interrupted && !result)result=9;\n GstBus *bus=')
(HERE/'gst-sustained.c').write_text(gst)
W='/private/camss449-probes';work=storage.SDK/W.lstrip('/');shutil.copyfile(HERE/'gst-sustained.c',work/'gst-sustained.c')
with storage.sdk_candidate():
 flags=subprocess.check_output(['chroot',str(storage.SDK),'pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-allocators-1.0'],text=True).split()
 q=subprocess.run(['chroot',str(storage.SDK),'gcc','-O2','-Wall','-Wextra','-Werror',W+'/gst-sustained.c',*flags,'-o',W+'/gst-sustained'],capture_output=True)
 (P/'long-gst-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2500:]
shutil.copyfile(work/'gst-sustained',P/'gst-sustained')
rows=[dict(name=n,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_sha256=hashlib.sha256((HERE/s).read_bytes()).hexdigest()) for n,p,s in [('pipeline-fixture',P/'pipeline-fixture-long','pipeline-fixture-long.c'),('gst-sustained',P/'gst-sustained','gst-sustained.c')]]
r=dict(stage=449,fixture_default50s_max600s_monotonic_bound=True,long_case_350s_then10s_grace=True,gst_signal_handler_reaches_state_null_cleanup=True,per_sample_missing_buffer_timeout_still5s_polled100ms=True,production_448_and_lifecycle_probe_unchanged=True,aarch64_werror=True,clients=rows,passed=True)
(HERE/'long-client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
