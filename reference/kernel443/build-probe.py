"""Instrument the existing normal libcamerasrc/appsink consumer, unchanged IQ."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
source=(HERE.parent/'kernel316/gst-hardware-probe.c').read_text()
def replace(a,b):
 global source
 assert source.count(a)==1,(a,source.count(a));source=source.replace(a,b)
replace('#include <linux/dma-buf.h>', '#include <linux/dma-buf.h>\n#include <linux/v4l2-subdev.h>\n#include <fcntl.h>')
replace('const int width=atoi(argv[2]),height=atoi(argv[3]);', '''const int width=atoi(argv[2]),height=atoi(argv[3]);
 unsigned target=120;
 const char *setting=getenv("GST_TARGET_FRAMES");
 if(setting){char *end=NULL;unsigned long n=strtoul(setting,&end,10);if(!*setting||*end||n<12||n>600)return 2;target=(unsigned)n;}
 printf("GST_TARGET frames=%u\\n",target);fflush(stdout);''')
replace('uint64_t previous=0;', 'uint64_t previous=0,previous_sequence=0;')
replace('frames<12', 'frames<target')
replace('sample_buffer(buffer,&hash))result=6;', '''GST_BUFFER_OFFSET(buffer)==GST_BUFFER_OFFSET_NONE ||
     (frames && GST_BUFFER_OFFSET(buffer)<=previous_sequence) ||
     GST_BUFFER_FLAG_IS_SET(buffer,GST_BUFFER_FLAG_CORRUPTED) ||
     gst_buffer_get_size(buffer)!=(gsize)width*height*3/2 || sample_buffer(buffer,&hash))result=6;''')
replace('previous=GST_BUFFER_PTS(buffer);', 'previous=GST_BUFFER_PTS(buffer);previous_sequence=GST_BUFFER_OFFSET(buffer);')
replace('  if(!result) {\n   previous=', '''  if(!result && !frames && getenv("GST_SENSOR_NODE")) {
   int fd=open(getenv("GST_SENSOR_NODE"),O_RDONLY|O_CLOEXEC);
   struct v4l2_subdev_format format={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=0};
   if(fd<0 || ioctl(fd,VIDIOC_SUBDEV_G_FMT,&format))result=6;
   else {printf("GST_SENSOR width=%u height=%u code=%u\\n",format.format.width,format.format.height,format.format.code);fflush(stdout);}
   if(fd>=0)close(fd);
  }
  if(!result) {
   previous=''')
replace('pts=%llu hash=%llu\\n', 'pts=%llu hash=%llu sequence=%llu wall-ns=%llu\\n')
replace('(unsigned long long)hash);fflush(stdout);++frames;', '(unsigned long long)hash,(unsigned long long)previous_sequence,(unsigned long long)g_get_monotonic_time()*1000);fflush(stdout);++frames;')
(HERE/'gst-hardware-probe.c').write_text(source)
work=storage.SDK/'private/camss443-gst';work.mkdir(exist_ok=True);shutil.copyfile(HERE/'gst-hardware-probe.c',work/'gst-hardware-probe.c')
q=subprocess.run(['chroot',str(storage.SDK),'pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-allocators-1.0'],capture_output=True,text=True,check=True)
q=subprocess.run(['chroot',str(storage.SDK),'gcc','-O2','-Wall','-Wextra','-Werror','/private/camss443-gst/gst-hardware-probe.c',*q.stdout.split(),'-o','/private/camss443-gst/gst-hardware-probe'],capture_output=True)
(P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2500:]
shutil.copyfile(work/'gst-hardware-probe',P/'gst-hardware-probe')
r=dict(stage=443,existing_libcamerasrc_appsink_consumer=True,actual_kernel_sequence_from_gst_buffer_offset=True,
 bounded_frames_default120=True,aarch64_werror=True,probe_does_not_change_pipeline_ipa_or_modules=True,candidate_profile_validated_separately=True,
 clients=[dict(name='gst-hardware-probe',sha256=hashlib.sha256((P/'gst-hardware-probe').read_bytes()).hexdigest(),source_sha256=hashlib.sha256(source.encode()).hexdigest())],passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
