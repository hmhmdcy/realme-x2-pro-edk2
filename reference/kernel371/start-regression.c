/* Actual camss_a5_start() body with explicit platform/MMIO providers. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint32_t u32;
#define BIT(n) (1U<<(n))
#define A5_CONTROL 8
#define A5_RESET 4
#define A5_INT_ENABLE 0x10
#define A5_INT_CLEAR 0x18
#define A5_INIT_REQUEST 0x48
#define A5_INIT_RESPONSE 0x4c
#define A5_FW_VERSION 0x44
#define A5_QTABLE_PTR 0x58
#define A5_SFR_PTR 0x68
#define A5_SHARED_PTR 0x50
#define A5_SHARED_SIZE 0x54
#define A5_HEAP_PTR 0x5c
#define A5_HEAP_SIZE 0x60
#define A5_QDSS_PTR 0x6c
#define A5_QDSS_SIZE 0x70
#define A5_IO_PTR 0x74
#define A5_IO_SIZE 0x78
#define A5_ENABLE BIT(9)
#define A5_WAKE BIT(4)
#define A5_WFI_GATE BIT(12)
#define SHARED_IOVA 0x07400000
#define SFR_OFFSET 0x1c000
#define SHARED_WINDOW 0x09600000
#define HEAP_IOVA 0x10a00000
#define HEAP_BYTES 0x100000
#define IO_IOVA 0x10c00000
#define IO_BYTES 0xcf300000
#define SYS_INIT 0x10001
#define INIT_DONE 0x20001
#define __iomem
#define HRTIMER_MODE_REL 0
#define READ_ONCE(x) (x)
#define dev_info(...) ((void)0)
#define dma_wmb() ((void)0)
#define udelay(n) ((void)(n))
#define ms_to_ktime(n) (n)
#define spin_lock_irqsave(lock,flags) ((void)(lock),(flags)=1)
#define spin_unlock_irqrestore(lock,flags) ((void)(lock),(void)(flags))
struct firmware {int unused;};
struct camss_a5 {
 struct {void *sierra;} resources;
 void *dev,*reset;int lock,control_lock,boot_timer,irq;
 bool power_held,cpu_enabled,irq_enabled,initialized,reset_asserted,cpu_release_attempted,boot_expired;
 bool init_done,ping_done,pc_done;
 u32 init_response,fw_version,last_type,interrupts,messages,debug_packets,watchdogs,protocol_errors,response_before;
 int pc_error,cleanup_error;
};
static struct camss_a5 *active;
static u32 registers[64],responses[4];
static unsigned consumed,response_count,sends,stops,dumps,clock_order,published_at,stopped_at;
static int command_error,expire_after=-1;
static bool backing;
static int prepare_error,resume_error,stop_error;
static void mutex_lock(int *p) {assert(!*p);*p=1;}
static void mutex_unlock(int *p) {assert(*p);*p=0;}
static bool camss_a5_backing_owned(struct camss_a5 *a) {(void)a;return backing;}
static int prepare_memory(struct camss_a5 *a,const struct firmware *f) {(void)a;(void)f;backing=true;return prepare_error;}
static int pm_runtime_resume_and_get(void *dev) {(void)dev;return resume_error;}
static int reset_control_assert(void *reset) {(void)reset;return 0;}
static int reset_control_deassert(void *reset) {(void)reset;return 0;}
static void enable_irq(int irq) {(void)irq;}
static void hrtimer_start(int *t,int timeout,int mode) {(void)timeout;(void)mode;assert(!*t);*t=1;}
static void hrtimer_cancel(int *t) {*t=0;}
static u32 readl(void *p) {
 if(p==active->resources.sierra+A5_INIT_RESPONSE && active->cpu_enabled) {
  if(expire_after>=0 && consumed>=(unsigned)expire_after)active->boot_expired=true;
  unsigned index=consumed<response_count?consumed:response_count-1;++consumed;return responses[index];
 }
 return *(u32 *)p;
}
static void writel(u32 value,void *p) {*(u32 *)p=value;}
#define readl_poll_timeout(addr,value,condition,interval,timeout) ({ \
 (void)(interval);(void)(timeout);int status=-ETIMEDOUT; \
 for(unsigned sample=0;sample<4;++sample){(value)=readl(addr);if(condition){status=0;break;}}status;})
static int send_command(struct camss_a5 *a,u32 type,u32 response) {
 assert(a==active && type==SYS_INIT && response==INIT_DONE);++sends;
 assert(a->init_response==1);return command_error;
}
static void publish_start_failure(struct camss_a5 *a) {
 if(a->cpu_release_attempted){++dumps;published_at=++clock_order;}
}
static int quiesce_locked(struct camss_a5 *a) {
 ++stops;stopped_at=++clock_order;if(stop_error)return stop_error;
 a->cpu_enabled=false;a->irq_enabled=false;a->reset_asserted=true;return 0;
}
static int stop_locked(struct camss_a5 *a) {
 int ret=quiesce_locked(a);if(ret)return ret;a->power_held=false;backing=false;return 0;
}
#include "body.inc"
int main(int argc,char **argv)
{
 assert(argc==2);int scenario=atoi(argv[1]);struct camss_a5 a={0};struct firmware fw={0};active=&a;a.resources.sierra=registers;registers[A5_FW_VERSION/4]=0x01000100;
 response_count=1;responses[0]=1;int expected=0;unsigned wanted_sends=1,wanted_dumps=0;
 if(scenario==1){response_count=3;responses[0]=0;responses[1]=3;responses[2]=1;expected=-EREMOTEIO;wanted_sends=0;wanted_dumps=1;}
 if(scenario==2){responses[0]=3;expected=-EREMOTEIO;wanted_sends=0;wanted_dumps=1;}
 if(scenario==3){responses[0]=2;expected=-EREMOTEIO;wanted_sends=0;wanted_dumps=1;}
 if(scenario==4){responses[0]=0;expected=-ETIMEDOUT;wanted_sends=0;wanted_dumps=1;}
 if(scenario==5){responses[0]=3;expire_after=0;expected=-ETIMEDOUT;wanted_sends=0;wanted_dumps=1;}
 if(scenario==6){command_error=-EIO;expected=-EIO;wanted_dumps=1;}
 if(scenario==7){a.cpu_enabled=true;expected=-EBUSY;wanted_sends=0;}
 if(scenario==8){responses[0]=4;expected=-ETIMEDOUT;wanted_sends=0;wanted_dumps=1;}
 if(scenario==9){response_count=3;responses[0]=0;responses[1]=4;responses[2]=1;}
 if(scenario==10){resume_error=-EIO;expected=-EIO;wanted_sends=0;}
 if(scenario==11){prepare_error=-EINVAL;expected=-EINVAL;wanted_sends=0;}
 if(scenario==12){responses[0]=3;stop_error=-EBUSY;expected=-EREMOTEIO;wanted_sends=0;wanted_dumps=1;}
 assert(camss_a5_start(&a,&fw)==expected);assert(!a.lock && !a.boot_timer);
 assert(sends==wanted_sends && dumps==wanted_dumps);
 assert(stops==((expected && scenario!=7)?1U:0U));
 if(wanted_dumps)assert(published_at && stopped_at>published_at);
 if(scenario==1)assert(consumed==2);
 if(scenario==2)assert(consumed==1);
 if(scenario==12)assert(backing && a.cpu_enabled && a.power_held && a.cleanup_error==-EBUSY);
 else if(!expected)assert(a.initialized && a.cpu_enabled && a.power_held);
 else if(scenario!=7){
  assert(!a.cpu_enabled && !a.irq_enabled && backing && a.reset_asserted);
  assert(a.power_held==(scenario!=10 && scenario!=11));
 }
 puts("A5_START_DUMP_PASS");
}
