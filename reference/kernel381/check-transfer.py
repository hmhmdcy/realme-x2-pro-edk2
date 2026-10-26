from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'transfer-regression';work.mkdir(exist_ok=True)
s=(P/'camss-icp-a5-boot.c.proposed').read_text();header=(P/'camss-icp-a5-boot.h.proposed').read_text();ipe=(P/'camss-icp-a5-ipe.h.proposed').read_text()
strip=lambda text:'\n'.join(line for line in text.splitlines() if not line.startswith('#include'))
(work/'model-header.h').write_text(strip(header)+'\n'+strip(ipe))
parts=['\n'.join(line for line in s.splitlines() if line.startswith('#define '))]
for start,end in [('static void command_failure(','static irqreturn_t a5_interrupt('),('static void process_message(','static irqreturn_t a5_interrupt_thread('),('static int send_packet(','bool camss_a5_backing_owned('),('static int quiesce_locked(','int camss_a5_stop(')]:
 a=s.index(start);b=s.index(end,a);parts.append(s[a:b])
(work/'body.inc').write_text('\n'.join(parts))
a=s.rindex('static int free_transfer_memory(')
free_start=s.index('static int free_memory(');free_end=s.index('static int prepare_memory(',free_start)
actual_free=s[free_start:free_end].replace('static int free_memory(','static int free_memory_actual(',1)
(work/'extra-frame-body.inc').write_text(strip((HERE.parent/'kernel380/camss-icp-a5-ipe.c').read_text())+'\n'+s[a:]+'\n'+actual_free)
fixture=(HERE/'session-regression.c').read_text().replace('typedef uint32_t u32;','typedef uint16_t u16;typedef uint32_t u32;').replace('reply[64]','reply[96]')
fixture=fixture.replace('static void dma_wmb(void){}','static void dma_wmb(void){}\nstatic void dma_rmb(void){}\n#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))\n#define PAGE_SIZE 4096U\n#define PAGE_ALIGN(x) (((x)+4095)&~4095ULL)\nstatic u16 get_unaligned_le16(const void *p){u16 v;memcpy(&v,p,2);return v;}\nstatic void *memchr_inv(const void *p,int value,size_t n){const u8 *b=p;for(size_t i=0;i<n;i++)if(b[i]!=(u8)value)return (void*)(b+i);return NULL;}')
fixture=fixture.replace('static int free_memory(struct camss_a5 *a){assert(!a->cpu_enabled && !a->irq_enabled);backing=false;++free_calls;return 0;}','static int free_memory_actual(struct camss_a5 *a);\nstatic int free_memory(struct camss_a5 *a){assert(!a->cpu_enabled && !a->irq_enabled);int ret=free_memory_actual(a);if(ret)return ret;backing=false;++free_calls;return 0;}')
fixture=fixture.replace(' if(mode==4 ||',' if((mode==51 && get_unaligned_le32((u8 *)p+8)==6)||mode==4 ||')
providers=r'''
static unsigned allocations,mappings,live_allocations,unmap_failure_seen;
static int camss_a5_iova_memory_alloc(struct device *dev,struct camss_a5_fw_memory *m,u32 iova,u32 bytes){
 assert(dev==active->dev && !m->cpu && !(bytes&4095) && bytes);allocations++;
 if(mode>=60 && mode<=62 && allocations==mode-59)return -ENOMEM;
 m->cpu=calloc(1,bytes);assert(m->cpu);m->iova=iova;m->bytes=bytes;live_allocations++;return 0;
}
static int camss_a5_fw_memory_map(struct camss_a5_fw_memory *m){
 assert(m->cpu && !m->mapped);mappings++;m->mapped=m->bytes;
 if(mode>=63 && mode<=65 && mappings==mode-62){m->mapped=4096;return -EIO;}return 0;
}
static int camss_a5_fw_memory_unmap(struct camss_a5_fw_memory *m){
 assert(!active->ipe_dma_pending && !active->request_fw_mapped);
 if(mode==66 && m->cpu && !unmap_failure_seen++){return -EIO;}m->mapped=0;return 0;
}
static int camss_a5_fw_memory_free(struct camss_a5_fw_memory *m){
 assert(!m->mapped);if(m->cpu && (m==&active->request || m==&active->image_input || m==&active->image_output)){free(m->cpu);assert(live_allocations);live_allocations--;}memset(m,0,sizeof(*m));return 0;
}
'''
fixture=fixture.replace('#include "body.inc"',providers+'\n#include "body.inc"\n#include "extra-frame-body.inc"')
anchor='assert(get_unaligned_le32(last_packet+44)==1 && get_unaligned_le32(last_packet+48)==CONFIG_IOVA && get_unaligned_le32(last_packet+52)==4096);'
assert fixture.count(anchor)==1
fixture=fixture.replace(anchor,'''bool transfer=get_unaligned_le32(last_packet+48)==REQUEST_IOVA;
  assert(get_unaligned_le32(last_packet+44)==1 && get_unaligned_le32(last_packet+48)==(transfer?REQUEST_IOVA:CONFIG_IOVA) && get_unaligned_le32(last_packet+52)==(transfer?active->request.bytes:4096));
  if(transfer && mode==59 && opcode==IPE_MEM_MAP)return 0;''')
anchor='if((mode==32 && opcode==IPE_MEM_MAP)||(mode==36 && opcode==IPE_MEM_UNMAP))'
assert fixture.count(anchor)==1
fixture=fixture.replace(anchor,'if((transfer && mode==58 && opcode==IPE_MEM_MAP)||(transfer && mode==57 && opcode==IPE_MEM_UNMAP)||(mode==32 && opcode==IPE_MEM_MAP)||(mode==36 && opcode==IPE_MEM_UNMAP))')
anchor=' }else if(command==IPE_ASYNC_INDIRECT){';assert fixture.count(anchor)==1
fixture=fixture.replace(anchor,anchor+r'''
  if(get_unaligned_le32(last_packet+8)==IPE_FRAME_PROCESS){
   assert(last_bytes==40 && get_unaligned_le32(last_packet+36)==REQUEST_IOVA && active->request_fw_mapped && active->ipe_dma_pending && live_allocations==3);
   assert(active->request.mapped==active->request.bytes && active->image_input.mapped==active->image_input.bytes && active->image_output.mapped==active->image_output.bytes);
   assert(get_unaligned_le32(active->request.cpu+92)==IMAGE_INPUT_IOVA && get_unaligned_le32(active->request.cpu+220)==IMAGE_OUTPUT_IOVA);
   memset(active->image_output.cpu,0x7c,640*480*3/2);
   if(mode==52)return 0;
   bytes=mode==55?56:mode==67?76:72;put_unaligned_le32(IPE_ASYNC_INDIRECT_ACK,reply+4);put_unaligned_le32(IPE_FRAME_PROCESS,reply+8);memcpy(reply+12,last_packet+12,16);
   put_unaligned_le32(mode==53?7:0,reply+28);put_unaligned_le32(mode==54?0xa0001:0,reply+32);
   if(mode==56){reply[12]^=1;put_unaligned_le32(bytes,reply);memcpy(active->message,reply,bytes);process_message(active,bytes);assert(!c->done);return 0;}
   goto deliver;
  }
''')
anchor=' if(mode==10)bytes=28;';assert fixture.count(anchor)==1;fixture=fixture.replace(anchor,'deliver:\n'+anchor)
anchor=' if(scenario==45){';assert fixture.count(anchor)==1
main=r'''
 if(scenario>=50){
  assert(scenario<=73);a.engine_dma_capable=true;mode=0;
  u8 config[4096];a.config.cpu=config;a.config.bytes=a.config.mapped=4096;a.config.iova=CONFIG_IOVA;
  struct camss_a5_ipe_io io={.input={640,480,640,480,false},.output={640,480,640,480,false},.output_port=8};
  assert(!camss_a5_ipe_create(&a,&one,2) && !camss_a5_ipe_configure_nv12(&a,&one,&io));
  u8 *input=malloc(460800),*output=malloc(460800),stripe[2892]={0},iq[2584]={0};assert(input && output);memset(input,0x2a,460800);memset(output,0xa5,460800);
  put_unaligned_le32(1,stripe+20);u16 stripe_count=1;memcpy(stripe+428,&stripe_count,2);
  struct camss_a5_ipe_job job={.striping=stripe,.iq=iq,.input=input,.output=output,.striping_bytes=sizeof(stripe),.iq_bytes=sizeof(iq),.input_bytes=460800,.output_bytes=460800,.bl_bytes=156512,.request_id=1,.max_cores=1,.target_time_ns=1000000};
  mode=scenario;if(scenario==68)iq[0]=1;if(scenario==69)a.engine_dma_capable=false;if(scenario==70)job.input_bytes=1;if(scenario==71)job.striping_bytes=2268;if(scenario==72)job.bl_bytes=2*REQUEST_MAX;if(scenario==73){one.io.input.width=one.io.input.stride=10000;one.io.input.height=one.io.input.slice_height=10000;}
  ret=camss_a5_ipe_run(&a,&one,&job);
  bool uncertain=(scenario>=52 && scenario<=56)||scenario==58||scenario==59||scenario==67;
  bool pending=(scenario>=52 && scenario<=56)||scenario==67;
  int expected=scenario==50?0:scenario==51?-ENOSPC:scenario==52||scenario==56||scenario==59?-ETIMEDOUT:scenario==53||scenario==54||scenario==57||scenario==58?-EREMOTEIO:scenario==55||scenario==67?-EPROTO:scenario>=60&&scenario<=62?-ENOMEM:scenario>=63&&scenario<=66?-EIO:scenario==68?-EOPNOTSUPP:scenario==69?-ENODEV:-EINVAL;
  assert(ret==expected && a.session_uncertain==uncertain && a.ipe_dma_pending==pending);
  bool copied=scenario==50||scenario==57||scenario==66;assert(a.frames_completed==(unsigned)copied);
  for(unsigned i=0;i<460800;i++)assert(output[i]==(copied?0x7c:0xa5));
  if(uncertain || scenario==57 || scenario==66){assert(live_allocations==3 && a.request.cpu && a.image_input.cpu && a.image_output.cpu);}else assert(!live_allocations && !a.request.cpu && !a.image_input.cpu && !a.image_output.cpu);
  if(pending){ipe_reset_error=1;assert(model_stop(&a)==-ETIMEDOUT && a.ipe_dma_pending && live_allocations==3 && a.power_held && backing);ipe_reset_error=0;}
  mode=0;assert(!model_stop(&a) && !live_allocations && !a.ipe_dma_pending && !a.request_fw_mapped && !a.power_held && !backing);free(input);free(output);return 0;
 }
'''
fixture=fixture.replace(anchor,main+anchor);(work/'probe.c').write_text(fixture)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);(work/'build-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
rows=[]
for case in range(50,74):
 q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10);(work/(str(case)+'-private.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(case,q.stderr.decode());rows.append(dict(case=case,passed=True))
report=dict(stage=381,actual_transfer_region_encoder_parser_send_stop_and_global_dma_retirement_bodies=True,asan_ubsan=True,tests=rows,
 queued_uncertain_frame_retains_all_three_buffers_and_pm=True,engine_reset_failure_preserves_dma_backing=True,engine_reset_retry_precedes_dma_unmap=True,
 successful_72_byte_completion_required_before_output_copy=True,invalid_reply_length_status_tokens_and_timeout_checked=True,
 firmware_unmap_rejection_and_partial_dma_alloc_map_unmap_failures_checked=True,nonzero_unvalidated_iq_rejected=True,
 iommu_irq_engine_dma_scheduler_and_mmio_providers_modelled=True,no_hardware_image_claim=True,passed=True)
(HERE/'transfer-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
