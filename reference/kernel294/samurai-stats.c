/* SPDX-License-Identifier: GPL-2.0-only */
/* Bounded SM8150 internal TPG validation through standard media/V4L2 APIs. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <glob.h>
#include <inttypes.h>
#include <linux/media.h>
#include <linux/qcom-camss-config.h>
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
 int result;do {result=ioctl(fd,request,argument);} while(result<0&&errno==EINTR&&!interrupted);if(result<0)fprintf(stderr,"IOCTL_FAILURE fd=%d request=%#lx errno=%d\n",fd,request,errno);return result;
}
static unsigned char prefill(unsigned char seed,size_t offset) {
 return seed^(unsigned char)(offset*197u+(offset>>8)*31u);
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


static int params_fd=-1;static void *params_map;static size_t params_size;static bool params_streaming;
static enum v4l2_buf_type params_type=V4L2_BUF_TYPE_META_OUTPUT;
struct params_envelope {uint32_t version,data_size;};
_Static_assert(sizeof(struct params_envelope)==sizeof(struct v4l2_isp_buffer),"ISP envelope ABI");
static size_t make_packet(void *memory,unsigned int phase) {
 struct camss_params_wb_gain wb={.header={CAMSS_PARAMS_WB_GAIN,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(wb)},.g_gain=1024,.b_gain=1024,.r_gain=1024};
 if(phase==1||phase==5||phase==6)wb.r_gain=256;
 if(phase==2)wb.b_gain=256;if(phase==3)wb.g_gain=256;
 if(phase==5)wb.header.flags=0;
 if(phase==4){wb.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;wb.header.size=sizeof(wb.header);}
 struct camss_params_aec_bhist bh={.header={CAMSS_PARAMS_AEC_BHIST,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(bh)},.width=2104,.height=1560};
 if(phase==1)bh.width=1052;
 if(phase==2){bh.left=1052;bh.width=1052;}
 if(phase==3){bh.width=4;bh.height=2;}
 if(phase==5){bh.left=4000;bh.top=4000;bh.width=8192;bh.height=16384;}
 struct params_envelope envelope={V4L2_ISP_VERSION_V1,wb.header.size+sizeof(bh)};
 memset(memory,0,params_size);memcpy(memory,&envelope,sizeof(envelope));memcpy((char*)memory+sizeof(envelope),&wb,wb.header.size);
 memcpy((char*)memory+sizeof(envelope)+wb.header.size,&bh,sizeof(bh));
 return sizeof(envelope)+envelope.data_size;
}
static int queue_params(unsigned int phase,bool corrupt_after) {
 size_t size=make_packet(params_map,phase);
 struct v4l2_buffer b={.index=0,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP,.bytesused=size};
 if(call(params_fd,VIDIOC_QBUF,&b))return -1;
 /* What was validated and queued must be independent of later userspace writes. */
 if(corrupt_after)memset((char*)params_map+sizeof(struct params_envelope)+sizeof(struct v4l2_isp_block_header),0,params_size-sizeof(struct params_envelope)-sizeof(struct v4l2_isp_block_header));
 printf("PARAM_Q phase=%u bytes=%zu mutate_after_qbuf=%u\n",phase,size,corrupt_after);fflush(stdout);return 0;
}
static int dequeue_params(unsigned int phase) {
 struct pollfd p={.fd=params_fd,.events=POLLOUT};int ready=poll(&p,1,3000);
 if(ready<=0||!(p.revents&POLLOUT)){errno=ETIMEDOUT;return -1;}
 struct v4l2_buffer b={.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP};
 if(call(params_fd,VIDIOC_DQBUF,&b))return -1;
 if(b.index||b.flags&V4L2_BUF_FLAG_ERROR){errno=EIO;return -1;}
 printf("PARAM_DQ phase=%u sequence=%u bytes=%u timestamp_us=%" PRId64 "\n",phase,b.sequence,b.bytesused,(int64_t)b.timestamp.tv_sec*1000000+b.timestamp.tv_usec);fflush(stdout);return 0;
}
static int reject_invalid_params(void) {
 for(unsigned int test=0;test<10;test++){
  size_t size=make_packet(params_map,0);struct params_envelope *e=params_map;
  struct camss_params_wb_gain *w=(void*)((char*)params_map+sizeof(*e));
  switch(test){case 0:e->version=99;break;case 1:e->data_size++;break;case 2:w->header.type=CAMSS_PARAMS_GAMMA;break;case 3:w->header.flags=3;break;case 4:w->g_gain=32768;break;case 5:w->r_sub=1;break;case 6:w->_pad[0]=1;break;case 7:w->header.size=sizeof(w->header);break;case 8:size=sizeof(*e)-1;break;case 9:w->header.flags=4;break;}
  struct v4l2_buffer b={.index=0,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP,.bytesused=size};
  errno=0;if(!call(params_fd,VIDIOC_QBUF,&b)||errno!=EINVAL){fprintf(stderr,"INVALID_PARAM_UNEXPECTED test=%u errno=%d\n",test,errno);errno=EPROTO;return -1;}
  printf("PARAM_REJECT test=%u errno=%d\n",test,errno);
 }return 0;
}
static int open_params(const struct media_entity_desc *entity) {
 char path[128];if(device_path(entity,false,path,sizeof(path)))return -1;
 params_fd=open(path,O_RDWR|O_NONBLOCK|O_CLOEXEC);if(params_fd<0)return -1;
 struct v4l2_capability caps={0};if(call(params_fd,VIDIOC_QUERYCAP,&caps))return -1;
 if(!(caps.device_caps&V4L2_CAP_META_OUTPUT)){errno=ENOTTY;return -1;}
 struct v4l2_format f={.type=V4L2_BUF_TYPE_META_OUTPUT};if(call(params_fd,VIDIOC_G_FMT,&f))return -1;
 if(f.fmt.meta.dataformat!=V4L2_META_FMT_QCOM_ISP_PARAMS||f.fmt.meta.buffersize<sizeof(struct params_envelope)+sizeof(struct camss_params_wb_gain)||f.fmt.meta.buffersize>4096){errno=ERANGE;return -1;}
 struct v4l2_requestbuffers r={.count=1,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP};if(call(params_fd,VIDIOC_REQBUFS,&r)||r.count!=1)return -1;
 struct v4l2_buffer b={.index=0,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP};if(call(params_fd,VIDIOC_QUERYBUF,&b)||b.length<f.fmt.meta.buffersize||b.length>65536)return -1;
 params_size=b.length;params_map=mmap(NULL,params_size,PROT_READ|PROT_WRITE,MAP_SHARED,params_fd,b.m.offset);if(params_map==MAP_FAILED){params_map=NULL;return -1;}
 printf("PARAM_NODE path=%s capacity=%u map_size=%zu\n",path,f.fmt.meta.buffersize,params_size);
 if(reject_invalid_params()||queue_params(0,true)||call(params_fd,VIDIOC_STREAMON,&params_type))return -1;params_streaming=true;return 0;
}


static int stats_fd=-1;static void *stats_maps[3];static size_t stats_sizes[3];
static bool stats_streaming;static unsigned stats_buffers;
static enum v4l2_buf_type stats_type=V4L2_BUF_TYPE_META_CAPTURE;
static int stats_queue(unsigned index) {
 memset(stats_maps[index],0xa5,stats_sizes[index]);
 struct v4l2_buffer b={.index=index,.type=V4L2_BUF_TYPE_META_CAPTURE,.memory=V4L2_MEMORY_MMAP};
 return call(stats_fd,VIDIOC_QBUF,&b);
}
static int stats_start(void) {
 for(unsigned i=0;i<stats_buffers;i++)if(stats_queue(i))return -1;
 if(call(stats_fd,VIDIOC_STREAMON,&stats_type))return -1;
 stats_streaming=true;return 0;
}
static int stats_open(const struct media_entity_desc *entity) {
 char path[128];if(device_path(entity,false,path,sizeof(path)))return -1;
 stats_fd=open(path,O_RDWR|O_NONBLOCK|O_CLOEXEC);if(stats_fd<0)return -1;
 struct v4l2_capability c={0};if(call(stats_fd,VIDIOC_QUERYCAP,&c)||!(c.device_caps&V4L2_CAP_META_CAPTURE))return -1;
 struct v4l2_format f={.type=V4L2_BUF_TYPE_META_CAPTURE};if(call(stats_fd,VIDIOC_G_FMT,&f))return -1;
 if(f.fmt.meta.dataformat!=V4L2_META_FMT_QCOM_ISP_STATS||f.fmt.meta.buffersize!=sizeof(struct params_envelope)+sizeof(struct camss_stats_bhist)){errno=ERANGE;return -1;}
 struct v4l2_requestbuffers r={.count=3,.type=V4L2_BUF_TYPE_META_CAPTURE,.memory=V4L2_MEMORY_MMAP};
 if(call(stats_fd,VIDIOC_REQBUFS,&r)||r.count!=3)return -1;stats_buffers=r.count;
 for(unsigned i=0;i<stats_buffers;i++){
  struct v4l2_buffer b={.index=i,.type=V4L2_BUF_TYPE_META_CAPTURE,.memory=V4L2_MEMORY_MMAP};
  if(call(stats_fd,VIDIOC_QUERYBUF,&b)||b.length<f.fmt.meta.buffersize||b.length>65536)return -1;
  stats_sizes[i]=b.length;stats_maps[i]=mmap(NULL,b.length,PROT_READ|PROT_WRITE,MAP_SHARED,stats_fd,b.m.offset);
  if(stats_maps[i]==MAP_FAILED){stats_maps[i]=NULL;return -1;}
 }
 printf("STATS_NODE path=%s capacity=%u buffers=%u\n",path,f.fmt.meta.buffersize,stats_buffers);
 return stats_start();
}
static int stats_dequeue(unsigned frame,const char *prefix) {
 struct pollfd p={.fd=stats_fd,.events=POLLIN};int ready=poll(&p,1,3000);
 if(ready<=0||!(p.revents&POLLIN)){errno=ETIMEDOUT;return -1;}
 struct v4l2_buffer b={.type=V4L2_BUF_TYPE_META_CAPTURE,.memory=V4L2_MEMORY_MMAP};
 if(call(stats_fd,VIDIOC_DQBUF,&b))return -1;
 if(b.index>=stats_buffers||b.flags&V4L2_BUF_FLAG_ERROR||b.bytesused!=sizeof(struct params_envelope)+sizeof(struct camss_stats_bhist)){errno=EPROTO;return -1;}
 const unsigned char *data=stats_maps[b.index];const struct params_envelope *e=(void*)data;
 const struct camss_stats_bhist *h=(void*)(data+sizeof(*e));
 if(e->version!=V4L2_ISP_VERSION_V1||e->data_size!=sizeof(*h)||h->header.type!=CAMSS_STATS_AEC_BHIST||h->header.flags||h->header.size!=sizeof(*h)){errno=EPROTO;return -1;}
 for(size_t i=b.bytesused;i<stats_sizes[b.index];i++)if(data[i]!=0xa5){errno=EOVERFLOW;return -1;}
 uint64_t sum=0,weighted=0;unsigned nonzero=0,peak=0;
 for(unsigned i=0;i<CAMSS_STATS_BHIST_BINS;i++){sum+=h->bins[i];weighted+=(uint64_t)i*h->bins[i];nonzero+=h->bins[i]!=0;if(h->bins[i]>h->bins[peak])peak=i;}
 printf("STATS frame=%u phase=%u index=%u sequence=%u bytes=%u sum=%" PRIu64 " weighted=%" PRIu64 " nonzero=%u peak=%u peak_count=%u hash=%016" PRIx64 " timestamp_us=%" PRId64 "\n",frame,frame/9,b.index,b.sequence,b.bytesused,sum,weighted,nonzero,peak,h->bins[peak],hash(data,b.bytesused),(int64_t)b.timestamp.tv_sec*1000000+b.timestamp.tv_usec);fflush(stdout);
 if(frame%9==8){
  char path[1024];if(snprintf(path,sizeof(path),"%s-%u.qcst",prefix,frame)>=(int)sizeof(path)){errno=ENAMETOOLONG;return -1;}
  int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);if(fd<0)return -1;
  ssize_t count=write(fd,data,b.bytesused);int saved=errno;int closed=close(fd);if(count!=(ssize_t)b.bytesused||closed){errno=saved;return -1;}
 }
 return stats_queue(b.index);
}
static int stats_drain_stopped(void) {
 for(;;){
  struct v4l2_buffer b={.type=V4L2_BUF_TYPE_META_CAPTURE,.memory=V4L2_MEMORY_MMAP};
  if(ioctl(stats_fd,VIDIOC_DQBUF,&b)){if(errno==EAGAIN)return 0;return -1;}
  if(b.index>=stats_buffers||b.flags&V4L2_BUF_FLAG_ERROR){errno=EIO;return -1;}
  if(stats_queue(b.index))return -1;
 }
}
static int stats_close(void) {
 int result=0;
 if(stats_streaming&&call(stats_fd,VIDIOC_STREAMOFF,&stats_type))result=-1;stats_streaming=false;
 for(unsigned i=0;i<stats_buffers;i++)if(stats_maps[i])munmap(stats_maps[i],stats_sizes[i]);
 if(stats_fd>=0){struct v4l2_requestbuffers r={.count=0,.type=V4L2_BUF_TYPE_META_CAPTURE,.memory=V4L2_MEMORY_MMAP};if(call(stats_fd,VIDIOC_REQBUFS,&r))result=-1;close(stats_fd);}
 return result;
}

struct format_save {int fd;struct v4l2_subdev_format value;};
static struct format_save formats[16];static unsigned format_count;
static int save_formats(int fd,unsigned pads) {
 for(unsigned pad=0;pad<pads;pad++){
  if(format_count==16){errno=E2BIG;return -1;}
  struct format_save *s=&formats[format_count];s->fd=fd;
  s->value=(struct v4l2_subdev_format){.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=pad};
  if(call(fd,VIDIOC_SUBDEV_G_FMT,&s->value))return -1;format_count++;
 }return 0;
}
static int set_input(int fd,const struct v4l2_mbus_framefmt *value) {
 struct v4l2_subdev_format f={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=0,.format=*value};
 if(call(fd,VIDIOC_SUBDEV_S_FMT,&f))return -1;
 if(f.format.code!=value->code||f.format.width!=value->width||f.format.height!=value->height){errno=ERANGE;return -1;}
 return 0;
}
static int change_link(int media,struct media_link_desc link,bool enabled,
                      struct media_link_desc *changed,unsigned *count) {
 if(!!(link.flags&MEDIA_LNK_FL_ENABLED)==enabled)return 0;
 if(link.flags&MEDIA_LNK_FL_IMMUTABLE||*count==128){errno=EPERM;return -1;}
 changed[(*count)++]=link;
 if(enabled)link.flags|=MEDIA_LNK_FL_ENABLED;else link.flags&=~MEDIA_LNK_FL_ENABLED;
 return call(media,MEDIA_IOC_SETUP_LINK,&link);
}
int main(int argc,char **argv) {
 if(argc==2&&!strcmp(argv[1],"--self-test")){unsigned char d[4096];memset(d,0xa5,sizeof(d));uint64_t h=hash(d,sizeof(d));d[2048]^=0xff;return hash(d,sizeof(d))==h;}
 if(argc!=3||strcmp(argv[1],"--pattern")){fprintf(stderr,"usage: %s --capture PRIVATE_OUTPUT_PREFIX\n",argv[0]);return 2;}
 struct utsname identity;if(uname(&identity)||strcmp(identity.release,"7.3.0-rc6-rmx1931-samurai-k294+")||strncmp(identity.version,"#294 ",5)){fputs("wrong kernel release\n",stderr);return 3;}
 signal(SIGINT,on_signal);signal(SIGTERM,on_signal);
 int media=-1,csid=-1,vfe=-1,video=-1,sensor=-1,phy=-1,result=1;bool streaming=false,format_saved=false;
 bool settings_changed=false;unsigned controls_saved=0,selections_saved=0;
 struct media_entity_desc entities[128],c={0},v={0},capture={0},s={0},p={0},parameters={0},statistics={0};unsigned entity_count=0;
 struct media_link_desc all_links[256],changed[128];unsigned link_count=0,changed_count=0;
 struct v4l2_control controls[4]={{.id=V4L2_CID_TEST_PATTERN},{.id=V4L2_CID_EXPOSURE},{.id=V4L2_CID_ANALOGUE_GAIN},{.id=V4L2_CID_TEST_PATTERN}};
 struct v4l2_subdev_selection selections[2]={{.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=0,.target=V4L2_SEL_TGT_COMPOSE},{.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=1,.target=V4L2_SEL_TGT_CROP}};
 struct v4l2_format old_format={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE};
 void *maps[4]={0};size_t sizes[4]={0};unsigned buffers=0;unsigned char fills[4]={0};
 enum v4l2_buf_type type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
 const char *phase="discover";
 for(unsigned m=0;m<8;m++){
  char path[32];snprintf(path,sizeof(path),"/dev/media%u",m);media=open(path,O_RDWR|O_CLOEXEC);if(media<0)continue;
  struct media_device_info info={0};if(call(media,MEDIA_IOC_DEVICE_INFO,&info)||strcmp(info.model,"Qualcomm Camera Subsystem")){close(media);media=-1;continue;}
  struct media_entity_desc item={.id=MEDIA_ENT_ID_FLAG_NEXT};
  while(!call(media,MEDIA_IOC_ENUM_ENTITIES,&item)){
   if(entity_count==128){errno=E2BIG;goto cleanup;}entities[entity_count++]=item;
   if(!strcmp(item.name,"msm_csid0"))c=item;
   if(!strcmp(item.name,"msm_vfe0_pix"))v=item;
   if(!strcmp(item.name,"msm_vfe0_video3"))capture=item;
   if(!strcmp(item.name,"msm_vfe0_params"))parameters=item;
   if(!strcmp(item.name,"msm_vfe0_stats"))statistics=item;
   if(!strncmp(item.name,"s5k3m5 ",7))s=item;
   item.id|=MEDIA_ENT_ID_FLAG_NEXT;
  }
  if(c.id&&v.id&&capture.id&&s.id&&parameters.id&&statistics.id)break;
  close(media);media=-1;entity_count=0;c=(struct media_entity_desc){0};v=c;capture=c;s=c;
 }
 if(media<0){errno=ENODEV;goto cleanup;}
 for(unsigned n=0;n<entity_count;n++){
  const struct media_entity_desc *e=&entities[n];if(e->pads>64||e->links>128){errno=E2BIG;goto cleanup;}
  struct media_pad_desc pads[64]={0};struct media_link_desc links[128]={0};
  struct media_links_enum en={.entity=e->id,.pads=pads,.links=links};if(call(media,MEDIA_IOC_ENUM_LINKS,&en))goto cleanup;
  for(unsigned j=0;j<e->links;j++)if(links[j].source.entity==e->id){
   if(link_count==256){errno=E2BIG;goto cleanup;}all_links[link_count++]=links[j];
   if(e->id==s.id&&links[j].flags&MEDIA_LNK_FL_ENABLED)
    for(unsigned k=0;k<entity_count;k++)if(entities[k].id==links[j].sink.entity)p=entities[k];
  }
 }
 if(!p.id||strncmp(p.name,"msm_csiphy",10)){errno=ENOLINK;goto cleanup;}
 char cp[128],vp[128],device[128],sp[128],pp[128];
 if(device_path(&c,true,cp,sizeof(cp))||device_path(&v,true,vp,sizeof(vp))||device_path(&capture,false,device,sizeof(device))||device_path(&s,true,sp,sizeof(sp))||device_path(&p,true,pp,sizeof(pp))){errno=ENODEV;goto cleanup;}
 printf("GRAPH sensor=%s phy=%s csid=%s pix=%s video=%s\n",s.name,p.name,c.name,v.name,device);
 sensor=open(sp,O_RDWR|O_CLOEXEC);phy=open(pp,O_RDWR|O_CLOEXEC);csid=open(cp,O_RDWR|O_CLOEXEC);vfe=open(vp,O_RDWR|O_CLOEXEC);
 if(sensor<0||phy<0||csid<0||vfe<0)goto cleanup;
 phase="save-state";
 struct v4l2_subdev_format input={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=0};
 if(call(sensor,VIDIOC_SUBDEV_G_FMT,&input))goto cleanup;
 if(input.format.code!=MEDIA_BUS_FMT_SGRBG10_1X10||input.format.width!=2104||input.format.height!=1560){errno=ERANGE;goto cleanup;}
 if(save_formats(phy,2)||save_formats(csid,5)||save_formats(vfe,2))goto cleanup;
 /* Sink restoration propagates to all CSID pads; reject nonuniform old state. */
 for(unsigned n=3;n<7;n++)if(memcmp(&formats[2].value.format,&formats[n].value.format,sizeof(input.format))){errno=EINVAL;goto cleanup;}
 for(unsigned n=0;n<4;n++){if(call(n==0?csid:sensor,VIDIOC_G_CTRL,&controls[n]))goto cleanup;controls_saved++;}
 for(unsigned n=0;n<2;n++){if(call(vfe,VIDIOC_SUBDEV_G_SELECTION,&selections[n]))goto cleanup;selections_saved++;}
 struct v4l2_queryctrl exposure={.id=V4L2_CID_EXPOSURE},gain={.id=V4L2_CID_ANALOGUE_GAIN};
 if(call(sensor,VIDIOC_QUERYCTRL,&exposure)||call(sensor,VIDIOC_QUERYCTRL,&gain))goto cleanup;
 if(exposure.minimum>150||exposure.maximum<1200||gain.minimum>64||gain.maximum<64){errno=ERANGE;goto cleanup;}
 phase="configure-links";settings_changed=true;
 struct v4l2_control off={.id=V4L2_CID_TEST_PATTERN,.value=0};if(call(csid,VIDIOC_S_CTRL,&off))goto cleanup;off.value=2;if(call(sensor,VIDIOC_S_CTRL,&off))goto cleanup;
 bool input_link=false,output_link=false,video_link=false;
 for(unsigned n=0;n<link_count;n++){
  struct media_link_desc l=all_links[n];
  if((l.sink.entity==c.id||l.source.entity==c.id)&&l.flags&MEDIA_LNK_FL_ENABLED)
   if(change_link(media,l,false,changed,&changed_count))goto cleanup;
 }
 for(unsigned n=0;n<link_count;n++){
  struct media_link_desc l=all_links[n];
  if(l.source.entity==p.id&&l.source.index==1&&l.sink.entity==c.id&&l.sink.index==0){
   /* All CSID links above are disabled, regardless of their original flags. */
   l.flags&=~MEDIA_LNK_FL_ENABLED;if(change_link(media,l,true,changed,&changed_count))goto cleanup;input_link=true;
  }
  if(l.source.entity==c.id&&l.source.index==4&&l.sink.entity==v.id&&l.sink.index==0){
   l.flags&=~MEDIA_LNK_FL_ENABLED;if(change_link(media,l,true,changed,&changed_count))goto cleanup;output_link=true;
  }
  if(l.source.entity==v.id&&l.sink.entity==capture.id&&l.flags&MEDIA_LNK_FL_ENABLED)video_link=true;
 }
 if(!input_link||!output_link||!video_link){errno=ENOLINK;goto cleanup;}
 phase="configure-formats";
 /* Use the sensor's actual metadata, including colorimetry, throughout. */
 if(set_input(phy,&input.format)||set_input(csid,&input.format)||set_input(vfe,&input.format))goto cleanup;
 struct v4l2_subdev_selection compose={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=0,.target=V4L2_SEL_TGT_COMPOSE,.r={.width=320,.height=240}};
 if(call(vfe,VIDIOC_SUBDEV_S_SELECTION,&compose))goto cleanup;
 if(compose.r.left||compose.r.top||compose.r.width!=320||compose.r.height!=240){errno=ERANGE;goto cleanup;}
 struct v4l2_control setting={.id=V4L2_CID_ANALOGUE_GAIN,.value=64};if(call(sensor,VIDIOC_S_CTRL,&setting))goto cleanup;
 setting=(struct v4l2_control){.id=V4L2_CID_EXPOSURE,.value=150};if(call(sensor,VIDIOC_S_CTRL,&setting))goto cleanup;
 printf("INPUT code=%x width=%u height=%u output=320x240 gain_code=64 exposures=150,1200,150 sensor_tpg=2 csid_tpg=0\n",input.format.code,input.format.width,input.format.height);
 phase="configure-video";
 video=open(device,O_RDWR|O_NONBLOCK|O_CLOEXEC);if(video<0)goto cleanup;
 if(call(video,VIDIOC_G_FMT,&old_format))goto cleanup;format_saved=true;
 struct v4l2_format format={.type=type};format.fmt.pix_mp.width=320;format.fmt.pix_mp.height=240;format.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_NV12;format.fmt.pix_mp.field=V4L2_FIELD_NONE;
 if(call(video,VIDIOC_S_FMT,&format))goto cleanup;
 struct v4l2_pix_format_mplane *f=&format.fmt.pix_mp;
 if(f->width!=320||f->height!=240||f->pixelformat!=V4L2_PIX_FMT_NV12||f->num_planes!=1||f->plane_fmt[0].bytesperline<320||f->plane_fmt[0].sizeimage<(size_t)f->plane_fmt[0].bytesperline*360||f->plane_fmt[0].sizeimage>1024*1024){errno=ERANGE;goto cleanup;}
 printf("FORMAT video=%s width=%u height=%u stride=%u sizeimage=%u\n",device,f->width,f->height,f->plane_fmt[0].bytesperline,f->plane_fmt[0].sizeimage);
 phase="capture-reqbufs";
 struct v4l2_requestbuffers request={.count=3,.type=type,.memory=V4L2_MEMORY_MMAP};if(call(video,VIDIOC_REQBUFS,&request)||request.count<3||request.count>4)goto cleanup;buffers=request.count;
 phase="capture-map-queue";
 for(unsigned n=0;n<buffers;n++){
  struct v4l2_plane plane[VIDEO_MAX_PLANES]={0};struct v4l2_buffer buffer={.index=n,.type=type,.memory=V4L2_MEMORY_MMAP,.length=VIDEO_MAX_PLANES,.m.planes=plane};
  if(call(video,VIDIOC_QUERYBUF,&buffer)||buffer.length!=1||plane[0].length<f->plane_fmt[0].sizeimage||plane[0].length>2*1024*1024){errno=ERANGE;goto cleanup;}
  sizes[n]=plane[0].length;maps[n]=mmap(NULL,sizes[n],PROT_READ|PROT_WRITE,MAP_SHARED,video,plane[0].m.mem_offset);if(maps[n]==MAP_FAILED){maps[n]=NULL;goto cleanup;}
  fills[n]=(unsigned char)(0xa5^(n*0x31));for(size_t i=0;i<sizes[n];i++)((unsigned char *)maps[n])[i]=prefill(fills[n],i);
  if(call(video,VIDIOC_QBUF,&buffer))goto cleanup;
 }
 phase="stats-open";if(stats_open(&statistics))goto cleanup;
 phase="params-open";if(open_params(&parameters))goto cleanup;
 phase="streamon";
 if(call(video,VIDIOC_STREAMON,&type))goto cleanup;streaming=true;
 puts("STREAMON_OK");fflush(stdout);if(dequeue_params(0))goto cleanup;

 phase="capture";
 uint32_t last_sequence=0;int64_t last_time=0;

 for(unsigned frame=0;frame<99;frame++){
  unsigned int wb_phase=frame/9;
  if(frame&&frame%9==0){
   if(wb_phase<7){if(queue_params(wb_phase,true)||dequeue_params(wb_phase))goto cleanup;}
   else if(wb_phase==7){if(call(params_fd,VIDIOC_STREAMOFF,&params_type))goto cleanup;params_streaming=false;puts("PARAM_STREAMOFF_IMAGE_CONTINUES");}
   else if(wb_phase==8){
    if(call(video,VIDIOC_STREAMOFF,&type))goto cleanup;streaming=false;
    if(stats_drain_stopped())goto cleanup;
    for(unsigned n=0;n<buffers;n++){
     struct v4l2_plane planes[VIDEO_MAX_PLANES]={0};planes[0].length=sizes[n];
     struct v4l2_buffer b={.index=n,.type=type,.memory=V4L2_MEMORY_MMAP,.length=1,.m.planes=planes};
     if(call(video,VIDIOC_QBUF,&b))goto cleanup;
    }
    if(call(video,VIDIOC_STREAMON,&type))goto cleanup;streaming=true;last_sequence=0;last_time=0;puts("IMAGE_REOPEN_WITHOUT_PARAMS_STATS_STILL_STREAMING");
   }else if(wb_phase==9){
    if(call(stats_fd,VIDIOC_STREAMOFF,&stats_type))goto cleanup;stats_streaming=false;puts("STATS_STREAMOFF_IMAGE_CONTINUES");
   }else if(wb_phase==10){
    if(stats_start())goto cleanup;puts("STATS_LATE_STREAMON_IMAGE_CONTINUES");
   }
  }
  struct pollfd p={.fd=video,.events=POLLIN};int ready=poll(&p,1,5000);if(ready<=0||interrupted||!(p.revents&POLLIN)){errno=ETIMEDOUT;goto cleanup;}
  struct v4l2_plane plane[VIDEO_MAX_PLANES]={0};struct v4l2_buffer buffer={.type=type,.memory=V4L2_MEMORY_MMAP,.length=VIDEO_MAX_PLANES,.m.planes=plane};if(call(video,VIDIOC_DQBUF,&buffer))goto cleanup;
  if(buffer.index>=buffers||buffer.flags&V4L2_BUF_FLAG_ERROR||buffer.length!=1||plane[0].bytesused!=f->plane_fmt[0].sizeimage||plane[0].data_offset||plane[0].bytesused>sizes[buffer.index]){errno=EIO;goto cleanup;}
  unsigned char *data=maps[buffer.index];size_t changed_bytes=0,active_changed=0;
  for(size_t n=0;n<plane[0].bytesused;n++)changed_bytes+=data[n]!=prefill(fills[buffer.index],n);
  for(unsigned y=0;y<360;y++)for(unsigned x=0;x<320;x++)active_changed+=data[(size_t)y*f->plane_fmt[0].bytesperline+x]!=prefill(fills[buffer.index],(size_t)y*f->plane_fmt[0].bytesperline+x);
  size_t luma=(size_t)f->plane_fmt[0].bytesperline*240,y_changed=0,uv_changed=0;
  for(size_t n=0;n<luma;n++)y_changed+=data[n]!=prefill(fills[buffer.index],n);
  for(size_t n=luma;n<plane[0].bytesused;n++)uv_changed+=data[n]!=prefill(fills[buffer.index],n);
  for(size_t n=plane[0].bytesused;n<sizes[buffer.index];n++)if(data[n]!=prefill(fills[buffer.index],n)){errno=EOVERFLOW;goto cleanup;}
  printf("PLANES y_changed=%zu uv_changed=%zu tail_unchanged=%zu\n",y_changed,uv_changed,sizes[buffer.index]-plane[0].bytesused);
  if(y_changed<luma*3/4||uv_changed<(plane[0].bytesused-luma)*3/4){errno=EIO;goto cleanup;}
  int64_t timestamp=(int64_t)buffer.timestamp.tv_sec*1000000+buffer.timestamp.tv_usec;
  printf("FRAME number=%u index=%u sequence=%u bytes=%u changed=%zu active_changed=%zu active_bytes=115200 hash=%016" PRIx64 " timestamp_us=%" PRId64 "\n",frame,buffer.index,buffer.sequence,plane[0].bytesused,changed_bytes,active_changed,hash(data,plane[0].bytesused),timestamp);fflush(stdout);
  if(active_changed<103680||timestamp<=0||((frame!=0&&frame!=72)&&(buffer.sequence<=last_sequence||timestamp<=last_time))){errno=EIO;goto cleanup;}
  last_sequence=buffer.sequence;last_time=timestamp;
  if(frame%9==8){char output_path[1024];if(snprintf(output_path,sizeof(output_path),"%s-%u.nv12",argv[2],frame)>=(int)sizeof(output_path)){errno=ENAMETOOLONG;goto cleanup;}int output=open(output_path,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);if(output<0)goto cleanup;size_t written=0;while(written<plane[0].bytesused){ssize_t step=write(output,data+written,plane[0].bytesused-written);if(step<=0){close(output);goto cleanup;}written+=(size_t)step;}if(fsync(output)||close(output))goto cleanup;}

  if(stats_streaming&&stats_dequeue(frame,argv[2]))goto cleanup;
  double levels[4]={0};const unsigned int xs[4]={20,220,140,260};
  for(unsigned int patch=0;patch<4;patch++)for(unsigned int yy=112;yy<128;yy++)for(unsigned int xx=xs[patch]-8;xx<xs[patch]+8;xx++)levels[patch]+=data[(size_t)yy*f->plane_fmt[0].bytesperline+xx];
  printf("PIX_LEVEL phase=%u frame=%u sequence=%u white_y=%.6f red_y=%.6f green_y=%.6f blue_y=%.6f\n",wb_phase,frame,buffer.sequence,levels[0]/256,levels[1]/256,levels[2]/256,levels[3]/256);
  for(size_t n=0;n<sizes[buffer.index];n++)data[n]=prefill(fills[buffer.index],n);
  if(call(video,VIDIOC_QBUF,&buffer))goto cleanup;
 }
 result=0;
cleanup:
 if(result)fprintf(stderr,"CAPTURE_FAILURE phase=%s errno=%d message=%s interrupted=%d\n",phase,errno,strerror(errno),(int)interrupted);
 if(streaming&&call(video,VIDIOC_STREAMOFF,&type)){perror("STREAMOFF");result=1;}
 if(stats_close()){perror("stats cleanup");result=1;}
 for(unsigned n=0;n<buffers;n++)if(maps[n])munmap(maps[n],sizes[n]);
 if(video>=0){
  if(buffers){struct v4l2_requestbuffers release={.count=0,.type=type,.memory=V4L2_MEMORY_MMAP};if(call(video,VIDIOC_REQBUFS,&release)){perror("release buffers");result=1;}}
  if(format_saved&&call(video,VIDIOC_S_FMT,&old_format)){perror("restore video format");result=1;}close(video);
 }
 if(params_streaming&&call(params_fd,VIDIOC_STREAMOFF,&params_type)){perror("params STREAMOFF");result=1;}
 if(params_map)munmap(params_map,params_size);
 if(params_fd>=0){struct v4l2_requestbuffers r={.count=0,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP};if(call(params_fd,VIDIOC_REQBUFS,&r)){perror("params release");result=1;}close(params_fd);}
 if(settings_changed){
  /* Restore sinks before dependent source formats and selections. */
  for(unsigned n=0;n<format_count;n++){struct v4l2_subdev_format f=formats[n].value;if(call(formats[n].fd,VIDIOC_SUBDEV_S_FMT,&f)){perror("restore subdev format");result=1;}}
  for(unsigned n=0;n<selections_saved;n++){struct v4l2_subdev_selection sel=selections[n];if(call(vfe,VIDIOC_SUBDEV_S_SELECTION,&sel)){perror("restore selection");result=1;}}
  for(unsigned n=0;n<controls_saved;n++){struct v4l2_control control=controls[n];if(call(n==0?csid:sensor,VIDIOC_S_CTRL,&control)){perror("restore control");result=1;}}
  while(changed_count){struct media_link_desc link=changed[--changed_count];if(call(media,MEDIA_IOC_SETUP_LINK,&link)){perror("restore link");result=1;}}
  for(unsigned n=0;n<format_count;n++){
   struct v4l2_subdev_format f={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=formats[n].value.pad};
   if(call(formats[n].fd,VIDIOC_SUBDEV_G_FMT,&f)||memcmp(&f.format,&formats[n].value.format,sizeof(f.format))){fputs("format readback mismatch\n",stderr);result=1;}
  }
  for(unsigned n=0;n<selections_saved;n++){
   struct v4l2_subdev_selection sel=selections[n];
   if(call(vfe,VIDIOC_SUBDEV_G_SELECTION,&sel)||memcmp(&sel.r,&selections[n].r,sizeof(sel.r))){fputs("selection readback mismatch\n",stderr);result=1;}
  }
  for(unsigned n=0;n<controls_saved;n++){
   struct v4l2_control control={.id=controls[n].id};
   if(call(n==0?csid:sensor,VIDIOC_G_CTRL,&control)||control.value!=controls[n].value){fputs("control readback mismatch\n",stderr);result=1;}
  }
 }
 if(vfe>=0)close(vfe);if(csid>=0)close(csid);if(phy>=0)close(phy);if(sensor>=0)close(sensor);if(media>=0)close(media);
 printf("CAPTURE_RESULT success=%d cleanup_complete=%d\n",!result,!result);return result;
}
