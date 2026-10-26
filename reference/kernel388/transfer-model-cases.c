static int camss_a5_ipe_bypass_size(const struct camss_a5_ipe_io *io,u32 cores,u32 *bytes){(void)io;(void)cores;*bytes=4096;return 0;}
static int camss_a5_ipe_encode_bypass_striping(void *p,u32 capacity,const struct camss_a5_ipe_io *io,u32 cores,u32 *bytes){(void)p;(void)capacity;(void)io;(void)cores;*bytes=4096;return mode==4?-EINVAL:0;}
static int camss_a5_ipe_encode_bypass_iq(void *p,u32 bytes){(void)p;(void)bytes;return mode==5?-EINVAL:0;}
static int camss_a5_ipe_encode_frame(void *p,u32 bytes,const struct camss_a5_ipe_io *io,const struct camss_a5_ipe_frame *f){
 (void)p;(void)bytes;(void)io;
 assert(f->input.iova==(active->dma_input.buffer?active->dma_input.iova:IMAGE_INPUT_IOVA));
 assert(f->output.iova==(active->dma_output.buffer?active->dma_output.iova:IMAGE_OUTPUT_IOVA));
 return 0;
}
int main(void)
{
 unsigned cases=0;
 for(unsigned scenario=0;scenario<=12;++scenario){
  clean_provider();mode=scenario;bo_live=bo_allocations=hw_frames=0;
  struct iommu_domain domain={true};struct device device={&domain};
  struct page ip={0x100000},op={0x900000};
  struct scatterlist is={&ip,462848,0,0x30000000,462848},os={&op,462848,0,0x40000000,462848};
  struct sg_table it={&is,1,1},ot={&os,1,1};struct dma_buf ib,ob;init_buffer(&ib,&it,462848);init_buffer(&ob,&ot,462848);
  ib.cpu=malloc(462848);ob.cpu=malloc(462848);assert(ib.cpu && ob.cpu);memset(ib.cpu,0x2a,462848);memset(ob.cpu,0xa5,462848);
  struct camss_a5 a={.dev=&device,.initialized=true,.cpu_enabled=true,.engine_dma_capable=true};active=&a;
  struct camss_a5_session session={.a5=&a,.handle=1,.configured=true,.scratch_bytes=4096,
   .io={.input={640,480,640,480,false},.output={640,480,640,480,false},.output_port=8}};
  struct camss_a5_ipe_job job={.input_dma=&ib,.output_dma=&ob,.input_offset=16,.input_bytes=460800,.output_bytes=460800,.bl_bytes=4096,.request_id=1,.max_cores=2,.target_time_ns=1000000};
  if(scenario==2)ib.resv->waited=0;
  if(scenario==3)os.page=is.page;
  if(scenario==11){job.input=ib.cpu;job.output=ob.cpu;job.input_dma=job.output_dma=NULL;job.input_offset=0;}
  if(scenario==12)job.input=ib.cpu; /* mixed interface must be rejected */
  int ret=camss_a5_ipe_run(&a,&session,&job);
  int expected=scenario==0 || scenario==11?0:scenario==1?-ENOMEM:scenario==2 || scenario==6 || scenario==7 || scenario==8?-ETIMEDOUT:scenario==9?-ENOSPC:scenario==10?-EOVERFLOW:-EINVAL;
  assert(ret==expected);
  bool completed=scenario==0 || scenario==8 || scenario==11;
  assert(a.frames_completed==(unsigned)completed);
  assert(a.direct_frames==(unsigned)(completed && scenario!=11) && a.copy_frames==(unsigned)(scenario==11));
  bool retained=scenario==6 || scenario==7 || scenario==8;
  if(retained){
   assert(camss_a5_backing_owned(&a) && refs==2 && mappings==2 && attachments==2 && bo_live==1 && a.dma_input.buffer && a.dma_output.buffer);
   /* Dropping the queue/caller references must not retire imported backing. */
   --ib.refs;--ob.refs;assert(ib.refs==1 && ob.refs==1);
   assert(free_transfer_memory(&a)==-EBUSY);
   assert(free_memory(&a)==-EBUSY && refs==2 && mappings==2);
   a.cpu_enabled=false;
   /* Failed engine quiesce keeps pending or firmware ownership intact. */
   assert(free_memory(&a)==-EBUSY && refs==2 && mappings==2);
   a.ipe_dma_pending=false;a.request_fw_mapped=false;a.request_owner=NULL;a.session_uncertain=false;
   assert(!free_memory(&a) && !camss_a5_backing_owned(&a) && !ib.refs && !ob.refs);
  }else{assert(!bo_live && !refs && !mappings && !attachments && !camss_a5_backing_owned(&a));}
  assert(!allocations);
  if(completed)for(unsigned i=0;i<460800;++i)assert(ob.cpu[i]==0x7c);
  if(!completed)for(unsigned i=0;i<460800;++i)assert(ob.cpu[i]==0xa5);
  free(ib.cpu);free(ob.cpu);++cases;
 }
 clean_provider();printf("TRANSFER_MODEL cases=%u passed=1\n",cases);return 0;
}
