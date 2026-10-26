/* SPDX-License-Identifier: GPL-2.0-only */
/* Bounded GTM hardware probe. Factory tables stay in private input packets. */
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
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t interrupted;
static void on_signal(int n) { (void)n; interrupted=1; }
static int call(int fd,unsigned long req,void *arg) {
 int r;do { r=ioctl(fd,req,arg); }while(r<0&&errno==EINTR&&!interrupted);
 if(r<0)fprintf(stderr,"IOCTL fd=%d request=%#lx errno=%d\n",fd,req,errno);return r;
}
static unsigned char fill(unsigned seed,size_t i) { return seed^(unsigned char)(i*197u+(i>>8)*31u); }
static uint64_t hash(const unsigned char *p,size_t n) { uint64_t h=UINT64_C(14695981039346656037);while(n--)h=(h^*p++)*UINT64_C(1099511628211);return h; }
static int open_entity(const struct media_entity_desc *e,bool subdev) {
 glob_t g={0};int fd=-1;if(glob(subdev?"/dev/v4l-subdev*":"/dev/video*",0,NULL,&g))return -1;
 for(size_t i=0;i<g.gl_pathc;i++){struct stat s;if(!stat(g.gl_pathv[i],&s)&&S_ISCHR(s.st_mode)&&major(s.st_rdev)==e->dev.major&&minor(s.st_rdev)==e->dev.minor){fd=open(g.gl_pathv[i],O_RDWR|O_NONBLOCK|O_CLOEXEC);break;}}
 globfree(&g);return fd;
}
struct queue { int fd; enum v4l2_buf_type type; bool streaming; unsigned count,frames; size_t size,length[4]; void *map[4]; unsigned seed[4]; uint32_t last; bool have_last; };
static int enqueue(struct queue *q,unsigned index) {
 struct v4l2_plane p={.length=q->length[index]};
 struct v4l2_buffer b={.index=index,.type=q->type,.memory=V4L2_MEMORY_MMAP,.length=1,.m.planes=&p};
 if(q->type==V4L2_BUF_TYPE_META_OUTPUT)b.bytesused=q->size;
 return call(q->fd,VIDIOC_QBUF,&b);
}
static int allocate(struct queue *q,unsigned count) {
 struct v4l2_requestbuffers r={.count=count,.type=q->type,.memory=V4L2_MEMORY_MMAP};
 if(call(q->fd,VIDIOC_REQBUFS,&r)||r.count<count||r.count>4)return -1;q->count=r.count;
 for(unsigned i=0;i<q->count;i++){
  struct v4l2_plane p={0};struct v4l2_buffer b={.index=i,.type=q->type,.memory=V4L2_MEMORY_MMAP,.length=1,.m.planes=&p};
  if(call(q->fd,VIDIOC_QUERYBUF,&b))return -1;
  size_t n=(q->type==V4L2_BUF_TYPE_META_OUTPUT||q->type==V4L2_BUF_TYPE_META_CAPTURE)?b.length:p.length;off_t offset=(q->type==V4L2_BUF_TYPE_META_OUTPUT||q->type==V4L2_BUF_TYPE_META_CAPTURE)?b.m.offset:p.m.mem_offset;
  if(n<q->size||n>4*1024*1024)return -1;q->length[i]=n;
  q->map[i]=mmap(NULL,n,PROT_READ|PROT_WRITE,MAP_SHARED,q->fd,offset);if(q->map[i]==MAP_FAILED){q->map[i]=NULL;return -1;}
  q->seed[i]=0xa5^(i*0x31);for(size_t j=0;j<n;j++)((unsigned char*)q->map[i])[j]=fill(q->seed[i],j);
 }
 return 0;
}
static int stream(struct queue *q,bool on) { if(call(q->fd,on?VIDIOC_STREAMON:VIDIOC_STREAMOFF,&q->type))return -1;q->streaming=on;return 0; }
static void cleanup(struct queue *q) {
 if(q->fd<0)return;if(q->streaming)stream(q,false);
 for(unsigned i=0;i<q->count;i++)if(q->map[i])munmap(q->map[i],q->length[i]);close(q->fd);q->fd=-1;
}
static int image_format(struct queue *q,unsigned w,unsigned h,unsigned fourcc,unsigned stride,unsigned size) {
 struct v4l2_format f={.type=q->type};f.fmt.pix_mp=(struct v4l2_pix_format_mplane){.width=w,.height=h,.pixelformat=fourcc,.field=V4L2_FIELD_NONE};
 if(call(q->fd,VIDIOC_S_FMT,&f))return -1;
 struct v4l2_pix_format_mplane *p=&f.fmt.pix_mp;
 printf("FORMAT fourcc=%#x width=%u height=%u planes=%u stride=%u size=%u\n",p->pixelformat,p->width,p->height,p->num_planes,p->plane_fmt[0].bytesperline,p->plane_fmt[0].sizeimage);
 if(p->width!=w||p->height!=h||p->pixelformat!=fourcc||p->num_planes!=1||p->plane_fmt[0].bytesperline!=stride||p->plane_fmt[0].sizeimage!=size)return -1;
 q->size=size;return allocate(q,4);
}
static int dump(const char *root,const char *name,unsigned seq,const void *data,size_t size) {
 char path[512];if(snprintf(path,sizeof(path),"%s/%s-%u.bin",root,name,seq)>=(int)sizeof(path))return -1;
 FILE *f=fopen(path,"wbx");if(!f)return -1;bool ok=fwrite(data,1,size,f)==size;return fclose(f)||!ok?-1:0;
}

static unsigned char base_packet[4096];static size_t base_size;
static struct camss_params_ife_gtm gtms[9];static const unsigned scene_packets[]={0,3,7};
static unsigned packet_index(unsigned phase,bool scene){return scene?scene_packets[phase]:phase;}
static int gtm_queue(struct queue *params,unsigned phase,bool scene){
 const struct camss_params_ife_gtm *g=&gtms[packet_index(phase,scene)];
 memcpy(params->map[0],base_packet,base_size);memcpy((char*)params->map[0]+base_size,g,sizeof(*g));
 struct v4l2_isp_buffer *b=params->map[0];b->data_size=base_size-sizeof(*b)+sizeof(*g);params->size=base_size+sizeof(*g);
 if(enqueue(params,0))return -1;
 memset((char*)params->map[0]+sizeof(*b),0,params->size-sizeof(*b));
 printf("GTM_PARAM_Q phase=%u packet=%u cookie=%" PRIu64 " enabled=%u bytes=%zu mutated_after_queue=1\n",phase,packet_index(phase,scene),(uint64_t)g->cookie,g->enabled,params->size);return 0;
}
static int read_stats(struct queue *stats,const struct v4l2_buffer *b,const char *root,
                      unsigned phase,uint64_t *cookie,uint64_t *generation,unsigned *status,unsigned *bank){
 if(b->index>=stats->count||b->flags&V4L2_BUF_FLAG_ERROR||b->bytesused<8||b->bytesused>stats->size||(stats->have_last&&b->sequence<=stats->last))return -1;
 const unsigned char *data=stats->map[b->index];const struct v4l2_isp_buffer *p=(const void*)data;
 if(p->version!=1||p->data_size!=b->bytesused-sizeof(*p))return -1;
 *cookie=*generation=0;*status=*bank=0;unsigned seen=0;uint64_t sum=0;
 for(size_t at=0;at<p->data_size;){
  if(p->data_size-at<sizeof(struct v4l2_isp_block_header))return -1;
  const struct v4l2_isp_block_header *h=(const void*)(p->data+at);
  if(h->size<sizeof(*h)||h->size%8||h->size>p->data_size-at||h->flags)return -1;
  if(h->type==CAMSS_STATS_IFE_GTM){
   if(h->size!=sizeof(struct camss_stats_ife_gtm)||seen&4)return -1;
   const struct camss_stats_ife_gtm *g=(const void*)h;*cookie=g->cookie;*generation=g->generation;*status=g->status;*bank=g->bank;seen|=4;
   if(!*cookie||!*generation||!(*status&1)||*status&~3u||*bank>1)return -1;
  }else if(h->type==CAMSS_STATS_AEC_BHIST){
   if(h->size!=sizeof(struct camss_stats_bhist)||seen&1)return -1;
   const struct camss_stats_bhist *hist=(const void*)h;for(unsigned i=0;i<1024;i++)sum+=hist->bins[i];seen|=1;
  }else if(h->type==CAMSS_STATS_AWB_BG){if(seen&2)return -1;seen|=2;}else return -1;
  at+=h->size;
 }
 if((seen&3)!=3||!sum)return -1;
 for(size_t i=b->bytesused;i<stats->length[b->index];i++)if(data[i]!=fill(stats->seed[b->index],i))return -1;
 stats->last=b->sequence;stats->have_last=true;stats->frames++;
 printf("GTM_STATS phase=%u sequence=%u timestamp_us=%" PRId64 " bytes=%u cookie=%" PRIu64 " generation=%" PRIu64 " status=%u bank=%u population=%" PRIu64 "\n",phase,b->sequence,(int64_t)b->timestamp.tv_sec*1000000+b->timestamp.tv_usec,b->bytesused,*cookie,*generation,*status,*bank,sum);
 return dump(root,"stats",b->sequence,data,b->bytesused);
}

int main(int argc,char **argv) {
 if(argc!=3){fprintf(stderr,"usage: %s PRIVATE_ROOT SENSOR_PATTERN\n",argv[0]);return 2;}
 struct utsname u;if(uname(&u)||strcmp(u.release,"7.3.0-rc6-rmx1931-samurai-k363+"))return 3;
 signal(SIGINT,on_signal);signal(SIGTERM,on_signal);setvbuf(stdout,NULL,_IOLBF,0);
 bool scene=atoi(argv[2])==0;unsigned phases=scene?3:9;
 const char *model=getenv("DS4_SENSOR_MODEL");if(!model)model="s5kgw1";
 const struct {const char *name;unsigned width,height;} modes[]={
  {"s5kgw1",4608,3456},{"s5k3m5",2104,1560},{"imx471",2304,1728},{"imx319",1632,1224}};
 unsigned mode=0;while(mode<4&&strcmp(model,modes[mode].name))mode++;if(mode==4)return 2;
 unsigned sensor_width=modes[mode].width,sensor_height=modes[mode].height;
 printf("CAMERA model=%s requested=%ux%u\n",model,sensor_width,sensor_height);

 struct queue full={.fd=-1,.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE},ds={.fd=-1,.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE},params={.fd=-1,.type=V4L2_BUF_TYPE_META_OUTPUT},stats={.fd=-1,.type=V4L2_BUF_TYPE_META_CAPTURE};
 int media=-1,sensor=-1,phy=-1,csid=-1,vfe=-1,result=1;const char *phase="discover";
 struct media_entity_desc entities[128],sen={0},ph={0},cs={0},vf={0},fu={0},ds4={0},pa={0},st={0};unsigned ne=0,nl=0;
 struct media_link_desc links[512];media=open("/dev/media0",O_RDWR|O_CLOEXEC);if(media<0)goto done;
 struct media_entity_desc e={.id=MEDIA_ENT_ID_FLAG_NEXT};
 while(!ioctl(media,MEDIA_IOC_ENUM_ENTITIES,&e)){
  if(ne==128)goto done;entities[ne++]=e;
  if(!strncmp(e.name,model,strlen(model))&&e.name[strlen(model)]==' ')sen=e;
  if(!strcmp(e.name,"msm_csid0"))cs=e;if(!strcmp(e.name,"msm_vfe0_pix"))vf=e;
  if(!strcmp(e.name,"msm_vfe0_video3"))fu=e;if(!strcmp(e.name,"msm_vfe0_ds4"))ds4=e;if(!strcmp(e.name,"msm_vfe0_params"))pa=e;if(!strcmp(e.name,"msm_vfe0_stats"))st=e;
  e.id|=MEDIA_ENT_ID_FLAG_NEXT;
 }
 if(!sen.id||!cs.id||!vf.id||!fu.id||!ds4.id||!pa.id||!st.id)goto done;
 for(unsigned i=0;i<ne;i++){
  struct media_pad_desc pads[64];struct media_link_desc edges[128];struct media_links_enum en={.entity=entities[i].id,.pads=pads,.links=edges};
  if(entities[i].pads>64||entities[i].links>128||call(media,MEDIA_IOC_ENUM_LINKS,&en))goto done;
  for(unsigned j=0;j<entities[i].links;j++)if(edges[j].source.entity==entities[i].id){
   if(nl==512)goto done;links[nl++]=edges[j];
   if(edges[j].source.entity==sen.id&&(edges[j].flags&MEDIA_LNK_FL_ENABLED))for(unsigned k=0;k<ne;k++)if(entities[k].id==edges[j].sink.entity)ph=entities[k];
  }
 }
 if(!ph.id)goto done;
 sensor=open_entity(&sen,true);phy=open_entity(&ph,true);csid=open_entity(&cs,true);vfe=open_entity(&vf,true);
 full.fd=open_entity(&fu,false);ds.fd=open_entity(&ds4,false);params.fd=open_entity(&pa,false);stats.fd=open_entity(&st,false);
 if(sensor<0||phy<0||csid<0||vfe<0||full.fd<0||ds.fd<0||params.fd<0||stats.fd<0)goto done;
 struct v4l2_fmtdesc desc={.type=ds.type};if(call(ds.fd,VIDIOC_ENUM_FMT,&desc)||desc.pixelformat!=V4L2_PIX_FMT_QCOM_PD10_LOCAL||!desc.description[0])goto done;
 phase="links";
 for(unsigned i=0;i<nl;i++){struct media_link_desc l=links[i];if((l.sink.entity==cs.id||l.source.entity==cs.id)&&(l.flags&MEDIA_LNK_FL_ENABLED)){l.flags&=~MEDIA_LNK_FL_ENABLED;if(call(media,MEDIA_IOC_SETUP_LINK,&l))goto done;}}
 unsigned enabled=0;
 for(unsigned i=0;i<nl;i++){struct media_link_desc l=links[i];if((l.source.entity==ph.id&&l.source.index==1&&l.sink.entity==cs.id&&l.sink.index==0)||(l.source.entity==cs.id&&l.source.index==4&&l.sink.entity==vf.id&&l.sink.index==0)){l.flags|=MEDIA_LNK_FL_ENABLED;if(call(media,MEDIA_IOC_SETUP_LINK,&l))goto done;enabled++;}}
 if(enabled!=2)goto done;
 phase="sensor-format";struct v4l2_subdev_format input={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=0};
 if(call(sensor,VIDIOC_SUBDEV_G_FMT,&input))goto done;input.format.width=sensor_width;input.format.height=sensor_height;
 if(call(sensor,VIDIOC_SUBDEV_S_FMT,&input)||input.format.width!=sensor_width||input.format.height!=sensor_height)goto done;
 printf("SENSOR width=%u height=%u code=%#x field=%u\n",input.format.width,input.format.height,input.format.code,input.format.field);
 for(unsigned i=0;i<3;i++){int fd=(int[]){phy,csid,vfe}[i];phase=(const char*[]){"phy-format","csid-format","vfe-format"}[i];struct v4l2_subdev_format f=input;if(call(fd,VIDIOC_SUBDEV_S_FMT,&f))goto done;printf("INPUT stage=%u width=%u height=%u code=%#x field=%u\n",i,f.format.width,f.format.height,f.format.code,f.format.field);if(f.format.code!=input.format.code||f.format.width!=input.format.width||f.format.height!=input.format.height)goto done;}
 phase="controls";
 struct v4l2_control ctl={.id=V4L2_CID_TEST_PATTERN,.value=0};if(call(csid,VIDIOC_S_CTRL,&ctl))goto done;ctl.value=atoi(argv[2]);if(call(sensor,VIDIOC_S_CTRL,&ctl))goto done;
 struct v4l2_queryctrl qc={.id=V4L2_CID_EXPOSURE};if(call(sensor,VIDIOC_QUERYCTRL,&qc))goto done;
 ctl=(struct v4l2_control){.id=V4L2_CID_EXPOSURE,.value=qc.default_value};if(call(sensor,VIDIOC_S_CTRL,&ctl))goto done;
 phase="compose";struct v4l2_subdev_selection compose={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=0,.target=V4L2_SEL_TGT_COMPOSE,.r={.width=640,.height=480}};
 if(call(vfe,VIDIOC_SUBDEV_S_SELECTION,&compose)||compose.r.width!=640||compose.r.height!=480)goto done;
 phase="coarse-format";struct v4l2_subdev_format coarse={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=2,.format={.width=160,.height=120,.code=MEDIA_BUS_FMT_UYYVYY10_0_5X30,.field=V4L2_FIELD_NONE}};
 if(call(vfe,VIDIOC_SUBDEV_S_FMT,&coarse)||coarse.format.width!=160||coarse.format.height!=120||coarse.format.code!=MEDIA_BUS_FMT_UYYVYY10_0_5X30)goto done;
 phase="image-buffers";if(image_format(&full,640,480,V4L2_PIX_FMT_NV12,640,460800)||image_format(&ds,160,120,V4L2_PIX_FMT_QCOM_PD10_LOCAL,768,46080))goto done;
 phase="params";struct v4l2_format pf={.type=params.type};if(call(params.fd,VIDIOC_G_FMT,&pf))goto done;
 char packet[512];snprintf(packet,sizeof(packet),"%s/params-private.bin",argv[1]);FILE *f=fopen(packet,"rb");if(!f)goto done;
 base_size=fread(base_packet,1,sizeof(base_packet),f);fclose(f);if(base_size!=56)goto done;
 params.size=base_size+sizeof(struct camss_params_ife_gtm);if(allocate(&params,1))goto done;
 snprintf(packet,sizeof(packet),"%s/gtm-packets-private.bin",argv[1]);f=fopen(packet,"rb");if(!f)goto done;
 bool valid=fread(gtms,sizeof(gtms),1,f)==1&&fgetc(f)==EOF;fclose(f);if(!valid)goto done;
 for(unsigned i=0;i<9;i++)if(gtms[i].header.type!=CAMSS_PARAMS_IFE_GTM||gtms[i].header.flags||gtms[i].header.size!=sizeof(gtms[i])||!gtms[i].cookie||gtms[i].enabled>1||gtms[i].reserved)goto done;
 if(gtm_queue(&params,0,scene))goto done;
 struct v4l2_format sf={.type=stats.type};if(call(stats.fd,VIDIOC_G_FMT,&sf)||sf.fmt.meta.dataformat!=V4L2_META_FMT_QCOM_ISP_STATS)goto done;
 stats.size=sf.fmt.meta.buffersize;if(stats.size<sizeof(struct v4l2_isp_buffer)+sizeof(struct camss_stats_bhist)||allocate(&stats,4))goto done;
 for(unsigned i=0;i<stats.count;i++)if(enqueue(&stats,i))goto done;
 if(full.count!=4||ds.count!=4)goto done;
 for(unsigned i=0;i<4;i++)if(enqueue(&full,i)||enqueue(&ds,i))goto done;
 struct v4l2_event_subscription sub={.type=V4L2_EVENT_FRAME_SYNC};if(call(vfe,VIDIOC_SUBSCRIBE_EVENT,&sub))goto done;
 phase="streamon";if(stream(&params,true)||stream(&stats,true)||stream(&ds,true)||stream(&full,true))goto done;
 phase="capture";unsigned step=0,accepted=0;bool parameter_pending=true;time_t start=time(NULL);
 while(!interrupted&&time(NULL)-start<24){
  struct pollfd p[5]={{.fd=full.fd,.events=POLLIN},{.fd=ds.fd,.events=POLLIN},{.fd=vfe,.events=POLLPRI},{.fd=stats.fd,.events=POLLIN},{.fd=parameter_pending?params.fd:-1,.events=POLLOUT}};
  int ready=poll(p,5,3000);if(ready<=0)goto done;
  for(unsigned k=0;k<5;k++)if(p[k].revents&(POLLERR|POLLHUP|POLLNVAL)){printf("GTM_POLL_ERROR slot=%u events=%#x\n",k,p[k].revents);goto done;}
  if(p[2].revents&POLLPRI){struct v4l2_event ev;while(!ioctl(vfe,VIDIOC_DQEVENT,&ev))printf("SOF sequence=%u\n",ev.u.frame_sync.frame_sequence);}
  if(p[4].revents&POLLOUT){
   struct v4l2_buffer b={.type=params.type,.memory=V4L2_MEMORY_MMAP};if(call(params.fd,VIDIOC_DQBUF,&b)||b.index||b.flags&V4L2_BUF_FLAG_ERROR)goto done;
   parameter_pending=false;printf("GTM_PARAM_DQ phase=%u sequence=%u timestamp_us=%" PRId64 "\n",step,b.sequence,(int64_t)b.timestamp.tv_sec*1000000+b.timestamp.tv_usec);
  }
  for(unsigned k=0;k<2;k++)if(p[k].revents&POLLIN){
   struct queue *q=k?&ds:&full;struct v4l2_plane pl={0};struct v4l2_buffer b={.type=q->type,.memory=V4L2_MEMORY_MMAP,.length=1,.m.planes=&pl};
   if(call(q->fd,VIDIOC_DQBUF,&b)||b.index>=q->count||b.flags&V4L2_BUF_FLAG_ERROR||pl.bytesused!=q->size||(q->have_last&&b.sequence<=q->last))goto done;
   q->last=b.sequence;q->have_last=true;q->frames++;unsigned char *data=q->map[b.index];size_t changed=0,tail=0;
   for(size_t i=0;i<q->size;i++)changed+=data[i]!=fill(q->seed[b.index],i);
   for(size_t i=q->size;i<q->length[b.index];i++)tail+=data[i]!=fill(q->seed[b.index],i);
   if(!changed||tail)goto done;
   uint64_t active_hash=UINT64_C(14695981039346656037);
   if(k)for(unsigned row=0;row<60;row++)for(unsigned x=0;x<640;x++)active_hash=(active_hash^data[row*768+x])*UINT64_C(1099511628211);else active_hash=hash(data,q->size);
   printf("GTM_FRAME kind=%s phase=%u sequence=%u timestamp_us=%" PRId64 " bytes=%u hash=%016" PRIx64 " active_hash=%016" PRIx64 "\n",k?"ds4":"full",step,b.sequence,(int64_t)b.timestamp.tv_sec*1000000+b.timestamp.tv_usec,pl.bytesused,hash(data,q->size),active_hash);
   if(dump(argv[1],k?"ds4":"full",b.sequence,data,q->size))goto done;
   for(size_t i=0;i<q->length[b.index];i++)data[i]=fill(q->seed[b.index],i);
   if(enqueue(q,b.index))goto done;
  }
  if(p[3].revents&POLLIN){
   struct v4l2_buffer b={.type=stats.type,.memory=V4L2_MEMORY_MMAP};uint64_t cookie,generation;unsigned status,bank;
   if(call(stats.fd,VIDIOC_DQBUF,&b)||read_stats(&stats,&b,argv[1],step,&cookie,&generation,&status,&bank))goto done;
   const struct camss_params_ife_gtm *want=&gtms[packet_index(step,scene)];
   if(cookie==want->cookie){if(generation!=step+1||status!=(1u|(want->enabled?2u:0u)))goto done;accepted++;}
   unsigned char *data=stats.map[b.index];for(size_t i=0;i<stats.length[b.index];i++)data[i]=fill(stats.seed[b.index],i);
   if(enqueue(&stats,b.index))goto done;
  }
  if(!parameter_pending&&accepted>=5&&full.have_last&&ds.have_last&&full.last>=stats.last&&ds.last>=stats.last){
   printf("GTM_PHASE_DONE phase=%u matched_stats=%u\n",step,accepted);step++;accepted=0;
   if(step==phases){result=0;break;}
   if(gtm_queue(&params,step,scene))goto done;parameter_pending=true;
  }
 }

done:
 if(full.streaming&&stream(&full,false))result=1;
 if(ds.streaming&&stream(&ds,false))result=1;
 if(result&&!strcmp(phase,"capture"))for(unsigned k=0;k<2;k++){
  struct queue *q=k?&ds:&full;
  for(unsigned b=0;b<q->count;b++)if(q->map[b]){
   const unsigned char *data=q->map[b];size_t changed=0;unsigned first=UINT32_MAX,last=0,rows=0;size_t stride=k?768:640;
   for(size_t row=0;row<q->size/stride;row++){bool different=false;for(size_t x=0;x<stride;x++){size_t at=row*stride+x;if(data[at]!=fill(q->seed[b],at)){changed++;different=true;}}if(different){if(first==UINT32_MAX)first=row;last=row;rows++;}}
   printf("UNDELIVERED kind=%s index=%u changed=%zu changed_rows=%u first_row=%u last_row=%u\n",k?"ds4":"full",b,changed,rows,first,last);
   if(changed){char name[48];snprintf(name,sizeof(name),"undelivered-%s",k?"ds4":"full");if(dump(argv[1],name,b,data,q->size))result=1;}
  }
 }
 cleanup(&stats);cleanup(&ds);cleanup(&params);cleanup(&full);
 if(sensor>=0)close(sensor);if(phy>=0)close(phy);if(csid>=0)close(csid);if(vfe>=0)close(vfe);if(media>=0)close(media);
 printf("GTM_RESULT result=%d phase=%s full_frames=%u ds4_frames=%u stats_frames=%u interrupted=%d\n",result,phase,full.frames,ds.frames,stats.frames,interrupted);return result;
}
