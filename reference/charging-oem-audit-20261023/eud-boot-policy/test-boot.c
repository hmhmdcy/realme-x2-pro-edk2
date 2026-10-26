#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#define STATIC static
#define VOID void
#define IN
#define OUT
#define EFIAPI
#define CONST const
#define TRUE true
#define FALSE false
#define SAMURAI_ENABLE_EUD 1
#define SAMURAI_LINUX_KERNEL 1
#define DEBUG_ERROR 1
#define DEBUG_WARN 2
#define DEBUG(...) ((void)0)
#define EFI_SUCCESS 0
#define EFI_NOT_READY 1
#define EFI_DEVICE_ERROR 2
#define EFI_COMPROMISED_DATA 3
#define EFI_ALREADY_STARTED 4
#define EFI_UNSUPPORTED 5
#define EFI_INVALID_PARAMETER 6
#define EFI_ERROR(s) ((s)!=EFI_SUCCESS)
#define EVT_NOTIFY_SIGNAL 0x200
#define TPL_CALLBACK 8
#define TPL_HIGH_LEVEL 31
#define ASSERT assert
#define VALID_TPL(x) ((x)<=TPL_HIGH_LEVEL)
#define REPORT_STATUS_CODE(...) ((void)0)
typedef bool BOOLEAN;
typedef uint32_t UINT32;
typedef uint8_t UINT8;
typedef uint64_t UINT64;
typedef uintptr_t UINTN;
typedef unsigned EFI_STATUS;
typedef unsigned EFI_TPL;
typedef void *EFI_EVENT;
typedef void *EFI_HANDLE;
typedef char CHAR8;
typedef int EFI_GUID;
typedef void (*NOTIFY)(EFI_EVENT,void *);
static EFI_GUID gEfiEventBeforeExitBootServicesGuid,gEventExitBootServicesFailedGuid,gEfiEventExitBootServicesGuid;
struct boot_services {
 EFI_STATUS (*CreateEventEx)(UINT32,EFI_TPL,NOTIFY,void *,EFI_GUID *,EFI_EVENT *);
 EFI_STATUS (*CloseEvent)(EFI_EVENT);
 void (*Stall)(UINTN);
};
typedef struct boot_services EFI_BOOT_SERVICES;
static struct boot_services services,*gBS=&services;
static UINT32 csr;
static int reads,writes,fifo_writes,created,closed,kernel_calls,panel_arms,panel_disarms;
static int ignore_write,create_error,close_error,fire_on_boot;
static NOTIFY notify;
static void *notify_context;
static UINT32 MmioRead32(UINTN a){if(a==0x088e1014U){reads++;return csr;}assert(a==0x088e0000U);return 0x90;}
static void MmioWrite32(UINTN a,UINT32 v){
 if(a==0x088e1014U){assert(v==0);writes++;if(!ignore_write)csr=0;}
 else {assert(a==0x088e0000U||a==0x088e0004U||a==0x088e0008U);fifo_writes++;}
}
#define ZeroMem(p,n) memset((p),0,(n))
static EFI_STATUS create(UINT32 t,EFI_TPL tpl,NOTIFY fn,void *ctx,EFI_GUID *guid,EFI_EVENT *event){
 assert(t==EVT_NOTIFY_SIGNAL&&tpl==TPL_CALLBACK&&guid==&gEfiEventBeforeExitBootServicesGuid);created++;
 if(create_error)return EFI_DEVICE_ERROR;
 notify=fn;notify_context=ctx;*event=(void *)0x1234;return 0;
}
static EFI_STATUS close_event(EFI_EVENT e){assert(e==(void*)0x1234);closed++;if(close_error)return EFI_DEVICE_ERROR;notify=NULL;return 0;}
static void stall(UINTN us){(void)us;}
#include "eud-handoff-fragment.inc"
#include "direct-fifo.inc"
static int NewOption;
static void Print(const void *format,...){(void)format;}
static EFI_STATUS SamuraiArmPanelHandoff(void *p){(void)p;panel_arms++;return 0;}
static void SamuraiDisarmPanelHandoff(void *p){(void)p;panel_disarms++;}
static void EfiBootManagerBoot(void *p){(void)p;kernel_calls++;if(fire_on_boot)notify((void*)0x1234,notify_context);}
static void launch(void){EFI_STATUS Status;int PanelHandoff;
#include "launch.inc"
}
/* Actual EDK2 CoreExitBootServices with OS/firmware edges faked. */
static int map_error,timer_stops,before_events,failed_events,exit_events;
static BOOLEAN gMemoryMapTerminated;
struct timer {void (*SetTimerPeriod)(void *,UINT64);};
static void stop_timer(void *t,UINT64 p){(void)t;assert(p==0);timer_stops++;assert(before_events>0);}
static struct timer timer={stop_timer},*gTimer=&timer;
static EFI_STATUS CoreTerminateMemoryMap(UINTN key){(void)key;assert(timer_stops>0);return map_error?EFI_INVALID_PARAMETER:0;}
static void CoreNotifySignalList(EFI_GUID *guid){
 if(guid==&gEfiEventBeforeExitBootServicesGuid){before_events++;if(notify)notify((void*)0x1234,notify_context);}
 else if(guid==&gEventExitBootServicesFailedGuid)failed_events++;
 else {assert(guid==&gEfiEventExitBootServicesGuid);exit_events++;}
}
static void MemoryProtectionExitBootServicesCallback(void){}
static void SaveAndSetDebugTimerInterrupt(BOOLEAN b){assert(!b);}
static void cpu_disable(void *c){(void)c;}
struct cpu {void (*DisableInterrupt)(void *);};
static struct cpu cpu={cpu_disable},*gCpu=&cpu;
struct st {struct boot_services *BootServices;void *ConIn,*ConsoleInHandle,*ConOut,*ConsoleOutHandle,*StdErr,*StandardErrorHandle;int Hdr;};
static struct st st,*gDxeCoreST=&st;
static void CalculateEfiHdrCrc(void *p){(void)p;}
struct runtime {BOOLEAN AtRuntime;};
static struct runtime runtime,*gRuntime=&runtime;
static EFI_TPL gEfiCurrentTpl;
static UINT64 gEventPending;
static int dispatched;
static int HighBitSet64(UINT64 x){assert(x);return 63-__builtin_clzll(x);}
static void CoreSetInterruptState(BOOLEAN b){(void)b;}
static void CoreDispatchEventNotifies(EFI_TPL t){dispatched++;gEventPending&=~(1ULL<<t);}
#include "core-functions.inc"
static void reset(UINT32 value){
 memset(&mSamuraiEudOffHandoff,0,sizeof(mSamuraiEudOffHandoff));csr=value;
 reads=writes=fifo_writes=created=closed=kernel_calls=panel_arms=panel_disarms=0;
 ignore_write=create_error=close_error=fire_on_boot=0;notify=NULL;notify_context=NULL;
 services=(struct boot_services){create,close_event,stall};gBS=&services;
 map_error=timer_stops=before_events=failed_events=exit_events=0;
 gMemoryMapTerminated=false;runtime.AtRuntime=false;gEventPending=0;dispatched=0;
}
int main(void){
 reset(1);assert(SamuraiArmEudOffHandoff()==0&&writes==0&&notify_context==&mSamuraiEudOffHandoff);
 notify((void*)0x1234,notify_context);assert(csr==0&&writes==1&&mSamuraiEudOffHandoff.Status==0);
 notify((void*)0x1234,notify_context);assert(writes==1);
 SamuraiEudComPuts("late");assert(fifo_writes==0);SamuraiDisarmEudOffHandoff();assert(closed==1);
 puts("ok: known1 one write; static event context; repeated notification and late direct producer inert");
 reset(0);assert(!SamuraiArmEudOffHandoff());notify(NULL,notify_context);
 assert(!writes&&mSamuraiEudOffHandoff.AfterCsr==0&&!mSamuraiEudOffHandoff.Status);
 puts("ok: already zero is verified without write");
 UINT32 unknowns[]={2,0x01010101,0xffffffff,0x10000001};
 for(unsigned i=0;i<sizeof(unknowns)/sizeof(unknowns[0]);i++){reset(unknowns[i]);launch();assert(!writes&&!created&&!kernel_calls&&mSamuraiEudOffHandoff.Status==EFI_COMPROMISED_DATA);}
 puts("ok: unknown full words including unproven replica refuse arm and current launch");
 reset(1);assert(!SamuraiArmEudOffHandoff());csr=2;notify(NULL,notify_context);
 assert(!writes&&csr==2&&mSamuraiEudOffHandoff.Attempted&&mSamuraiEudOffHandoff.Status==EFI_COMPROMISED_DATA);
 puts("ok: value becomes unknown after arm; no write and no automatic retry");
 reset(1);ignore_write=1;assert(!SamuraiArmEudOffHandoff());notify(NULL,notify_context);
 assert(writes==1&&csr==1&&mSamuraiEudOffHandoff.Status==EFI_DEVICE_ERROR);notify(NULL,notify_context);assert(writes==1);
 puts("ok: failed readback records device error, remains terminal, no fabricated off");
 reset(1);create_error=1;launch();assert(!kernel_calls&&!panel_arms&&!writes&&created==1);
 puts("ok: registration failure refuses kernel launch and leaves panel untouched");
 reset(1);launch();assert(kernel_calls==1&&panel_arms==1&&panel_disarms==1&&closed==1&&!writes&&!notify);
 assert(mSamuraiEudOffHandoff.Cancelled&&!mSamuraiEudOffHandoff.Attempted&&csr==1);
 puts("ok: loader returns before EBS: close/cancel and no CSR change");
 reset(1);assert(!SamuraiArmEudOffHandoff());close_error=1;SamuraiDisarmEudOffHandoff();
 assert(mSamuraiEudOffHandoff.Event&&mSamuraiEudOffHandoff.Cancelled);notify(NULL,notify_context);
 assert(!writes&&!mSamuraiEudOffHandoff.Attempted&&SamuraiArmEudOffHandoff()==EFI_ALREADY_STARTED);
 puts("ok: failed CloseEvent retains cancelled static context; future signal cannot write");
 reset(1);assert(!SamuraiArmEudOffHandoff());map_error=1;
 assert(CoreExitBootServices(NULL,1)==EFI_INVALID_PARAMETER&&writes==1&&before_events==1&&failed_events==1&&!exit_events&&timer_stops==1);
 map_error=0;assert(CoreExitBootServices(NULL,2)==0&&writes==1&&before_events==2&&timer_stops==2&&exit_events==1&&runtime.AtRuntime);
 assert(!gBS);SamuraiDisarmEudOffHandoff();assert(mSamuraiEudOffHandoff.Cancelled&&csr==0);
 puts("ok: actual CoreExitBootServices bad MapKey then success: Before fires twice, sole write stays once");
 reset(1);ignore_write=1;assert(!SamuraiArmEudOffHandoff());assert(CoreExitBootServices(NULL,1)==0);
 assert(runtime.AtRuntime&&csr==1&&mSamuraiEudOffHandoff.Status==EFI_DEVICE_ERROR);
 puts("ok: void callback failure does not prevent actual EBS success; Linux validation remains required");
 reset(1);gEfiCurrentTpl=TPL_CALLBACK;gEventPending=1ULL<<TPL_CALLBACK;CoreRestoreTpl(TPL_CALLBACK);assert(!dispatched&&gEventPending);
 CoreRestoreTpl(4);assert(dispatched==1&&!gEventPending);
 puts("ok: actual CoreRestoreTpl does not dispatch equal-TPL notification inside callback");
 reset(1);SamuraiEudBeforeExitBootServices(NULL,NULL);assert(!writes&&!reads);
 gBS=NULL;assert(SamuraiArmEudOffHandoff()==EFI_UNSUPPORTED&&!reads&&!writes);
 puts("ok: missing context/BootServices are inert");
 return 0;
}
