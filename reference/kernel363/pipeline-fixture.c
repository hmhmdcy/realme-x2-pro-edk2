/* SPDX-License-Identifier: GPL-2.0-only */
/* Test-only state fixture; the child owns all libcamera streams and buffers. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <glob.h>
#include <linux/media.h>
#include <linux/v4l2-subdev.h>
#include <linux/videodev2.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

struct format_save { int fd; struct v4l2_subdev_format value; };
struct selection_save { int fd; struct v4l2_subdev_selection value; };
struct control_save { int fd; struct v4l2_control value; };
struct video_save { int fd; struct v4l2_format value; };
static struct format_save formats[160];
static struct selection_save selections[128];
static struct control_save controls[128];
static struct video_save videos[32];
static unsigned nf,ns,nc,nv;
static int fds[64];static unsigned nfd;
static struct media_link_desc links[256];static unsigned nl;
static volatile sig_atomic_t interrupted;
static void on_signal(int n) { (void)n; interrupted=1; }
static int call(int fd,unsigned long request,void *arg) {
 int ret;do { ret=ioctl(fd,request,arg); }while(ret<0&&errno==EINTR);return ret;
}
static int device_path(const struct media_entity_desc *e,char *path,size_t size) {
 glob_t names={0};int result=-1;
 if(glob("/dev/v4l-subdev*",0,NULL,&names))return -1;
 for(size_t i=0;i<names.gl_pathc;i++) {struct stat st;
  if(!stat(names.gl_pathv[i],&st)&&S_ISCHR(st.st_mode)&&major(st.st_rdev)==e->dev.major&&minor(st.st_rdev)==e->dev.minor) {
   if(snprintf(path,size,"%s",names.gl_pathv[i])<(int)size)result=0;break;
  }
 }
 globfree(&names);return result;
}
static int snapshot_entity(const struct media_entity_desc *e) {
 char path[128];if(device_path(e,path,sizeof(path)))return 0;
 if(nfd==64)return -1;
 int fd=open(path,O_RDWR|O_CLOEXEC);if(fd<0)return -1;fds[nfd++]=fd;
 for(unsigned pad=0;pad<e->pads;pad++) {
  struct v4l2_subdev_format f={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=pad};
  if(!call(fd,VIDIOC_SUBDEV_G_FMT,&f)) {if(nf==160)return -1;formats[nf++]=(struct format_save){fd,f};}
  else if(errno!=EINVAL&&errno!=ENOTTY)return -1;
  unsigned targets[]={V4L2_SEL_TGT_CROP,V4L2_SEL_TGT_COMPOSE};
  for(unsigned i=0;i<2;i++) {
   struct v4l2_subdev_selection s={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=pad,.target=targets[i]};
   if(!call(fd,VIDIOC_SUBDEV_G_SELECTION,&s)) {if(ns==128)return -1;selections[ns++]=(struct selection_save){fd,s};}
   else if(errno!=EINVAL&&errno!=ENOTTY)return -1;
  }
 }
 unsigned ids[]={V4L2_CID_FOCUS_ABSOLUTE,V4L2_CID_TEST_PATTERN,V4L2_CID_EXPOSURE,V4L2_CID_ANALOGUE_GAIN,V4L2_CID_HFLIP,V4L2_CID_VFLIP};
 for(unsigned i=0;i<sizeof(ids)/sizeof(ids[0]);i++) {
  struct v4l2_control c={.id=ids[i]};
  if(!call(fd,VIDIOC_G_CTRL,&c)) {if(nc==128||(c.id==V4L2_CID_TEST_PATTERN&&c.value))return -1;controls[nc++]=(struct control_save){fd,c};}
  else if(errno!=EINVAL&&errno!=ENOTTY)return -1;
 }
 return 0;
}
static int snapshot_videos(void) {
 glob_t names={0};if(glob("/dev/video*",0,NULL,&names))return -1;
 for(size_t i=0;i<names.gl_pathc;i++) {
  int fd=open(names.gl_pathv[i],O_RDWR|O_CLOEXEC);if(fd<0)continue;
  struct v4l2_capability c={0};
  if(call(fd,VIDIOC_QUERYCAP,&c)||strcmp((char *)c.driver,"qcom-camss")||!(c.device_caps&V4L2_CAP_VIDEO_CAPTURE_MPLANE)){close(fd);continue;}
  if(nv==32||nfd==64){close(fd);globfree(&names);return -1;}
  struct v4l2_format f={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE};
  if(call(fd,VIDIOC_G_FMT,&f)){close(fd);globfree(&names);return -1;}
  fds[nfd++]=fd;videos[nv++]=(struct video_save){fd,f};
 }
 globfree(&names);return 0;
}
static int restore(int media) {
 int result=0;
 /* Sink formats first; source-pad formats and selections follow. */
 for(unsigned pass=0;pass<2;pass++)for(unsigned i=0;i<nf;i++) {
  if((formats[i].value.pad==0)!=(pass==0))continue;
  struct v4l2_subdev_format current={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=formats[i].value.pad};
  if(call(formats[i].fd,VIDIOC_SUBDEV_G_FMT,&current)){result=1;continue;}
  if(memcmp(&current.format,&formats[i].value.format,sizeof(current.format))) {
   struct v4l2_subdev_format f=formats[i].value;
   if(call(formats[i].fd,VIDIOC_SUBDEV_S_FMT,&f)){perror("fixture restore format");result=1;}
  }
 }
 for(unsigned i=0;i<ns;i++) {
  struct v4l2_subdev_selection s=selections[i].value;
  struct v4l2_subdev_selection current=s;
  if(call(selections[i].fd,VIDIOC_SUBDEV_G_SELECTION,&current)){result=1;continue;}
  if(!memcmp(&current.r,&s.r,sizeof(s.r)))continue;
  if(call(selections[i].fd,VIDIOC_SUBDEV_S_SELECTION,&s)){perror("fixture restore selection");result=1;}
 }
 for(unsigned i=0;i<nc;i++) {
  struct v4l2_control c=controls[i].value;
  struct v4l2_control current={.id=c.id};
  if(call(controls[i].fd,VIDIOC_G_CTRL,&current)){result=1;continue;}
  if(current.value==c.value)continue;
  if(call(controls[i].fd,VIDIOC_S_CTRL,&c)){perror("fixture restore control");result=1;}
 }
 for(unsigned i=0;i<nv;i++) {
  struct v4l2_format f=videos[i].value;
  struct v4l2_format current={.type=f.type};
  if(call(videos[i].fd,VIDIOC_G_FMT,&current)){result=1;continue;}
  if(!memcmp(&current.fmt.pix_mp,&f.fmt.pix_mp,sizeof(f.fmt.pix_mp)))continue;
  if(call(videos[i].fd,VIDIOC_S_FMT,&f)){perror("fixture restore video");result=1;}
 }
 /* An interrupted app may leave a competing input enabled. Remove it first. */
 for(unsigned pass=0;pass<2;pass++)for(unsigned i=0;i<nl;i++)if(!(links[i].flags&MEDIA_LNK_FL_IMMUTABLE)) {
  bool enabled=!!(links[i].flags&MEDIA_LNK_FL_ENABLED);
  if(enabled!=(pass==1))continue;
  struct media_link_desc l=links[i];
  if(call(media,MEDIA_IOC_SETUP_LINK,&l)){perror("fixture restore link");result=1;}
 }
 for(unsigned i=0;i<nf;i++) {
  struct v4l2_subdev_format f={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=formats[i].value.pad};
  if(call(formats[i].fd,VIDIOC_SUBDEV_G_FMT,&f)||memcmp(&f.format,&formats[i].value.format,sizeof(f.format)))result=1;
 }
 for(unsigned i=0;i<ns;i++) {
  struct v4l2_subdev_selection s=selections[i].value;
  if(call(selections[i].fd,VIDIOC_SUBDEV_G_SELECTION,&s)||memcmp(&s.r,&selections[i].value.r,sizeof(s.r)))result=1;
 }
 for(unsigned i=0;i<nc;i++) {
  struct v4l2_control c={.id=controls[i].value.id};
  if(call(controls[i].fd,VIDIOC_G_CTRL,&c)||c.value!=controls[i].value.value)result=1;
 }
 for(unsigned i=0;i<nv;i++) {
  struct v4l2_format f={.type=videos[i].value.type};
  if(call(videos[i].fd,VIDIOC_G_FMT,&f)||memcmp(&f.fmt.pix_mp,&videos[i].value.fmt.pix_mp,sizeof(f.fmt.pix_mp)))result=1;
 }
 return result;
}
int main(int argc,char **argv) {
 if(argc<3)return 2;
 struct utsname id;if(uname(&id)||strcmp(id.release,"7.3.0-rc6-rmx1931-samurai-k363+")||strncmp(id.version,"#363 ",5))return 3;
 signal(SIGINT,on_signal);signal(SIGTERM,on_signal);
 int media=open(argv[1],O_RDWR|O_CLOEXEC),result=1;bool saved=false;
 if(media<0)return 4;
 struct media_device_info info={0};
 if(call(media,MEDIA_IOC_DEVICE_INFO,&info)||strcmp(info.driver,"qcom-camss"))goto done;
 struct media_entity_desc e={.id=MEDIA_ENT_ID_FLAG_NEXT};
 while(!call(media,MEDIA_IOC_ENUM_ENTITIES,&e)) {
  if(e.pads>64||e.links>128)goto done;
  struct media_pad_desc pads[64]={0};struct media_link_desc edges[128]={0};
  struct media_links_enum en={.entity=e.id,.pads=pads,.links=edges};
  if(call(media,MEDIA_IOC_ENUM_LINKS,&en)||snapshot_entity(&e))goto done;
  for(unsigned i=0;i<e.links;i++)if(edges[i].source.entity==e.id) {
   if(nl==256)goto done;links[nl++]=edges[i];
  }
  e.id|=MEDIA_ENT_ID_FLAG_NEXT;
 }
 if(errno!=EINVAL||snapshot_videos())goto done;
 saved=true;fflush(NULL);
 pid_t child=fork();if(child<0)goto done;
 if(!child){setpgid(0,0);execv(argv[2],argv+2);_exit(127);}
 setpgid(child,child);
 int status=0;time_t start=time(NULL);bool signalled=false;
 for(;;) {
  pid_t ret=waitpid(child,&status,WNOHANG);
  if(ret==child)break;
  if(ret<0&&errno!=EINTR)goto done;
  if((interrupted||time(NULL)-start>50)&&!signalled){kill(-child,SIGINT);signalled=true;start=time(NULL);}
  if(signalled&&time(NULL)-start>5){kill(-child,SIGKILL);while(waitpid(child,&status,0)<0&&errno==EINTR){}break;}
  usleep(50000);
 }
 printf("FIXTURE_CHILD status=%d exited=%d exit=%d signalled=%d\n",status,WIFEXITED(status),WIFEXITED(status)?WEXITSTATUS(status):-1,WIFSIGNALED(status));
 result=signalled||!WIFEXITED(status)||WEXITSTATUS(status)!=0;
done:
 int restored=saved?restore(media):-1;
 if(restored)result=1;
 printf("FIXTURE_RESTORATION result=%d\n",restored);
 for(unsigned i=0;i<nfd;i++)close(fds[i]);close(media);
 printf("FIXTURE_RESULT result=%d saved=%u formats=%u selections=%u controls=%u videos=%u\n",result,saved,nf,ns,nc,nv);
 return result;
}
