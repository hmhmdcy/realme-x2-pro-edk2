#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <errno.h>
typedef uint32_t u32;typedef uint64_t u64;typedef uint8_t u8;typedef uint32_t __le32;typedef uint64_t phys_addr_t;
#define U64_MAX UINT64_MAX
#define U32_MAX UINT32_MAX
#define BIT(n) (1U<<(n))
#define __iomem
#define EXPORT_SYMBOL_GPL(x)
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define cpu_to_le32(x) (x)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define max(a,b) ((a)>(b)?(a):(b))
#define msecs_to_jiffies(x) (x)
#define dev_info(...) ((void)0)
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
struct list_head {struct list_head *next,*prev;};
#define INIT_LIST_HEAD(h) ((h)->next=(h),(h)->prev=(h))
static void list_add_tail(struct list_head *n,struct list_head *h){n->prev=h->prev;n->next=h;h->prev->next=n;h->prev=n;}
static void list_del_init(struct list_head *n){n->prev->next=n->next;n->next->prev=n->prev;INIT_LIST_HEAD(n);}
#define list_for_each_entry(p,h,m) for(p=container_of((h)->next,__typeof__(*p),m);&(p)->m!=(h);p=container_of((p)->m.next,__typeof__(*p),m))
#define list_for_each_entry_safe(p,n,h,m) for(p=container_of((h)->next,__typeof__(*p),m),n=container_of((p)->m.next,__typeof__(*p),m);&(p)->m!=(h);p=n,n=container_of((n)->m.next,__typeof__(*n),m))
struct completion{unsigned done;};struct mutex{unsigned held;};struct hrtimer{unsigned armed;};typedef int spinlock_t;
struct camss_a5_resources {void *sierra;unsigned enabled_groups,held_domains;};
struct camss_a5_fw_memory {void *cpu;unsigned bytes,mapped,iova;};
struct camss_a5_ring{unsigned unused;};struct camss_a5_qtable;struct device;struct reset_control;struct platform_device;struct firmware;
#define CAMSS_A5_QUEUE_COUNT 3
#define CAMSS_A5_CMD 0
#include "model-header.h"
static void mutex_lock(struct mutex *m){assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=0;}
static void reinit_completion(struct completion *c){c->done=0;}
static void complete(struct completion *c){c->done++;}
static void dma_wmb(void){}
static u32 get_unaligned_le32(const void *p){u32 x;memcpy(&x,p,4);return x;}
static u64 get_unaligned_le64(const void *p){u64 x;memcpy(&x,p,8);return x;}
static void put_unaligned_le32(u32 x,void *p){memcpy(p,&x,4);}
static void put_unaligned_le64(u64 x,void *p){memcpy(p,&x,8);}
static struct camss_a5 *active;
static unsigned writes,joins,resets,pm_calls,free_calls,pc_commands,mode,reset_error;
static u32 registers[256],last_handle=100;
static u8 last_packet[64],reply[64];static unsigned last_bytes;
static bool backing=true;
static void hrtimer_cancel(struct hrtimer *t){t->armed=0;}
static u32 readl(void *p){return *(u32 *)p;}
static void writel(u32 v,void *p){*(u32 *)p=v;}
static void disable_irq(int irq){(void)irq;}
static int reset_control_assert(struct reset_control *r){(void)r;++resets;return reset_error ? -EBUSY : 0;}
#define readl_poll_timeout(addr,value,condition,interval,timeout) ({(void)(interval);(void)(timeout);value=readl(addr);(condition)?0:-ETIMEDOUT;})
static void capture_shared_state(struct camss_a5 *a){assert(!a->cpu_enabled);}
static int free_memory(struct camss_a5 *a){assert(!a->cpu_enabled && !a->irq_enabled);backing=false;++free_calls;return 0;}
static int pm_runtime_put_sync_suspend(struct device *d){(void)d;assert(!backing);++pm_calls;return 0;}
static int camss_a5_ring_write(struct camss_a5_ring *r,const void *p,size_t n){
 assert(active->lock.held && r==&active->rings[0]);assert(get_unaligned_le32(p)==n && n<=sizeof(last_packet));
 if(mode==4 || (mode==31 && get_unaligned_le32((u8 *)p+8)==14))return -ENOSPC;
 memcpy(last_packet,p,n);last_bytes=n;++writes;return 0;
}
static unsigned wait_for_completion_timeout(struct completion *c,unsigned timeout);
static void command_failure(struct camss_a5 *a,int error);
static void synchronize_irq(int irq){(void)irq;++joins;assert(!active->expected);if(mode==26){active->watchdogs++;command_failure(active,-EIO);}}
#include "body.inc"
static int model_stop(struct camss_a5 *a){mutex_lock(&a->lock);int r=stop_locked(a);mutex_unlock(&a->lock);return r;}
static unsigned wait_for_completion_timeout(struct completion *c,unsigned timeout){
 (void)timeout;u32 command=get_unaligned_le32(last_packet+4);unsigned bytes=0;memset(reply,0,sizeof(reply));
 if(mode==7 || mode==16)return 0;
 if(mode==23){active->watchdogs++;command_failure(active,-EIO);return 1;}
 if(mode==25){active->watchdogs++;command_failure(active,-EIO);}
 if(command==IPE_ASYNC_DIRECT && get_unaligned_le32(last_packet+8)!=IPE_DESTROY){
  u32 opcode=get_unaligned_le32(last_packet+8);assert(last_bytes==56 && (opcode==IPE_MEM_MAP || opcode==IPE_MEM_UNMAP));
  assert(get_unaligned_le32(last_packet+44)==1 && get_unaligned_le32(last_packet+48)==CONFIG_IOVA && get_unaligned_le32(last_packet+52)==4096);
  if(mode==41 && opcode==IPE_MEM_UNMAP)return 0;
  bytes=44;put_unaligned_le32(IPE_ASYNC_DIRECT_ACK,reply+4);put_unaligned_le32(opcode,reply+8);memcpy(reply+12,last_packet+12,16);
  if((mode==32 && opcode==IPE_MEM_MAP)||(mode==36 && opcode==IPE_MEM_UNMAP))put_unaligned_le32(7,reply+28);
 }else if(command==IPE_ASYNC_INDIRECT){
  assert(last_bytes==40 && get_unaligned_le32(last_packet+8)==IPE_CONFIG_IO && get_unaligned_le32(last_packet+36)==CONFIG_IOVA);
  assert(active->config_fw_mapped && active->config_owner && get_unaligned_le32(active->config.cpu)==20 && get_unaligned_le32(active->config.cpu+8*84)==20);
  if(mode==35)return 0;
  bytes=mode==40?48:56;put_unaligned_le32(IPE_ASYNC_INDIRECT_ACK,reply+4);put_unaligned_le32(IPE_CONFIG_IO,reply+8);memcpy(reply+12,last_packet+12,16);
  put_unaligned_le32(mode==33?7:0,reply+28);put_unaligned_le32(mode==34?0xa0001:0,reply+32);put_unaligned_le32(65536,reply+36);
 }else if(command==IPE_CREATE){
  assert(last_bytes==28 && (get_unaligned_le32(last_packet+8)==2 || get_unaligned_le32(last_packet+8)==3));
  bytes=32;put_unaligned_le32(IPE_CREATE_ACK,reply+4);put_unaligned_le32(mode==5?7:0,reply+8);
  put_unaligned_le32(mode==6?0:mode==17?last_handle:++last_handle,reply+12);
  memcpy(reply+16,last_packet+12,16);
 }else if(command==IPE_ASYNC_DIRECT){
  assert(last_bytes==44 && get_unaligned_le32(last_packet+8)==8 && get_unaligned_le32(last_packet+28)==1);
  bool found=false;struct camss_a5_session *s;
  list_for_each_entry(s,&active->sessions,node)if(s->handle==get_unaligned_le32(last_packet+32))found=true;
  assert(found && get_unaligned_le64(last_packet+36)==active->session_cookie);
  bytes=48;put_unaligned_le32(IPE_ASYNC_DIRECT_ACK,reply+4);put_unaligned_le32(mode==13?7:8,reply+8);
  memcpy(reply+12,last_packet+12,16);put_unaligned_le32(mode==11?7:0,reply+28);put_unaligned_le32(mode==12?0xa0001:0,reply+32);
  if(mode==21)bytes=44;
 }else if(command==SYS_PC_PREP){assert(last_bytes==8);++pc_commands;bytes=12;put_unaligned_le32(PC_DONE,reply+4);
 }else if(command==SYS_INIT){assert(last_bytes==8);bytes=16;put_unaligned_le32(INIT_DONE,reply+4);
 }else if(command==SYS_PING){assert(last_bytes==16);bytes=16;put_unaligned_le32(PING_ACK,reply+4);memcpy(reply+8,last_packet+8,8);
 }else assert(0);
 if(mode==10)bytes=28;
 if(mode==20)bytes=36;
 put_unaligned_le32(bytes,reply);
 if(mode==22)put_unaligned_le32(bytes-4,reply);
 if(mode==8 || mode==9 || mode==19){
  unsigned bad=mode==19?31:23;
  assert(command==IPE_CREATE);reply[bad]^=0x80;memcpy(active->message,reply,bytes);process_message(active,bytes);assert(!c->done && !active->session_reply && !active->protocol_errors);
  if(mode==8)return 0;reply[bad]^=0x80;
  put_unaligned_le32(PING_ACK,reply+4);memcpy(active->message,reply,bytes);process_message(active,bytes);assert(!c->done);
  put_unaligned_le32(IPE_CREATE_ACK,reply+4);
 }
 memcpy(active->message,reply,bytes);process_message(active,bytes);assert(c->done==(mode==25?2U:1U));return 1;
}
int main(int argc,char **argv){
 assert(argc==2);unsigned scenario=atoi(argv[1]);struct camss_a5 a={0};struct camss_a5_session one={0},two={0},foreign={0};u8 message[4096];
 active=&a;a.resources.sierra=registers;a.message=message;a.initialized=true;a.cpu_enabled=true;a.irq_enabled=true;a.power_held=true;INIT_LIST_HEAD(&a.sessions);registers[A5_STATUS/4]=A5_WFI;
 int ret;unsigned before;
 if(scenario==1){assert(camss_a5_ipe_create(&a,&one,1)==-EINVAL && !writes);return 0;}
 if(scenario==2){a.initialized=false;assert(camss_a5_ipe_create(&a,&one,2)==-ENODEV && !writes);return 0;}
 if(scenario==14){assert(camss_a5_ipe_destroy(&a,&foreign)==-ENOENT && !writes);return 0;}
 if(scenario==18){a.session_sequence=U64_MAX;assert(camss_a5_ipe_create(&a,&one,2)==-EOVERFLOW && !writes);return 0;}
 if(scenario==24){mutex_lock(&a.lock);assert(!send_command(&a,SYS_INIT,INIT_DONE) && a.init_done);a.ping_cookie=0x11223344aabbccddULL;assert(!send_command(&a,SYS_PING,PING_ACK) && a.ping_done);assert(!send_command(&a,SYS_PC_PREP,PC_DONE) && a.pc_done);assert(writes==3 && joins==3);mutex_unlock(&a.lock);return 0;}
 if(scenario==43){
  u32 f[11];u8 out[1216];while(fread(f,sizeof(u32),11,stdin)==11){
   struct camss_a5_ipe_io io={.input={f[0],f[1],f[2],f[3],f[4]},.output={f[5],f[6],f[7],f[8],f[9]},.output_port=f[10]};
   assert(!encode_ipe_io(out,sizeof(out),&io));assert(fwrite(out,1,sizeof(out),stdout)==sizeof(out));
  }return 0;
 }
 if(scenario==44){
  for(unsigned bad=0;bad<13;bad++){
   u8 out[1216],saved[1216];memset(out,0xa5,sizeof(out));memcpy(saved,out,sizeof(out));
   struct camss_a5_ipe_io io={.input={640,480,640,480,false},.output={640,480,640,480,false},.output_port=8};
   if(bad==3)io.input.width=639;if(bad==4)io.output.height=479;if(bad==5)io.input.stride=638;
   if(bad==6)io.output.slice_height=478;if(bad==7)io.input.stride=641;if(bad==8)io.input.slice_height=481;
   if(bad==9){io.input.stride=U32_MAX-1;io.input.slice_height=U32_MAX-1;}
   if(bad==10)io.output_port=0;if(bad==11)io.input.width=0;if(bad==12)io.output.height=0;
   assert(encode_ipe_io(bad==0?NULL:out,bad==1?1215:1216,bad==2?NULL:&io)==-EINVAL && !memcmp(out,saved,sizeof(out)));
  }return 0;
 }
 if(scenario>=30){
  u8 config[4096];a.config.cpu=config;a.config.bytes=a.config.mapped=4096;a.config.iova=CONFIG_IOVA;
  struct camss_a5_ipe_io io={.input={640,480,640,480,false},.output={640,480,640,480,false},.output_port=8};
  assert(!camss_a5_ipe_create(&a,&one,2));mode=scenario;
  if(scenario==37)io.input.width=639;
  if(scenario==38)a.config.mapped=0;
  ret=camss_a5_ipe_configure_nv12(&a,scenario==39?&foreign:&one,&io);
  if(scenario==30){assert(!ret && a.io_configs==1 && a.config_maps==1 && a.config_unmaps==1 && !a.config_fw_mapped && !a.config_owner && one.configured && one.scratch_bytes==65536);}
  else if(scenario==31 || scenario==37 || scenario==38 || scenario==39){assert(ret==(scenario==31?-ENOSPC:scenario==39?-ENODEV:-EINVAL) && !a.config_fw_mapped && !a.session_uncertain && !a.io_configs);}
  else if(scenario==33 || scenario==34){assert(ret==-EREMOTEIO && !a.config_fw_mapped && !a.session_uncertain && !one.configured && a.config_maps==1 && a.config_unmaps==1);}
  else if(scenario==36){assert(ret==-EREMOTEIO && a.config_fw_mapped && a.config_owner==&one && !a.session_uncertain && !one.configured && a.io_configs==1);}
  else if(scenario==32 || scenario==35 || scenario==40 || scenario==41){
   assert(ret==(scenario==32?-EREMOTEIO:scenario==40?-EPROTO:-ETIMEDOUT) && a.session_uncertain && a.config_fw_mapped && a.config_owner==&one);
   mode=0;reset_error=1;assert(model_stop(&a)==-EBUSY && a.config_fw_mapped && a.config_owner==&one && a.cpu_enabled && a.power_held && backing && one.a5==&a);
   reset_error=0;assert(!model_stop(&a) && !a.config_fw_mapped && !a.config_owner && !one.a5 && !a.cpu_enabled && !a.power_held);return 0;
  }else assert(0);
  mode=0;assert(!camss_a5_ipe_destroy(&a,&one) && !a.config_fw_mapped && !a.config_owner);
  assert(!model_stop(&a) && !resets && !a.cpu_enabled && !a.power_held && !a.session_count);return 0;
 }
 mode=scenario;
 if(scenario==3 || scenario==11 || scenario==12 || scenario==13 || scenario==15 || scenario==16 || scenario==17 || scenario==21)mode=0;
 ret=camss_a5_ipe_create(&a,&one,2);
 if(scenario==4 || scenario==5){assert(ret==(scenario==4?-ENOSPC:-EREMOTEIO) && !one.a5 && !a.session_count && !a.session_uncertain);mode=0;assert(!camss_a5_ipe_create(&a,&one,2));}
 else if(scenario==6 || scenario==7 || scenario==8 || scenario==10 || scenario==20 || scenario==22 || scenario==23 || scenario==25 || scenario==26){
  int expected=(scenario==7 || scenario==8)?-ETIMEDOUT:scenario==23 || scenario==25 || scenario==26?-EIO:-EPROTO;
  assert(ret==expected && !one.a5 && !a.session_count && a.session_uncertain);
  before=writes;assert(camss_a5_ipe_create(&a,&two,3)==-EIO && writes==before);mode=0;assert(!model_stop(&a) && resets==1 && !a.session_uncertain && !a.cpu_enabled && !a.power_held);return 0;
 }else assert(!ret);
 assert(one.a5==&a && one.handle && a.session_count==1 && a.session_creates==1);
 if(scenario==3){before=writes;assert(camss_a5_ipe_create(&a,&one,2)==-EBUSY && writes==before);}
 mode=0;
 if(scenario==11 || scenario==12 || scenario==13 || scenario==21){
  mode=scenario;ret=camss_a5_ipe_destroy(&a,&one);assert(ret==(scenario==13 || scenario==21?-EPROTO:-EREMOTEIO) && one.a5==&a && a.session_count==1);
  if(scenario==13 || scenario==21){assert(a.session_uncertain);mode=0;assert(!model_stop(&a) && resets==1 && !one.a5 && !one.handle);return 0;}
  assert(!a.session_uncertain);mode=0;assert(!camss_a5_ipe_destroy(&a,&one));
 }else if(scenario==16){
  mode=16;reset_error=1;assert(model_stop(&a)==-EBUSY && one.a5==&a && a.session_count==1 && a.session_uncertain && a.cpu_enabled && a.power_held && backing && !free_calls && !pm_calls);
  mode=0;reset_error=0;assert(!model_stop(&a) && !one.a5 && !a.session_count && !a.session_uncertain && !backing && !a.power_held);return 0;
 }else{
  mode=scenario==17?17:0;ret=camss_a5_ipe_create(&a,&two,3);
  if(scenario==17){assert(ret==-EPROTO && !two.a5 && one.a5==&a && a.session_count==1 && a.session_uncertain);mode=0;assert(!model_stop(&a) && resets==1 && !one.a5);return 0;}
  assert(!ret && a.session_count==2 && one.handle!=two.handle && a.session_peak==2);
  if(scenario!=15){assert(!camss_a5_ipe_destroy(&a,&two) && a.session_count==1 && !two.a5);assert(!camss_a5_ipe_destroy(&a,&one) && !a.session_count && !one.a5);}
 }
 assert(!model_stop(&a) && !resets && pc_commands==1 && !a.cpu_enabled && !a.irq_enabled && !a.power_held && !backing && !a.session_count && !one.a5 && !two.a5);
 assert(a.session_destroys==a.session_creates && joins==writes+(scenario==4) && !a.lock.held && !a.protocol_errors);
 puts("A5_IPE_SESSION_MODEL_PASS");
}
