/* SPDX-License-Identifier: GPL-2.0-only */
/* Test-only physical control timing at observed VFE SOFs, standard V4L2 only. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <glob.h>
#include <inttypes.h>
#include <linux/media.h>
#include <linux/v4l2-subdev.h>
#include <linux/videodev2.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/utsname.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t interrupted;
static void stop_signal(int n) { (void)n;interrupted=1; }
static int call(int fd,unsigned long req,void *arg) {
 int ret;do{ret=ioctl(fd,req,arg);}while(ret<0&&errno==EINTR&&!interrupted);return ret;
}
static int64_t ns(void) {struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return -1;return (int64_t)t.tv_sec*1000000000+t.tv_nsec;}
static int path_for(const struct media_entity_desc *e,char *out,size_t size) {
 glob_t names={0};int ret=-1;if(glob("/dev/v4l-subdev*",0,NULL,&names))return -1;
 for(size_t i=0;i<names.gl_pathc;i++){struct stat s;
  if(!stat(names.gl_pathv[i],&s)&&S_ISCHR(s.st_mode)&&major(s.st_rdev)==e->dev.major&&minor(s.st_rdev)==e->dev.minor){
   if(snprintf(out,size,"%s",names.gl_pathv[i])<(int)size)ret=0;break;
  }
 }
 globfree(&names);return ret;
}
struct change {uint32_t sof,id;int32_t value;};
static const struct change changes[]={
 {12,V4L2_CID_EXPOSURE,3000},{36,V4L2_CID_EXPOSURE,500},{60,V4L2_CID_EXPOSURE,3000},
 {84,V4L2_CID_ANALOGUE_GAIN,768},{108,V4L2_CID_ANALOGUE_GAIN,512},
 {132,V4L2_CID_ANALOGUE_GAIN,768},{156,V4L2_CID_ANALOGUE_GAIN,512},
 {180,V4L2_CID_EXPOSURE,1500},{204,V4L2_CID_EXPOSURE,500},
};
int main(int argc,char **argv) {
 if(argc!=2)return 2;
 struct utsname identity;if(uname(&identity)||strcmp(identity.release,"7.3.0-rc6-rmx1931-samurai-k298+")||strncmp(identity.version,"#298 ",5))return 3;
 char *end;long ready=strtol(argv[1],&end,10);if(*end||ready<3||ready>1024)return 2;
 signal(SIGINT,stop_signal);signal(SIGTERM,stop_signal);setvbuf(stdout,NULL,_IOLBF,0);
 int media=open("/dev/media0",O_RDWR|O_CLOEXEC),sensor=-1,pix=-1,result=1;unsigned applied=0,events=0;
 bool initial=false;struct v4l2_control original[2]={{.id=V4L2_CID_EXPOSURE},{.id=V4L2_CID_ANALOGUE_GAIN}};
 if(media<0)goto done;
 struct media_device_info info={0};if(call(media,MEDIA_IOC_DEVICE_INFO,&info)||strcmp(info.driver,"qcom-camss"))goto done;
 struct media_entity_desc s={0},v={0},e={.id=MEDIA_ENT_ID_FLAG_NEXT};
 while(!call(media,MEDIA_IOC_ENUM_ENTITIES,&e)){
  if(!strncmp(e.name,"imx319 ",7))s=e;
  if(!strcmp(e.name,"msm_vfe0_pix"))v=e;
  e.id|=MEDIA_ENT_ID_FLAG_NEXT;
 }
 if(!s.id||!v.id)goto done;
 char sp[128],vp[128];if(path_for(&s,sp,sizeof(sp))||path_for(&v,vp,sizeof(vp)))goto done;
 sensor=open(sp,O_RDWR|O_CLOEXEC);pix=open(vp,O_RDWR|O_CLOEXEC|O_NONBLOCK);if(sensor<0||pix<0)goto done;
 struct v4l2_queryctrl exposure={.id=V4L2_CID_EXPOSURE},gain={.id=V4L2_CID_ANALOGUE_GAIN};
 if(call(sensor,VIDIOC_QUERYCTRL,&exposure)||call(sensor,VIDIOC_QUERYCTRL,&gain)||exposure.minimum>500||exposure.maximum<3000||gain.minimum>512||gain.maximum<768)goto done;
 if(call(sensor,VIDIOC_G_CTRL,&original[0])||call(sensor,VIDIOC_G_CTRL,&original[1]))goto done;
 struct v4l2_control c={.id=V4L2_CID_EXPOSURE,.value=500};if(call(sensor,VIDIOC_S_CTRL,&c))goto done;
 initial=true;c=(struct v4l2_control){.id=V4L2_CID_ANALOGUE_GAIN,.value=512};if(call(sensor,VIDIOC_S_CTRL,&c))goto done;
 struct v4l2_event_subscription subscription={.type=V4L2_EVENT_FRAME_SYNC};if(call(pix,VIDIOC_SUBSCRIBE_EVENT,&subscription))goto done;
 printf("STEPPER_READY pid=%d sensor=%s pix=%s initial_exposure=500 initial_gain_code=512\n",getpid(),s.name,v.name);
 if(write((int)ready,"R",1)!=1)goto done;close((int)ready);ready=-1;
 int64_t deadline=ns()+INT64_C(18000000000);uint32_t previous=0;bool have=false;
 while(!interrupted&&ns()<deadline){
  struct pollfd p={.fd=pix,.events=POLLPRI};int n=poll(&p,1,1000);
  if(n<0&&errno==EINTR)continue;if(n<0)goto done;if(!n)continue;
  struct v4l2_event event={0};if(call(pix,VIDIOC_DQEVENT,&event)){if(errno==EAGAIN)continue;goto done;}
  if(event.type!=V4L2_EVENT_FRAME_SYNC)goto done;
  uint32_t sof=event.u.frame_sync.frame_sequence;int64_t event_ns=(int64_t)event.timestamp.tv_sec*1000000000+event.timestamp.tv_nsec;
  printf("STEPPER_SOF sequence=%u pending=%u event_ns=%" PRId64 " observed_ns=%" PRId64 "\n",sof,event.pending,event_ns,ns());
  if((have&&sof<=previous)||(!have&&sof!=0))goto done;previous=sof;have=true;events++;
  if(sof==0){
   struct v4l2_control x={.id=V4L2_CID_EXPOSURE},g={.id=V4L2_CID_ANALOGUE_GAIN};
   if(call(sensor,VIDIOC_G_CTRL,&x)||call(sensor,VIDIOC_G_CTRL,&g)||x.value!=500||g.value!=512)goto done;
   printf("STEPPER_INITIAL_READBACK exposure=%d gain_code=%d\n",x.value,g.value);
  }
  if(applied<sizeof(changes)/sizeof(changes[0])&&sof>=changes[applied].sof){
   if(sof!=changes[applied].sof||event.pending)goto done;
   const struct change *change=&changes[applied];c=(struct v4l2_control){.id=change->id,.value=change->value};
   int64_t begin=ns();int ret=call(sensor,VIDIOC_S_CTRL,&c),saved=errno;int64_t finish=ns();
   printf("CONTROL_WRITE step=%u sof=%u id=%u value=%d event_ns=%" PRId64 " begin_ns=%" PRId64 " end_ns=%" PRId64 " ret=%d errno=%d\n",applied,sof,c.id,c.value,event_ns,begin,finish,ret,ret?saved:0);
   if(ret)goto done;
   struct v4l2_control readback={.id=c.id};if(call(sensor,VIDIOC_G_CTRL,&readback)||readback.value!=c.value)goto done;
   applied++;
  }
  if(sof>=232){result=applied!=sizeof(changes)/sizeof(changes[0]);break;}
 }
done:
 if(result)fprintf(stderr,"STEPPER_FAILURE errno=%d events=%u applied=%u interrupted=%d\n",errno,events,applied,(int)interrupted);
 /* The outer fixture restores controls after the camera has stopped. */
 if(initial)printf("STEPPER_ORIGINAL exposure=%d gain_code=%d outer_fixture_restores=1\n",original[0].value,original[1].value);
 if(ready>=0)close((int)ready);if(sensor>=0)close(sensor);if(pix>=0)close(pix);if(media>=0)close(media);
 printf("STEPPER_RESULT result=%d events=%u steps=%u\n",result,events,applied);return result;
}
