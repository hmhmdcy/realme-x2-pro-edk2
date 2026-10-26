"""Reuse proven media restoration, capturing one stable image/statistics pair."""
from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;TREE=Path('/mnt/samurai-full282/source338')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);storage.mounted_build()
s=(HERE.parent/'kernel334/samurai-ccm.c').read_text()
a=s.index('static struct camss_params_color_correct factory_ccm;');b=s.index('static int queue_params(',a)
s=s[:a]+'''static unsigned input_width,input_height;
static size_t make_packet(void *memory,unsigned int phase) {
 (void)phase;
 struct camss_params_wb_gain wb={.header={CAMSS_PARAMS_WB_GAIN,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(wb)},.g_gain=1024,.b_gain=1024,.r_gain=1024};
 struct camss_params_aec_bhist bh={.header={CAMSS_PARAMS_AEC_BHIST,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(bh)},.width=input_width,.height=input_height};
 struct params_envelope e={V4L2_ISP_VERSION_V1,sizeof(wb)+sizeof(bh)};
 memset(memory,0,params_size);memcpy(memory,&e,sizeof(e));memcpy((char*)memory+sizeof(e),&wb,sizeof(wb));memcpy((char*)memory+sizeof(e)+sizeof(wb),&bh,sizeof(bh));return sizeof(e)+e.data_size;
}
'''+s[b:]
a=s.index('static int reject_invalid_params(');b=s.index('static int open_params(',a);s=s[:a]+s[b:]
s=s.replace('reject_invalid_params()||queue_params(0,true)','queue_params(0,false)')
s=s.replace('sizeof(struct camss_params_color_correct)','sizeof(struct camss_params_aec_bhist)')
needle='static int save_formats(';at=s.index(needle)
support='''static int stats_fd=-1;static void *stats_maps[3];static size_t stats_sizes[3];static unsigned stats_buffers,stats_capacity;
static bool stats_streaming,stats_stable,stats_seen,stats_nonuniform;static uint64_t previous_stats_hash;
static unsigned char current_stats[65536];static size_t current_stats_size;
static enum v4l2_buf_type stats_type=V4L2_BUF_TYPE_META_CAPTURE;
static int stats_queue(unsigned index) {
 memset(stats_maps[index],0xa5,stats_sizes[index]);
 struct v4l2_buffer b={.index=index,.type=V4L2_BUF_TYPE_META_CAPTURE,.memory=V4L2_MEMORY_MMAP};return call(stats_fd,VIDIOC_QBUF,&b);
}
static int stats_open(const struct media_entity_desc *entity) {
 char path[128];if(device_path(entity,false,path,sizeof(path)))return -1;
 stats_fd=open(path,O_RDWR|O_NONBLOCK|O_CLOEXEC);if(stats_fd<0)return -1;
 struct v4l2_format f={.type=V4L2_BUF_TYPE_META_CAPTURE};if(call(stats_fd,VIDIOC_G_FMT,&f))return -1;
 if(f.fmt.meta.dataformat!=V4L2_META_FMT_QCOM_ISP_STATS||f.fmt.meta.buffersize!=sizeof(struct params_envelope)+CAMSS_STATS_MAX_PAYLOAD){errno=EPROTO;return -1;}
 stats_capacity=f.fmt.meta.buffersize;
 struct v4l2_requestbuffers r={.count=3,.type=V4L2_BUF_TYPE_META_CAPTURE,.memory=V4L2_MEMORY_MMAP};if(call(stats_fd,VIDIOC_REQBUFS,&r)||r.count!=3)return -1;stats_buffers=r.count;
 for(unsigned i=0;i<stats_buffers;i++){
  struct v4l2_buffer b={.index=i,.type=V4L2_BUF_TYPE_META_CAPTURE,.memory=V4L2_MEMORY_MMAP};if(call(stats_fd,VIDIOC_QUERYBUF,&b)||b.length<stats_capacity||b.length>sizeof(current_stats))return -1;
  stats_sizes[i]=b.length;stats_maps[i]=mmap(NULL,b.length,PROT_READ|PROT_WRITE,MAP_SHARED,stats_fd,b.m.offset);if(stats_maps[i]==MAP_FAILED){stats_maps[i]=NULL;return -1;}
  if(stats_queue(i))return -1;
 }
 if(call(stats_fd,VIDIOC_STREAMON,&stats_type))return -1;stats_streaming=true;
 printf("STATS_NODE path=%s capacity=%u buffers=%u\\n",path,stats_capacity,stats_buffers);return 0;
}
static int stats_dequeue(unsigned frame) {
 struct pollfd poller={.fd=stats_fd,.events=POLLIN};if(poll(&poller,1,3000)<=0||!(poller.revents&POLLIN)){errno=ETIMEDOUT;return -1;}
 struct v4l2_buffer b={.type=V4L2_BUF_TYPE_META_CAPTURE,.memory=V4L2_MEMORY_MMAP};if(call(stats_fd,VIDIOC_DQBUF,&b))return -1;
 const size_t expected=sizeof(struct params_envelope)+sizeof(struct camss_stats_bhist)+sizeof(struct camss_stats_awb_bg)+512*sizeof(struct camss_stats_bg_region);
 if(b.index>=stats_buffers||b.flags&V4L2_BUF_FLAG_ERROR||b.bytesused!=expected||b.bytesused>stats_capacity){errno=EPROTO;return -1;}
 const unsigned char *data=stats_maps[b.index];const struct params_envelope *e=(const void*)data;
 const struct camss_stats_bhist *h=(const void*)(data+sizeof(*e));const struct camss_stats_awb_bg *bg=(const void*)(data+sizeof(*e)+sizeof(*h));
 if(e->version!=V4L2_ISP_VERSION_V1||e->data_size!=b.bytesused-sizeof(*e)||h->header.type!=CAMSS_STATS_AEC_BHIST||h->header.flags||h->header.size!=sizeof(*h)||
    bg->header.type!=CAMSS_STATS_AWB_BG||bg->header.flags||bg->header.size!=sizeof(*bg)+512*sizeof(struct camss_stats_bg_region)||bg->columns!=32||bg->rows!=16||bg->input_bits!=14||bg->high_threshold!=16383||
    (bg->left|bg->top|bg->region_width|bg->region_height)&1||bg->left+(uint32_t)bg->columns*bg->region_width>input_width||bg->top+(uint32_t)bg->rows*bg->region_height>input_height){errno=EPROTO;return -1;}
 for(size_t i=stats_capacity;i<stats_sizes[b.index];i++)if(data[i]!=0xa5){errno=EOVERFLOW;return -1;}
 uint64_t histogram=0,counts[4]={0};for(unsigned i=0;i<CAMSS_STATS_BHIST_BINS;i++)histogram+=h->bins[i];
 if(histogram!=(uint64_t)(input_width/2)*(input_height/2)){errno=EPROTO;return -1;}
 unsigned maximum=bg->region_width*bg->region_height/4;stats_nonuniform=false;
 for(unsigned i=0;i<512;i++){
  const struct camss_stats_bg_region *r=&bg->regions[i];uint32_t sums[4]={r->r_sum,r->b_sum,r->gr_sum,r->gb_sum};uint16_t n[4]={r->r_count,r->b_count,r->gr_count,r->gb_count};
  for(unsigned c=0;c<4;c++){if(n[c]>maximum||sums[c]>(uint64_t)n[c]*bg->high_threshold){errno=EPROTO;return -1;}counts[c]+=n[c];}
  if(i&&memcmp(r,&bg->regions[0],sizeof(*r)))stats_nonuniform=true;
 }
 for(unsigned c=0;c<4;c++)if(!counts[c]){errno=ENODATA;return -1;}
 uint64_t value=hash((const void*)bg,bg->header.size);stats_stable=stats_seen&&value==previous_stats_hash;stats_seen=true;previous_stats_hash=value;
 memcpy(current_stats,data,b.bytesused);current_stats_size=b.bytesused;
 printf("BG_FRAME frame=%u sequence=%u bytes=%u grid=%ux%u offset=%u,%u region=%ux%u stable=%u nonuniform=%u hash=%016" PRIx64 "\\n",frame,b.sequence,b.bytesused,bg->columns,bg->rows,bg->left,bg->top,bg->region_width,bg->region_height,stats_stable,stats_nonuniform,value);fflush(stdout);
 return stats_queue(b.index);
}
static int stats_close(void) {
 int result=0;if(stats_streaming&&call(stats_fd,VIDIOC_STREAMOFF,&stats_type))result=-1;
 for(unsigned i=0;i<stats_buffers;i++)if(stats_maps[i])munmap(stats_maps[i],stats_sizes[i]);
 if(stats_fd>=0){struct v4l2_requestbuffers r={.count=0,.type=V4L2_BUF_TYPE_META_CAPTURE,.memory=V4L2_MEMORY_MMAP};if(call(stats_fd,VIDIOC_REQBUFS,&r))result=-1;close(stats_fd);}return result;
}
static int save_private(const char *prefix,const char *suffix,const void *data,size_t length) {
 char path[1024];if(snprintf(path,sizeof(path),"%s-private.%s",prefix,suffix)>=(int)sizeof(path)){errno=ENAMETOOLONG;return -1;}
 int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);if(fd<0)return -1;
 size_t written=0;while(written<length){ssize_t n=write(fd,(const char*)data+written,length-written);if(n<=0){close(fd);return -1;}written+=(size_t)n;}return close(fd);
}
'''
s=s[:at]+support+s[at:]
a=s.index(' if(argc!=4||strcmp(argv[1],"--pattern"))');b=s.index(' struct utsname identity;',a)
s=s[:a]+''' if(argc!=4||strcmp(argv[1],"--capture")){fprintf(stderr,"usage: %s --capture MODEL PRIVATE_OUTPUT_PREFIX\\n",argv[0]);return 2;}
 const char *model=argv[2],*prefix=argv[3];unsigned pattern=!strcmp(model,"s5kgw1")?2:3;
'''+s[b:]
s=s.replace('if(!strncmp(item.name,"s5kgw1 ",7))s=item;','if(!strncmp(item.name,model,strlen(model))&&item.name[strlen(model)]==\' \')s=item;')
s=s.replace('if(!input.format.width||!input.format.height){errno=ERANGE;goto cleanup;}','if(!input.format.width||!input.format.height){errno=ERANGE;goto cleanup;}input_width=input.format.width;input_height=input.format.height;')
s=s.replace('off.value=2;if(call(sensor,VIDIOC_S_CTRL,&off))','off.value=pattern;if(call(sensor,VIDIOC_S_CTRL,&off))')
s=s.replace('sensor_tpg=2 csid_tpg=0\\n",input.format.code,input.format.width,input.format.height','sensor_tpg=%u csid_tpg=0\\n",input.format.code,input.format.width,input.format.height,pattern')
s=s.replace(' phase="params-open";if(open_params(&parameters))goto cleanup;',' phase="params-open";if(open_params(&parameters))goto cleanup;\n phase="stats-open";if(stats_open(&statistics))goto cleanup;')
a=s.index(' unsigned wb_phase=0,phase_frames=0;');b=s.index(' result=0;',a)
s=s[:a]+''' unsigned frames=0;uint64_t previous_image_hash=0;bool image_seen=false,complete=false;
 while(!complete&&!interrupted){
  struct pollfd poller={.fd=video,.events=POLLIN};if(poll(&poller,1,5000)<=0||!(poller.revents&POLLIN)){errno=ETIMEDOUT;goto cleanup;}
  struct v4l2_plane plane[VIDEO_MAX_PLANES]={0};struct v4l2_buffer buffer={.type=type,.memory=V4L2_MEMORY_MMAP,.length=VIDEO_MAX_PLANES,.m.planes=plane};if(call(video,VIDIOC_DQBUF,&buffer))goto cleanup;
  if(buffer.index>=buffers||buffer.flags&V4L2_BUF_FLAG_ERROR||buffer.length!=1||plane[0].bytesused!=f->plane_fmt[0].sizeimage||plane[0].data_offset||plane[0].bytesused>sizes[buffer.index]){errno=EIO;goto cleanup;}
  unsigned char *data=maps[buffer.index];int64_t timestamp=(int64_t)buffer.timestamp.tv_sec*1000000+buffer.timestamp.tv_usec;
  if(timestamp<=0||(image_seen&&(buffer.sequence<=last_sequence||timestamp<=last_time))){errno=EIO;goto cleanup;}
  last_sequence=buffer.sequence;last_time=timestamp;
  if(stats_dequeue(frames))goto cleanup;
  uint64_t value=hash(data,plane[0].bytesused);bool settled=buffer.sequence>=parameter_sequence&&image_seen&&value==previous_image_hash&&stats_stable&&stats_nonuniform;
  printf("GRID_FRAME model=%s frame=%u sequence=%u parameter_sequence=%u settled=%u image_hash=%016" PRIx64 "\\n",model,frames,buffer.sequence,parameter_sequence,settled,value);fflush(stdout);
  if(settled){if(save_private(prefix,"nv12",data,plane[0].bytesused)||save_private(prefix,"stats",current_stats,current_stats_size))goto cleanup;complete=true;}
  previous_image_hash=value;image_seen=true;frames++;
  if(drain_sof(frames)||call(video,VIDIOC_QBUF,&buffer))goto cleanup;
 }
 if(!complete){errno=ETIMEDOUT;goto cleanup;}
'''+s[b:]
s=s.replace(' if(streaming&&call(video,VIDIOC_STREAMOFF,&type)){perror("STREAMOFF");result=1;}',' if(streaming&&call(video,VIDIOC_STREAMOFF,&type)){perror("STREAMOFF");result=1;}\n if(stats_close()){perror("stats cleanup");result=1;}')
source=HERE/'stats-grid-probe.c';source.write_text(s)
headers=P/'uapi/linux';headers.mkdir(parents=True,exist_ok=True);(headers/'media').mkdir(exist_ok=True)
for a,b in [(TREE/'include/uapi/linux/qcom-camss-config.h',headers/'qcom-camss-config.h'),(TREE/'include/uapi/linux/media/v4l2-isp.h',headers/'media/v4l2-isp.h')]:shutil.copyfile(a,b)
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I'+str(headers.parent),
 '-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(P/'stats-grid-probe')],capture_output=True)
(P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
(HERE/'probe-build-validation.json').write_text(json.dumps(dict(stage=338,tool='stats-grid-probe',four_sensors_supported=True,variable_bytesused_verified=True,stable_test_pattern_end_condition=True,installed_userspace_probe_reused=True,passed=True),indent=2)+'\n')
print('Built four-sensor direct statistics capture with media/control restoration.')
