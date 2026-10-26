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
static UINT32 csr, forced_after_write;
static int reads,writes,fifo_writes,created,closed,kernel_calls,panel_arms,panel_disarms;
static int ignore_write,create_error,close_error,fire_on_boot;
static NOTIFY notify;
static void *notify_context;
static UINT32 MmioRead32(UINTN a){if(a==0x088e1014U){reads++;return csr;}assert(a==0x088e0000U);return 0x90;}
static void MmioWrite32(UINTN a,UINT32 v){
 if(a==0x088e1014U){assert(v==0);writes++;if(!ignore_write)csr=0;if(forced_after_write)csr=forced_after_write;}
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
 assert(SamuraiEudCsrKnown(0)&&SamuraiEudCsrKnown(1)&&SamuraiEudCsrKnown(0x01010101U));
 assert(!SamuraiEudCsrKnown(0x00010101U)&&!SamuraiEudCsrKnown(0x01010100U));
 puts("ok: exact full-word set adds only the actually observed literal");

 reset(0x01010101U);forced_after_write=0;
 assert(!SamuraiArmEudOffHandoff()&&reads==1&&!writes&&created==1);
 assert(mSamuraiEudOffHandoff.ArmCsr==0x01010101U);
 notify(NULL,notify_context);
 assert(csr==0&&writes==1&&reads==3&&mSamuraiEudOffHandoff.WriteAttempted);
 assert(mSamuraiEudOffHandoff.BeforeCsr==0x01010101U&&mSamuraiEudOffHandoff.AfterCsr==0&&mSamuraiEudOffHandoff.Status==EFI_SUCCESS);
 notify(NULL,notify_context);assert(writes==1&&reads==3);
 SamuraiEudComPuts("late");assert(!fifo_writes);SamuraiDisarmEudOffHandoff();assert(closed==1);
 puts("ok: observed full word arms without writes, callback writes literal0 once, exact zero readback succeeds, retry inert");

 UINT32 unknowns[]={0x00010101U,0x01000101U,0x01010100U,0x01010102U,0x00000101U,2U,0xffffffffU,0x10000001U};
 for(unsigned i=0;i<sizeof(unknowns)/sizeof(unknowns[0]);i++){
  reset(unknowns[i]);forced_after_write=0;launch();
  assert(!writes&&!created&&!kernel_calls&&!panel_arms&&csr==unknowns[i]);
  assert(mSamuraiEudOffHandoff.Status==EFI_COMPROMISED_DATA);
 }
 puts("ok: approximate and other unknown whole words refuse arm and launch with zero writes");

 reset(0x01010101U);forced_after_write=0;assert(!SamuraiArmEudOffHandoff());csr=0x00010101U;
 notify(NULL,notify_context);assert(!writes&&csr==0x00010101U&&mSamuraiEudOffHandoff.Attempted&&mSamuraiEudOffHandoff.Status==EFI_COMPROMISED_DATA);
 int n=reads;notify(NULL,notify_context);assert(!writes&&reads==n);
 puts("ok: unknown near-word at callback is preserved and terminal without write or retry");

 UINT32 nonzero[]={1U,0x01010101U,0x01000000U};
 for(unsigned i=0;i<sizeof(nonzero)/sizeof(nonzero[0]);i++){
  reset(0x01010101U);forced_after_write=nonzero[i];assert(!SamuraiArmEudOffHandoff()&&!writes);
  notify(NULL,notify_context);assert(writes==1&&csr==nonzero[i]&&mSamuraiEudOffHandoff.AfterCsr==nonzero[i]&&mSamuraiEudOffHandoff.Status==EFI_DEVICE_ERROR);
  int count=reads;notify(NULL,notify_context);assert(writes==1&&reads==count);
 }
 puts("ok: every nonzero full readback fails even if known or low byte zero, and no callback retry writes");
 return 0;
}
