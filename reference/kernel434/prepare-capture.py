"""Reuse the verified FULL/PD10 probe and add GTM receipts/statistics capture."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
t=(HERE.parent/'kernel428/ds4-capture.c').read_text()
def change(old,new):
 global t
 assert t.count(old)==1,old;t=t.replace(old,new)
change('/* Bounded FULL/DS4 transport probe. OEM coefficients stay in a private packet. */','/* Bounded GTM hardware probe. Factory tables stay in private input packets. */')
t=t.replace('q->type==V4L2_BUF_TYPE_META_OUTPUT?','(q->type==V4L2_BUF_TYPE_META_OUTPUT||q->type==V4L2_BUF_TYPE_META_CAPTURE)?')
insert='''
static unsigned char base_packet[4096];static size_t base_size;
static struct camss_params_ife_gtm gtms[9];static const unsigned scene_packets[]={0,3,7};
static unsigned packet_index(unsigned phase,bool scene){return scene?scene_packets[phase]:phase;}
static int gtm_queue(struct queue *params,unsigned phase,bool scene){
 const struct camss_params_ife_gtm *g=&gtms[packet_index(phase,scene)];
 memcpy(params->map[0],base_packet,base_size);memcpy((char*)params->map[0]+base_size,g,sizeof(*g));
 struct v4l2_isp_buffer *b=params->map[0];b->data_size=base_size-sizeof(*b)+sizeof(*g);params->size=base_size+sizeof(*g);
 if(enqueue(params,0))return -1;
 memset((char*)params->map[0]+sizeof(*b),0,params->size-sizeof(*b));
 printf("GTM_PARAM_Q phase=%u packet=%u cookie=%" PRIu64 " enabled=%u bytes=%zu mutated_after_queue=1\\n",phase,packet_index(phase,scene),(uint64_t)g->cookie,g->enabled,params->size);return 0;
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
 printf("GTM_STATS phase=%u sequence=%u timestamp_us=%" PRId64 " bytes=%u cookie=%" PRIu64 " generation=%" PRIu64 " status=%u bank=%u population=%" PRIu64 "\\n",phase,b->sequence,(int64_t)b->timestamp.tv_sec*1000000+b->timestamp.tv_usec,b->bytesused,*cookie,*generation,*status,*bank,sum);
 return dump(root,"stats",b->sequence,data,b->bytesused);
}
'''
change('int main(int argc,char **argv) {',insert+'\nint main(int argc,char **argv) {')
change(' bool full_only=getenv("DS4_CAPTURE_FULL_ONLY")!=NULL;',' bool scene=atoi(argv[2])==0;unsigned phases=scene?3:9;')
change('if(!model)model="s5k3m5";','if(!model)model="s5kgw1";')
change('struct queue full={.fd=-1,.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE},ds={.fd=-1,.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE},params={.fd=-1,.type=V4L2_BUF_TYPE_META_OUTPUT};','struct queue full={.fd=-1,.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE},ds={.fd=-1,.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE},params={.fd=-1,.type=V4L2_BUF_TYPE_META_OUTPUT},stats={.fd=-1,.type=V4L2_BUF_TYPE_META_CAPTURE};')
change('ds4={0},pa={0};','ds4={0},pa={0},st={0};')
change('if(!strcmp(e.name,"msm_vfe0_params"))pa=e;','if(!strcmp(e.name,"msm_vfe0_params"))pa=e;if(!strcmp(e.name,"msm_vfe0_stats"))st=e;')
change('!ds4.id||!pa.id','!ds4.id||!pa.id||!st.id')
change('params.fd=open_entity(&pa,false);','params.fd=open_entity(&pa,false);stats.fd=open_entity(&st,false);')
change('ds.fd<0||params.fd<0','ds.fd<0||params.fd<0||stats.fd<0')
a=t.index(' unsigned char bytes[4096];');z=t.index(' if(full.count!=4',a)
t=t[:a]+''' base_size=fread(base_packet,1,sizeof(base_packet),f);fclose(f);if(base_size!=56)goto done;
 params.size=base_size+sizeof(struct camss_params_ife_gtm);if(allocate(&params,1))goto done;
 snprintf(packet,sizeof(packet),"%s/gtm-packets-private.bin",argv[1]);f=fopen(packet,"rb");if(!f)goto done;
 bool valid=fread(gtms,sizeof(gtms),1,f)==1&&fgetc(f)==EOF;fclose(f);if(!valid)goto done;
 for(unsigned i=0;i<9;i++)if(gtms[i].header.type!=CAMSS_PARAMS_IFE_GTM||gtms[i].header.flags||gtms[i].header.size!=sizeof(gtms[i])||!gtms[i].cookie||gtms[i].enabled>1||gtms[i].reserved)goto done;
 if(gtm_queue(&params,0,scene))goto done;
 struct v4l2_format sf={.type=stats.type};if(call(stats.fd,VIDIOC_G_FMT,&sf)||sf.fmt.meta.dataformat!=V4L2_META_FMT_QCOM_ISP_STATS)goto done;
 stats.size=sf.fmt.meta.buffersize;if(stats.size<sizeof(struct v4l2_isp_buffer)+sizeof(struct camss_stats_bhist)||allocate(&stats,4))goto done;
 for(unsigned i=0;i<stats.count;i++)if(enqueue(&stats,i))goto done;
'''+t[z:]
a=t.index(' phase="streamon";');z=t.index('\ndone:',a)
t=t[:a]+''' phase="streamon";if(stream(&params,true)||stream(&stats,true)||stream(&ds,true)||stream(&full,true))goto done;
 phase="capture";unsigned step=0,accepted=0;bool parameter_pending=true;time_t start=time(NULL);
 while(!interrupted&&time(NULL)-start<24){
  struct pollfd p[5]={{.fd=full.fd,.events=POLLIN},{.fd=ds.fd,.events=POLLIN},{.fd=vfe,.events=POLLPRI},{.fd=stats.fd,.events=POLLIN},{.fd=parameter_pending?params.fd:-1,.events=POLLOUT}};
  int ready=poll(p,5,3000);if(ready<=0)goto done;
  for(unsigned k=0;k<5;k++)if(p[k].revents&(POLLERR|POLLHUP|POLLNVAL)){printf("GTM_POLL_ERROR slot=%u events=%#x\\n",k,p[k].revents);goto done;}
  if(p[2].revents&POLLPRI){struct v4l2_event ev;while(!ioctl(vfe,VIDIOC_DQEVENT,&ev))printf("SOF sequence=%u\\n",ev.u.frame_sync.frame_sequence);}
  if(p[4].revents&POLLOUT){
   struct v4l2_buffer b={.type=params.type,.memory=V4L2_MEMORY_MMAP};if(call(params.fd,VIDIOC_DQBUF,&b)||b.index||b.flags&V4L2_BUF_FLAG_ERROR)goto done;
   parameter_pending=false;printf("GTM_PARAM_DQ phase=%u sequence=%u timestamp_us=%" PRId64 "\\n",step,b.sequence,(int64_t)b.timestamp.tv_sec*1000000+b.timestamp.tv_usec);
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
   printf("GTM_FRAME kind=%s phase=%u sequence=%u timestamp_us=%" PRId64 " bytes=%u hash=%016" PRIx64 " active_hash=%016" PRIx64 "\\n",k?"ds4":"full",step,b.sequence,(int64_t)b.timestamp.tv_sec*1000000+b.timestamp.tv_usec,pl.bytesused,hash(data,q->size),active_hash);
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
   printf("GTM_PHASE_DONE phase=%u matched_stats=%u\\n",step,accepted);step++;accepted=0;
   if(step==phases){result=0;break;}
   if(gtm_queue(&params,step,scene))goto done;parameter_pending=true;
  }
 }
'''+t[z:]
change('cleanup(&ds);cleanup(&params);cleanup(&full);','cleanup(&stats);cleanup(&ds);cleanup(&params);cleanup(&full);')
change('printf("DS4_RESULT result=%d phase=%s full_frames=%u ds4_frames=%u interrupted=%d\\n",result,phase,full.frames,ds.frames,interrupted);','printf("GTM_RESULT result=%d phase=%s full_frames=%u ds4_frames=%u stats_frames=%u interrupted=%d\\n",result,phase,full.frames,ds.frames,stats.frames,interrupted);')
(HERE/'gtm-capture.c').write_text(t)
print('GTM capture source prepared')
