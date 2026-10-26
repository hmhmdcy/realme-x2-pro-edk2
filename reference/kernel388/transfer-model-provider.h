#define EXPORT_SYMBOL_GPL(x)
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define dev_info(...) ((void)0)
#define IPE_FRAME_PROCESS 6
#define IPE_ASYNC_INDIRECT 0x200
#define IPE_ASYNC_INDIRECT_ACK 0x300
#define REQUEST_IOVA 0x07800000U
#define REQUEST_MAX (1024U*1024U)
#define IMAGE_INPUT_IOVA 0x20000000U
#define IMAGE_OUTPUT_IOVA 0x24000000U
#define IMAGE_WINDOW (64U*1024U*1024U)
struct mutex{bool locked;};
struct camss_a5_fw_memory{void *cpu;u32 bytes,mapped,iova;};
struct camss_a5_nv12_layout{u32 width,height,stride,slice_height;bool uv_swap;};
struct camss_a5_ipe_io{struct camss_a5_nv12_layout input,output;u32 output_port;};
struct camss_a5_session{struct camss_a5 *a5;u32 handle;bool configured;u32 scratch_bytes;struct camss_a5_ipe_io io;};
struct camss_a5{
 struct device *dev;struct mutex lock;
 bool initialized,cpu_enabled,engine_dma_capable,session_uncertain,ipe_dma_pending,request_fw_mapped,command_queued,session_reply;
 struct camss_a5_fw_memory image_input,image_output,request,config,heap,shared,firmware;
 struct camss_a5_dma_image dma_input,dma_output;
 struct camss_a5_session *request_owner;
 u32 frames_submitted,frames_completed,direct_frames,copy_frames,transfer_maps,transfer_unmaps;
 u32 session_opcode,session_header_error,session_payload_status;
 u64 session_cookie,session_cookie2;
 void *table;
};
static struct camss_a5 *active;
static unsigned mode,bo_live,bo_allocations,hw_frames;
static void mutex_lock(struct mutex *m){assert(!m->locked);m->locked=true;}
static void mutex_unlock(struct mutex *m){assert(m->locked);m->locked=false;}
static void capture_shared_state(struct camss_a5 *a){assert(!a->cpu_enabled);}
static void dma_wmb(void){}static void dma_rmb(void){}
static void put_unaligned_le32(u32 value,void *p){memcpy(p,&value,4);}
static void put_unaligned_le64(u64 value,void *p){memcpy(p,&value,8);}
static int camss_a5_iova_memory_alloc(struct device *d,struct camss_a5_fw_memory *m,u32 iova,u32 bytes){
 assert(d==active->dev && !m->cpu);++bo_allocations;if(mode==1)return -ENOMEM;
 m->cpu=calloc(1,bytes);assert(m->cpu);m->bytes=bytes;m->iova=iova;++bo_live;return 0;
}
static int camss_a5_fw_memory_map(struct camss_a5_fw_memory *m){m->mapped=m->bytes;return 0;}
static int camss_a5_fw_memory_unmap(struct camss_a5_fw_memory *m){assert(!active->ipe_dma_pending && !active->request_fw_mapped);m->mapped=0;return 0;}
static int camss_a5_fw_memory_free(struct camss_a5_fw_memory *m){assert(!m->mapped);if(m->cpu){assert(bo_live);--bo_live;free(m->cpu);}memset(m,0,sizeof(*m));return 0;}
static int region_packet_locked(struct camss_a5 *a,struct camss_a5_session *s,struct camss_a5_fw_memory *m,bool map){
 assert(a->lock.locked && s->a5==a && m->cpu);a->command_queued=true;
 return (mode==6 && map)||(mode==8 && !map)?-ETIMEDOUT:0;
}
static int session_token(struct camss_a5 *a){assert(a->lock.locked);a->session_cookie=17;a->session_cookie2=31;return mode==10?-EOVERFLOW:0;}
static void session_command_failed(struct camss_a5 *a,int ret){if(a->command_queued && (ret!=-EREMOTEIO || !a->session_reply))a->session_uncertain=true;}
static int send_packet(struct camss_a5 *a,const void *packet,unsigned bytes,unsigned ack){
 (void)packet;(void)ack;assert(bytes==40 && a->lock.locked && a->ipe_dma_pending && a->request_fw_mapped);
 a->command_queued=mode!=9;
 if(mode==7)return -ETIMEDOUT;
 if(mode==9)return -ENOSPC;
 if(a->dma_output.buffer){
  assert(!a->image_input.cpu && !a->image_output.cpu && mappings==2 && refs==2 && bo_live==1);
  memset(a->dma_output.buffer->cpu+a->dma_output.offset,0x7c,a->dma_output.bytes);
 }else{assert(bo_live==3);memset(a->image_output.cpu,0x7c,a->image_output.bytes);}
 ++hw_frames;return 0;
}
