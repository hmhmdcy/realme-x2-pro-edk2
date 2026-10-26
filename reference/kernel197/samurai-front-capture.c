/* SPDX-License-Identifier: GPL-2.0-only */
/* Three physical IMX471 frames; standard media/V4L2 APIs, no direct MMIO. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <glob.h>
#include <inttypes.h>
#include <linux/media.h>
#include <linux/media-bus-format.h>
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
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/utsname.h>
#include <unistd.h>

static volatile sig_atomic_t interrupted;
static void stop(int n) { (void)n;interrupted=1; }
static int call(int fd,unsigned long request,void *arg) { int r;do {r=ioctl(fd,request,arg);} while(r<0&&errno==EINTR&&!interrupted);return r; }
static uint64_t hash(const unsigned char *p,size_t n) { uint64_t h=UINT64_C(14695981039346656037);for(size_t i=0;i<n;i++)h=(h^p[i])*UINT64_C(1099511628211);return h; }
static int path_for(const struct media_entity_desc *e,bool sub,char *path,size_t size) {
 glob_t g={0};int r=-1;if(glob(sub?"/dev/v4l-subdev*":"/dev/video*",0,NULL,&g))return -1;
 for(size_t i=0;i<g.gl_pathc;i++) { struct stat s;if(!stat(g.gl_pathv[i],&s)&&S_ISCHR(s.st_mode)&&major(s.st_rdev)==e->dev.major&&minor(s.st_rdev)==e->dev.minor) {if(snprintf(path,size,"%s",g.gl_pathv[i])<(int)size)r=0;break;} }
 globfree(&g);return r;
}
static int set_format(int fd,unsigned pad,struct v4l2_subdev_format *saved,bool *valid) {
 *saved=(struct v4l2_subdev_format){.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=pad};if(call(fd,VIDIOC_SUBDEV_G_FMT,saved))return -1;*valid=true;
 struct v4l2_subdev_format f=*saved;f.format.width=1928;f.format.height=1088;f.format.code=MEDIA_BUS_FMT_SRGGB10_1X10;f.format.field=V4L2_FIELD_NONE;
 if(call(fd,VIDIOC_SUBDEV_S_FMT,&f))return -1;
 if(f.format.width!=1928||f.format.height!=1088||f.format.code!=MEDIA_BUS_FMT_SRGGB10_1X10){errno=ERANGE;return -1;}return 0;
}
int main(int argc,char **argv) {
 if(argc==2&&!strcmp(argv[1],"--self-test")){unsigned char a[4096];memset(a,0xa5,sizeof(a));uint64_t h=hash(a,sizeof(a));a[2048]=0x5a;if(hash(a,sizeof(a))==h)return 1;puts("FRONT_CAPTURE_HASH_SELF_TEST_PASS");return 0;}
 if(argc!=3||strcmp(argv[1],"--capture")){fprintf(stderr,"usage: %s --capture FIRST_PRIVATE_RAW_PATH\n",argv[0]);return 2;}
 struct utsname u;if(uname(&u)||strcmp(u.release,"7.3.0-rc6-rmx1931-samurai-k132+")||strncmp(u.version,"#183 ",5)){fputs("wrong kernel\n",stderr);return 3;}
 signal(SIGINT,stop);signal(SIGTERM,stop);
 int media=-1,video=-1,result=1,fd[5]={-1,-1,-1,-1,-1};bool streaming=false,fmt_saved[5]={0},video_saved=false,pattern_saved[2]={0};
 struct media_entity_desc entities[128],found[6]={{0}};unsigned count=0;const char *names[]={"imx471 7-0010","msm_csiphy2","msm_csid0","msm_vfe0_rdi0","msm_vfe0_video0"};
 struct media_link_desc changes[128];unsigned changed=0;struct v4l2_subdev_format oldfmt[5]={{0}};unsigned pads[]={0,0,0,1,0};
 struct v4l2_control old_pattern[2]={{.id=V4L2_CID_TEST_PATTERN},{.id=V4L2_CID_TEST_PATTERN}};struct v4l2_format old_video={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE};
 void *maps[4]={0};size_t sizes[4]={0};unsigned buffers=0;unsigned char fills[4]={0};unsigned char *first=NULL;size_t first_size=0;enum v4l2_buf_type type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
 for(unsigned m=0;m<8;m++) {
  char p[32];snprintf(p,sizeof(p),"/dev/media%u",m);media=open(p,O_RDWR|O_CLOEXEC);if(media<0)continue;
  struct media_device_info info={0};if(call(media,MEDIA_IOC_DEVICE_INFO,&info)||strcmp(info.model,"Qualcomm Camera Subsystem")){close(media);media=-1;continue;}
  struct media_entity_desc e={.id=MEDIA_ENT_ID_FLAG_NEXT};count=0;memset(found,0,sizeof(found));
  while(!call(media,MEDIA_IOC_ENUM_ENTITIES,&e)) {if(count==128){errno=E2BIG;goto cleanup;}entities[count++]=e;for(unsigned i=0;i<5;i++)if(!strcmp(e.name,names[i]))found[i]=e;e.id|=MEDIA_ENT_ID_FLAG_NEXT;}
  if(found[0].id&&found[1].id&&found[2].id&&found[3].id&&found[4].id){printf("GRAPH media=%s entities=%u sensor=%u phy=%u csid=%u vfe=%u video=%u\n",p,count,found[0].id,found[1].id,found[2].id,found[3].id,found[4].id);break;}
  close(media);media=-1;
 }
 if(media<0){errno=ENODEV;goto cleanup;}
 bool have[4]={0};
 for(unsigned n=0;n<count;n++) {
  struct media_pad_desc p[64]={0};struct media_link_desc links[128]={0};if(entities[n].pads>64||entities[n].links>128){errno=E2BIG;goto cleanup;}
  struct media_links_enum e={.entity=entities[n].id,.pads=p,.links=links};if(call(media,MEDIA_IOC_ENUM_LINKS,&e))goto cleanup;
  for(unsigned j=0;j<entities[n].links;j++) {
   struct media_link_desc l=links[j];if(l.source.entity!=entities[n].id)continue;
   bool a=l.source.entity==found[0].id&&l.sink.entity==found[1].id;
   bool b=l.source.entity==found[1].id&&l.source.index==1&&l.sink.entity==found[2].id&&l.sink.index==0;
   bool c=l.source.entity==found[2].id&&l.source.index==1&&l.sink.entity==found[3].id&&l.sink.index==0;
   bool d=l.source.entity==found[3].id&&l.sink.entity==found[4].id;
   if(a)have[0]=true;if(b)have[1]=true;if(c)have[2]=true;if(d)have[3]=true;
   bool selected=a||b||c||d;bool conflicting=(l.sink.entity==found[2].id&&l.sink.index==0)||(l.sink.entity==found[3].id&&l.sink.index==0);
   bool alter=(selected&&!(l.flags&MEDIA_LNK_FL_ENABLED))||(!selected&&conflicting&&(l.flags&MEDIA_LNK_FL_ENABLED));
   if(!alter)continue;if((l.flags&MEDIA_LNK_FL_IMMUTABLE)||changed==128){errno=EPERM;goto cleanup;}changes[changed++]=l;
   if(selected)l.flags|=MEDIA_LNK_FL_ENABLED;else l.flags&=~MEDIA_LNK_FL_ENABLED;if(call(media,MEDIA_IOC_SETUP_LINK,&l))goto cleanup;
  }
 }
 if(!have[0]||!have[1]||!have[2]||!have[3]){errno=ENOLINK;goto cleanup;}
 int ent_for_fd[]={0,1,2,2,3};
 for(unsigned i=0;i<5;i++){char p[128];if(path_for(&found[ent_for_fd[i]],true,p,sizeof(p))){errno=ENODEV;goto cleanup;}fd[i]=open(p,O_RDWR|O_CLOEXEC);if(fd[i]<0)goto cleanup;}
 for(unsigned i=0;i<2;i++) {int f=fd[i==0?0:2];if(call(f,VIDIOC_G_CTRL,&old_pattern[i]))goto cleanup;pattern_saved[i]=true;struct v4l2_control c={.id=V4L2_CID_TEST_PATTERN,.value=0};if(call(f,VIDIOC_S_CTRL,&c)||call(f,VIDIOC_G_CTRL,&c)||c.value){errno=EIO;goto cleanup;}}
 puts("PATTERNS sensor=0 csid=0 physical_link=enabled");
 for(unsigned i=0;i<5;i++)if(set_format(fd[i],pads[i],&oldfmt[i],&fmt_saved[i]))goto cleanup;
 char path[128];if(path_for(&found[4],false,path,sizeof(path))){errno=ENODEV;goto cleanup;}video=open(path,O_RDWR|O_NONBLOCK|O_CLOEXEC);if(video<0)goto cleanup;
 if(call(video,VIDIOC_G_FMT,&old_video))goto cleanup;video_saved=true;struct v4l2_format fmt={.type=type};fmt.fmt.pix_mp.width=1928;fmt.fmt.pix_mp.height=1088;fmt.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_SRGGB10P;fmt.fmt.pix_mp.field=V4L2_FIELD_NONE;
 if(call(video,VIDIOC_S_FMT,&fmt))goto cleanup;struct v4l2_pix_format_mplane *f=&fmt.fmt.pix_mp;
 if(f->width!=1928||f->height!=1088||f->pixelformat!=V4L2_PIX_FMT_SRGGB10P||f->num_planes!=1||f->plane_fmt[0].bytesperline<2410||f->plane_fmt[0].sizeimage<(size_t)f->plane_fmt[0].bytesperline*1088||f->plane_fmt[0].sizeimage>16*1024*1024){errno=ERANGE;goto cleanup;}
 printf("FORMAT video=%s width=1928 height=1088 stride=%u sizeimage=%u\n",path,f->plane_fmt[0].bytesperline,f->plane_fmt[0].sizeimage);fflush(stdout);
 struct v4l2_requestbuffers req={.count=4,.type=type,.memory=V4L2_MEMORY_MMAP};if(call(video,VIDIOC_REQBUFS,&req)||req.count<3||req.count>4)goto cleanup;buffers=req.count;
 for(unsigned i=0;i<buffers;i++) {struct v4l2_plane p[VIDEO_MAX_PLANES]={0};struct v4l2_buffer b={.index=i,.type=type,.memory=V4L2_MEMORY_MMAP,.length=VIDEO_MAX_PLANES,.m.planes=p};
  if(call(video,VIDIOC_QUERYBUF,&b)||b.length!=1||p[0].length<f->plane_fmt[0].sizeimage||p[0].length>32*1024*1024){errno=ERANGE;goto cleanup;}sizes[i]=p[0].length;maps[i]=mmap(NULL,sizes[i],PROT_READ|PROT_WRITE,MAP_SHARED,video,p[0].m.mem_offset);if(maps[i]==MAP_FAILED){maps[i]=NULL;goto cleanup;}fills[i]=(unsigned char)(0xa5^(i*0x31));memset(maps[i],fills[i],sizes[i]);if(call(video,VIDIOC_QBUF,&b))goto cleanup;
 }
 if(call(video,VIDIOC_STREAMON,&type))goto cleanup;streaming=true;uint32_t previous_sequence=0;int64_t previous_time=0;
 for(unsigned i=0;i<3;i++) {struct pollfd p={.fd=video,.events=POLLIN};int ready=poll(&p,1,5000);if(ready<=0||interrupted||!(p.revents&POLLIN)){errno=ETIMEDOUT;goto cleanup;}
  struct v4l2_plane pl[VIDEO_MAX_PLANES]={0};struct v4l2_buffer b={.type=type,.memory=V4L2_MEMORY_MMAP,.length=VIDEO_MAX_PLANES,.m.planes=pl};if(call(video,VIDIOC_DQBUF,&b))goto cleanup;
  if(b.index>=buffers||b.flags&V4L2_BUF_FLAG_ERROR||b.length!=1||pl[0].bytesused!=f->plane_fmt[0].sizeimage||pl[0].data_offset||pl[0].bytesused>sizes[b.index]){errno=EIO;goto cleanup;}
  unsigned char *data=maps[b.index];size_t active_changed=0;for(unsigned y=0;y<1088;y++)for(unsigned x=0;x<2410;x++)active_changed+=data[(size_t)y*f->plane_fmt[0].bytesperline+x]!=fills[b.index];
  int64_t stamp=(int64_t)b.timestamp.tv_sec*1000000+b.timestamp.tv_usec;printf("FRAME number=%u index=%u sequence=%u bytes=%u changed=%zu active_bytes=2622080 hash=%016" PRIx64 " timestamp_us=%" PRId64 "\n",i,b.index,b.sequence,pl[0].bytesused,active_changed,hash(data,pl[0].bytesused),stamp);fflush(stdout);
  if(active_changed<2359872||stamp<=0||(i&&(b.sequence<=previous_sequence||stamp<=previous_time))){errno=EIO;goto cleanup;}previous_sequence=b.sequence;previous_time=stamp;
  if(!i){first_size=pl[0].bytesused;first=malloc(first_size);if(!first)goto cleanup;memcpy(first,data,first_size);}
  if(i<2){memset(data,fills[b.index],sizes[b.index]);if(call(video,VIDIOC_QBUF,&b))goto cleanup;}
 }
 result=0;
cleanup:
 if(result)fprintf(stderr,"CAPTURE_FAILURE errno=%d message=%s interrupted=%d\n",errno,strerror(errno),(int)interrupted);
 if(streaming&&call(video,VIDIOC_STREAMOFF,&type)){perror("STREAMOFF");result=1;}
 for(unsigned i=0;i<buffers;i++)if(maps[i])munmap(maps[i],sizes[i]);
 if(video>=0){struct v4l2_requestbuffers r={.count=0,.type=type,.memory=V4L2_MEMORY_MMAP};if(call(video,VIDIOC_REQBUFS,&r)){perror("release buffers");result=1;}if(video_saved&&call(video,VIDIOC_S_FMT,&old_video)){perror("restore video format");result=1;}close(video);}
 for(int i=4;i>=0;i--)if(fmt_saved[i]&&call(fd[i],VIDIOC_SUBDEV_S_FMT,&oldfmt[i])){perror("restore subdev format");result=1;}
 for(unsigned i=0;i<2;i++)if(pattern_saved[i]&&call(fd[i==0?0:2],VIDIOC_S_CTRL,&old_pattern[i])){perror("restore pattern");result=1;}
 while(changed){struct media_link_desc *l=&changes[--changed];if(call(media,MEDIA_IOC_SETUP_LINK,l)){perror("restore link");result=1;}}
 for(unsigned i=0;i<5;i++)if(fd[i]>=0)close(fd[i]);if(media>=0)close(media);
 if(!result&&first){int output=open(argv[2],O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);if(output<0)result=1;else {size_t written=0;while(written<first_size){ssize_t n=write(output,first+written,first_size-written);if(n<=0){result=1;break;}written+=(size_t)n;}if(fsync(output)||close(output))result=1;}}
 free(first);printf("CAPTURE_RESULT success=%d cleanup_complete=%d\n",!result,!result);return result;
}
