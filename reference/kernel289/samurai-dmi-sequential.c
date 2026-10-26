/* SPDX-License-Identifier: GPL-2.0-only */
/* Bounded SM8150 internal TPG validation through standard media/V4L2 APIs. */
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
static void on_signal(int signal_number) { (void)signal_number; interrupted=1; }
static int call(int fd,unsigned long request,void *argument) {
 int result;do {result=ioctl(fd,request,argument);} while(result<0&&errno==EINTR&&!interrupted);return result;
}
static uint64_t hash(const unsigned char *data,size_t length) {
 uint64_t result=UINT64_C(14695981039346656037);for(size_t i=0;i<length;i++)result=(result^data[i])*UINT64_C(1099511628211);return result;
}
static int device_path(const struct media_entity_desc *entity,bool subdev,char *path,size_t size) {
 glob_t names={0};int result=-1;
 if(glob(subdev?"/dev/v4l-subdev*":"/dev/video*",0,NULL,&names))return -1;
 for(size_t n=0;n<names.gl_pathc;n++){struct stat st;
  if(!stat(names.gl_pathv[n],&st)&&S_ISCHR(st.st_mode)&&major(st.st_rdev)==entity->dev.major&&minor(st.st_rdev)==entity->dev.minor){
   if(snprintf(path,size,"%s",names.gl_pathv[n])<(int)size)result=0;break;
  }
 }
 globfree(&names);return result;
}
static int subformat(int fd,unsigned pad,struct v4l2_subdev_format *saved,bool *saved_valid) {
 *saved=(struct v4l2_subdev_format){.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=pad};
 if(call(fd,VIDIOC_SUBDEV_G_FMT,saved))return -1;
 *saved_valid=true;
 struct v4l2_subdev_format format=*saved;format.format.code=MEDIA_BUS_FMT_SGRBG10_1X10;
 format.format.width=320;format.format.height=240;format.format.field=V4L2_FIELD_NONE;
 if(call(fd,VIDIOC_SUBDEV_S_FMT,&format))return -1;
 if(format.format.code!=MEDIA_BUS_FMT_SGRBG10_1X10||format.format.width!=320||format.format.height!=240){errno=ERANGE;return -1;}return 0;
}
#include "dmi-sequential.h"
int main(int argc,char **argv) {
 if(argc==2&&!strcmp(argv[1],"--self-test")){unsigned char data[4096];memset(data,0xa5,sizeof(data));uint64_t first=hash(data,sizeof(data));data[2048]=0x5a;if(hash(data,sizeof(data))==first)return 1;puts("TPG_HELPER_CONTENT_HASH_SELF_TEST_PASS");return 0;}
 if(argc!=3||strcmp(argv[1],"--capture")){fprintf(stderr,"usage: %s --capture FIRST_FRAME_PATH\n",argv[0]);return 2;}
 struct utsname identity;if(uname(&identity)||strcmp(identity.release,"7.3.0-rc6-rmx1931-samurai-k279candidate+")||strncmp(identity.version,"#288 ",5)){fputs("wrong kernel release\n",stderr);return 3;}
 signal(SIGINT,on_signal);signal(SIGTERM,on_signal);
 int media=-1,csid=-1,vfe=-1,video=-1,result=1;bool streaming=false,control_saved=false,csid_saved=false,vfe_saved=false,format_saved=false;
 struct media_entity_desc entities[128],c={0},v={0},capture={0};unsigned entity_count=0;
 struct media_link_desc changed[128];unsigned changed_count=0;
 struct v4l2_control old_control={.id=V4L2_CID_TEST_PATTERN};struct v4l2_subdev_format old_csid={0},old_vfe={0};struct v4l2_format old_format={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE};
 void *maps[4]={0};size_t sizes[4]={0};unsigned buffers=0;unsigned char fills[4]={0};
 enum v4l2_buf_type type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
 for(unsigned m=0;m<8;m++){
  char path[32];snprintf(path,sizeof(path),"/dev/media%u",m);media=open(path,O_RDWR|O_CLOEXEC);if(media<0)continue;
  struct media_device_info info={0};if(call(media,MEDIA_IOC_DEVICE_INFO,&info)||strcmp(info.model,"Qualcomm Camera Subsystem")){close(media);media=-1;continue;}
  struct media_entity_desc item={.id=MEDIA_ENT_ID_FLAG_NEXT};entity_count=0;
  while(!call(media,MEDIA_IOC_ENUM_ENTITIES,&item)){
   if(entity_count>=128){errno=E2BIG;goto cleanup;}entities[entity_count++]=item;
   if(!strcmp(item.name,"msm_csid0"))c=item;
   if(!strcmp(item.name,"msm_vfe0_pix"))v=item;
   if(!strcmp(item.name,"msm_vfe0_video3"))capture=item;
   item.id|=MEDIA_ENT_ID_FLAG_NEXT;
  }
  if(c.id&&v.id&&capture.id){printf("GRAPH media=%s entities=%u csid=%u vfe=%u video=%u\n",path,entity_count,c.id,v.id,capture.id);break;}
  close(media);media=-1;c=(struct media_entity_desc){0};v=c;capture=c;
 }
 if(media<0){errno=ENODEV;goto cleanup;}
 bool rdi_link=false,video_link=false;struct media_link_desc selected_link={0};
 for(unsigned n=0;n<entity_count;n++){
  const struct media_entity_desc *entity=&entities[n];if(entity->pads>64||entity->links>128){errno=E2BIG;goto cleanup;}
  struct media_pad_desc pads[64]={0};struct media_link_desc links[128]={0};struct media_links_enum enumeration={.entity=entity->id,.pads=pads,.links=links};
  if(call(media,MEDIA_IOC_ENUM_LINKS,&enumeration))goto cleanup;
  for(unsigned j=0;j<entity->links;j++){
   struct media_link_desc link=links[j];if(link.source.entity!=entity->id)continue;
   bool selected=link.source.entity==c.id&&link.source.index==4&&link.sink.entity==v.id&&link.sink.index==0;
   bool physical=(link.sink.entity==c.id&&link.sink.index==0)||(link.source.entity==c.id&&!selected);
   if(link.source.entity==v.id&&link.sink.entity==capture.id){if(!(link.flags&MEDIA_LNK_FL_ENABLED)){errno=ENOLINK;goto cleanup;}video_link=true;}
   if(selected){rdi_link=true;selected_link=link;}
   bool alter=physical&&(link.flags&MEDIA_LNK_FL_ENABLED);
   if(!alter)continue;if(link.flags&MEDIA_LNK_FL_IMMUTABLE||changed_count>=128){errno=EPERM;goto cleanup;}
   changed[changed_count++]=link;if(selected)link.flags|=MEDIA_LNK_FL_ENABLED;else link.flags&=~MEDIA_LNK_FL_ENABLED;
   if(call(media,MEDIA_IOC_SETUP_LINK,&link))goto cleanup;
  }
 }
 if(!rdi_link||!video_link){errno=ENOLINK;goto cleanup;}
 if(!(selected_link.flags&MEDIA_LNK_FL_ENABLED)){
  if(selected_link.flags&MEDIA_LNK_FL_IMMUTABLE||changed_count>=128){errno=EPERM;goto cleanup;}
  changed[changed_count++]=selected_link;selected_link.flags|=MEDIA_LNK_FL_ENABLED;
  if(call(media,MEDIA_IOC_SETUP_LINK,&selected_link))goto cleanup;
 }

 char cp[128],vp[128],device[128];if(device_path(&c,true,cp,sizeof(cp))||device_path(&v,true,vp,sizeof(vp))||device_path(&capture,false,device,sizeof(device))){errno=ENODEV;goto cleanup;}
 csid=open(cp,O_RDWR|O_CLOEXEC);vfe=open(vp,O_RDWR|O_CLOEXEC);if(csid<0||vfe<0)goto cleanup;
 if(call(csid,VIDIOC_G_CTRL,&old_control))goto cleanup;control_saved=true;
 struct v4l2_control control={.id=V4L2_CID_TEST_PATTERN,.value=9};if(call(csid,VIDIOC_S_CTRL,&control))goto cleanup;
 if(subformat(csid,4,&old_csid,&csid_saved))goto cleanup;
 if(subformat(vfe,0,&old_vfe,&vfe_saved))goto cleanup;
 video=open(device,O_RDWR|O_NONBLOCK|O_CLOEXEC);if(video<0)goto cleanup;
 if(call(video,VIDIOC_G_FMT,&old_format))goto cleanup;format_saved=true;
 struct v4l2_format format={.type=type};format.fmt.pix_mp.width=320;format.fmt.pix_mp.height=240;format.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_NV12;format.fmt.pix_mp.field=V4L2_FIELD_NONE;
 if(call(video,VIDIOC_S_FMT,&format))goto cleanup;
 struct v4l2_pix_format_mplane *f=&format.fmt.pix_mp;
 if(f->width!=320||f->height!=240||f->pixelformat!=V4L2_PIX_FMT_NV12||f->num_planes!=1||f->plane_fmt[0].bytesperline<320||f->plane_fmt[0].sizeimage<(size_t)f->plane_fmt[0].bytesperline*360||f->plane_fmt[0].sizeimage>1024*1024){errno=ERANGE;goto cleanup;}
 printf("FORMAT video=%s width=%u height=%u stride=%u sizeimage=%u\n",device,f->width,f->height,f->plane_fmt[0].bytesperline,f->plane_fmt[0].sizeimage);
 struct v4l2_requestbuffers request={.count=3,.type=type,.memory=V4L2_MEMORY_MMAP};if(call(video,VIDIOC_REQBUFS,&request)||request.count<3||request.count>4)goto cleanup;buffers=request.count;
 for(unsigned n=0;n<buffers;n++){
  struct v4l2_plane plane[VIDEO_MAX_PLANES]={0};struct v4l2_buffer buffer={.index=n,.type=type,.memory=V4L2_MEMORY_MMAP,.length=VIDEO_MAX_PLANES,.m.planes=plane};
  if(call(video,VIDIOC_QUERYBUF,&buffer)||buffer.length!=1||plane[0].length<f->plane_fmt[0].sizeimage||plane[0].length>2*1024*1024){errno=ERANGE;goto cleanup;}
  sizes[n]=plane[0].length;maps[n]=mmap(NULL,sizes[n],PROT_READ|PROT_WRITE,MAP_SHARED,video,plane[0].m.mem_offset);if(maps[n]==MAP_FAILED){maps[n]=NULL;goto cleanup;}
  fills[n]=(unsigned char)(0xa5^(n*0x31));memset(maps[n],fills[n],sizes[n]);
  if(call(video,VIDIOC_QBUF,&buffer))goto cleanup;
 }
 if(call(video,VIDIOC_STREAMON,&type))goto cleanup;streaming=true;
 puts("STREAMON_OK");fflush(stdout);


 uint32_t last_sequence=0;int64_t last_time=0;
 for(unsigned frame=0;frame<3;frame++){
  struct pollfd p={.fd=video,.events=POLLIN};int ready=poll(&p,1,5000);if(ready<=0||interrupted||!(p.revents&POLLIN)){errno=ETIMEDOUT;goto cleanup;}
  struct v4l2_plane plane[VIDEO_MAX_PLANES]={0};struct v4l2_buffer buffer={.type=type,.memory=V4L2_MEMORY_MMAP,.length=VIDEO_MAX_PLANES,.m.planes=plane};if(call(video,VIDIOC_DQBUF,&buffer))goto cleanup;
  if(buffer.index>=buffers||buffer.flags&V4L2_BUF_FLAG_ERROR||buffer.length!=1||plane[0].bytesused!=f->plane_fmt[0].sizeimage||plane[0].data_offset||plane[0].bytesused>sizes[buffer.index]){errno=EIO;goto cleanup;}
  unsigned char *data=maps[buffer.index];size_t changed_bytes=0,active_changed=0;
  for(size_t n=0;n<plane[0].bytesused;n++)changed_bytes+=data[n]!=fills[buffer.index];
  for(unsigned y=0;y<360;y++)for(unsigned x=0;x<320;x++)active_changed+=data[(size_t)y*f->plane_fmt[0].bytesperline+x]!=fills[buffer.index];
  size_t luma=(size_t)f->plane_fmt[0].bytesperline*240,y_changed=0,uv_changed=0;
  for(size_t n=0;n<luma;n++)y_changed+=data[n]!=fills[buffer.index];
  for(size_t n=luma;n<plane[0].bytesused;n++)uv_changed+=data[n]!=fills[buffer.index];
  for(size_t n=plane[0].bytesused;n<sizes[buffer.index];n++)if(data[n]!=fills[buffer.index]){errno=EOVERFLOW;goto cleanup;}
  printf("PLANES y_changed=%zu uv_changed=%zu tail_unchanged=%zu\n",y_changed,uv_changed,sizes[buffer.index]-plane[0].bytesused);
  if(y_changed<luma*3/4||uv_changed<(plane[0].bytesused-luma)*3/4){errno=EIO;goto cleanup;}
  int64_t timestamp=(int64_t)buffer.timestamp.tv_sec*1000000+buffer.timestamp.tv_usec;
  printf("FRAME number=%u index=%u sequence=%u bytes=%u changed=%zu active_changed=%zu active_bytes=115200 hash=%016" PRIx64 " timestamp_us=%" PRId64 "\n",frame,buffer.index,buffer.sequence,plane[0].bytesused,changed_bytes,active_changed,hash(data,plane[0].bytesused),timestamp);fflush(stdout);
  if(active_changed<103680||timestamp<=0||(frame&&(buffer.sequence<=last_sequence||timestamp<=last_time))){errno=EIO;goto cleanup;}
  last_sequence=buffer.sequence;last_time=timestamp;
  if(!frame){int output=open(argv[2],O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);if(output<0)goto cleanup;size_t written=0;while(written<plane[0].bytesused){ssize_t step=write(output,data+written,plane[0].bytesused-written);if(step<=0){close(output);goto cleanup;}written+=(size_t)step;}if(fsync(output)||close(output))goto cleanup;}
 }
 if(gamma_readback())goto cleanup;
 result=0;
cleanup:
 if(result)fprintf(stderr,"CAPTURE_FAILURE errno=%d message=%s interrupted=%d\n",errno,strerror(errno),(int)interrupted);
 if(streaming&&call(video,VIDIOC_STREAMOFF,&type)){perror("STREAMOFF");result=1;}
 for(unsigned n=0;n<buffers;n++)if(maps[n])munmap(maps[n],sizes[n]);
 if(video>=0){struct v4l2_requestbuffers release={.count=0,.type=type,.memory=V4L2_MEMORY_MMAP};if(call(video,VIDIOC_REQBUFS,&release)){perror("REQBUFS release");result=1;}if(format_saved&&call(video,VIDIOC_S_FMT,&old_format)){perror("restore video format");result=1;}close(video);}
 if(vfe_saved&&call(vfe,VIDIOC_SUBDEV_S_FMT,&old_vfe)){perror("restore VFE format");result=1;}
 if(csid_saved&&call(csid,VIDIOC_SUBDEV_S_FMT,&old_csid)){perror("restore CSID format");result=1;}
 if(control_saved&&call(csid,VIDIOC_S_CTRL,&old_control)){perror("restore pattern");result=1;}
 while(changed_count){struct media_link_desc *link=&changed[--changed_count];if(call(media,MEDIA_IOC_SETUP_LINK,link)){perror("restore media link");result=1;}}
 if(video>=0)video=-1;if(vfe>=0)close(vfe);if(csid>=0)close(csid);if(media>=0)close(media);
 printf("CAPTURE_RESULT success=%d cleanup_complete=%d\n",!result,!result);return result;
}
