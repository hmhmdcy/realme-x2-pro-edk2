"""Derive the bounded typed histogram probe from the verified k293 WB probe."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel293/samurai-wb-params.c').read_text().replace('samurai-k293+','samurai-k294+').replace('"#293 "','"#294 "')
s=s.replace('CAMSS_PARAMS_AEC_BHIST;break;case 3','CAMSS_PARAMS_GAMMA;break;case 3')
old=''' struct params_envelope envelope={V4L2_ISP_VERSION_V1,wb.header.size};
 memset(memory,0,params_size);memcpy(memory,&envelope,sizeof(envelope));memcpy((char*)memory+sizeof(envelope),&wb,wb.header.size);
 return sizeof(envelope)+wb.header.size;'''
new=''' struct camss_params_aec_bhist bh={.header={CAMSS_PARAMS_AEC_BHIST,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(bh)},.width=2104,.height=1560};
 if(phase==1)bh.width=1052;
 if(phase==2){bh.left=1052;bh.width=1052;}
 if(phase==3){bh.width=4;bh.height=2;}
 if(phase==5){bh.left=4000;bh.top=4000;bh.width=8192;bh.height=16384;}
 struct params_envelope envelope={V4L2_ISP_VERSION_V1,wb.header.size+sizeof(bh)};
 memset(memory,0,params_size);memcpy(memory,&envelope,sizeof(envelope));memcpy((char*)memory+sizeof(envelope),&wb,wb.header.size);
 memcpy((char*)memory+sizeof(envelope)+wb.header.size,&bh,sizeof(bh));
 return sizeof(envelope)+envelope.data_size;'''
assert old in s;s=s.replace(old,new)
insert=r'''
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
'''
s=s.replace('struct format_save {',insert+'\nstruct format_save {',1)
s=s.replace('parameters={0};','parameters={0},statistics={0};')
s=s.replace('if(!strcmp(item.name,"msm_vfe0_params"))parameters=item;','if(!strcmp(item.name,"msm_vfe0_params"))parameters=item;\n   if(!strcmp(item.name,"msm_vfe0_stats"))statistics=item;')
s=s.replace('s.id&&parameters.id)break;','s.id&&parameters.id&&statistics.id)break;')
s=s.replace('phase="params-open";if(open_params(&parameters))goto cleanup;','phase="stats-open";if(stats_open(&statistics))goto cleanup;\n phase="params-open";if(open_params(&parameters))goto cleanup;')
s=s.replace('frame<81','frame<99')
s=s.replace('if(call(video,VIDIOC_STREAMOFF,&type))goto cleanup;streaming=false;','if(call(video,VIDIOC_STREAMOFF,&type))goto cleanup;streaming=false;\n    if(stats_drain_stopped())goto cleanup;',1)
s=s.replace('puts("IMAGE_REOPEN_WITHOUT_PARAMS");','puts("IMAGE_REOPEN_WITHOUT_PARAMS_STATS_STILL_STREAMING");')
old='''   }
  }
  struct pollfd p={.fd=video'''
new='''   }else if(wb_phase==9){
    if(call(stats_fd,VIDIOC_STREAMOFF,&stats_type))goto cleanup;stats_streaming=false;puts("STATS_STREAMOFF_IMAGE_CONTINUES");
   }else if(wb_phase==10){
    if(stats_start())goto cleanup;puts("STATS_LATE_STREAMON_IMAGE_CONTINUES");
   }
  }
  struct pollfd p={.fd=video'''
assert old in s;s=s.replace(old,new,1)
s=s.replace('((frame%72)&&(buffer.sequence<=last_sequence||timestamp<=last_time))','((frame!=0&&frame!=72)&&(buffer.sequence<=last_sequence||timestamp<=last_time))')
s=s.replace('  double levels[4]={0};','  if(stats_streaming&&stats_dequeue(frame,argv[2]))goto cleanup;\n  double levels[4]={0};')
s=s.replace(' for(unsigned n=0;n<buffers;n++)if(maps[n])munmap(maps[n],sizes[n]);',' if(stats_close()){perror("stats cleanup");result=1;}\n for(unsigned n=0;n<buffers;n++)if(maps[n])munmap(maps[n],sizes[n]);')
p=ROOT/'samurai-stats.c';assert not p.exists();p.write_text(s)
print('Prepared 99-image / 90-statistics bounded probe, including independent statistics restart.')
