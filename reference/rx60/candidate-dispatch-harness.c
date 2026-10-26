/* SPDX-License-Identifier: BSD-3-Clause
 * Offline transport-dispatch harness. FileCreate code comes from Qualcomm
 * 14b6fe1 (Copyright Qualcomm Technologies, Inc. and/or its subsidiaries),
 * with the local experimental patch. WDF APIs are mocks; this is not a WDK build.
 */
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
typedef int BOOLEAN;
typedef int32_t NTSTATUS;
typedef uint32_t ULONG;
typedef void VOID;
typedef int WDFKEY;
typedef int WDFDEVICE;
typedef int WDFREQUEST;
typedef int WDFFILEOBJECT;
typedef struct {uint16_t idVendor,idProduct;} USB_DEVICE_DESCRIPTOR;
typedef struct {int Device; void *UsbDevice; wchar_t *PortName; int BulkIN,BulkOUT,FileCreateEvent;} CONTEXT;
typedef CONTEXT *PDEVICE_CONTEXT;
#define TRUE 1
#define FALSE 0
#define STATUS_SUCCESS 0
#define STATUS_PENDING 0x103
#define FAILURE ((NTSTATUS)-1)
#define NT_SUCCESS(s) ((s)>=0)
#define QCSER_RESET_RETRIES 3
#define QCSER_DBG_MASK_CIRP 0
#define QCSER_DBG_LEVEL_TRACE 0
#define QCSER_DBG_LEVEL_ERROR 0
#define QCSER_DbgPrint(...) ((void)0)
#define PLUGPLAY_REGKEY_DRIVER 1
#define KEY_QUERY_VALUE 1
#define WDF_NO_OBJECT_ATTRIBUTES 0
#define IO_NO_INCREMENT 0
#define DECLARE_CONST_UNICODE_STRING(n,s) const wchar_t *n=s
static CONTEXT context;
static USB_DEVICE_DESCRIPTOR desc;
static ULONG option;
static NTSTATUS idleStatus,keyStatus,queryStatus,inStatus,outStatus,completed;
static int inCount,outCount,idleResumes,dtr,rts,wakes,keysOpened,keysClosed,queries;
static PDEVICE_CONTEXT QCDevGetContext(int d){(void)d;return &context;}
static void WdfUsbTargetDeviceGetDeviceDescriptor(void *d,USB_DEVICE_DESCRIPTOR *p){(void)d;*p=desc;}
static NTSTATUS WdfDeviceOpenRegistryKey(int d,int k,int a,int attrs,WDFKEY *p){(void)d;(void)k;(void)a;(void)attrs;if(NT_SUCCESS(keyStatus)){*p=1;keysOpened++;}return keyStatus;}
static NTSTATUS WdfRegistryQueryULong(WDFKEY k,const wchar_t **n,ULONG *p){assert(k==1);assert(wcscmp(*n,L"QCEudPreserveToggleOnOpen")==0);queries++;if(NT_SUCCESS(queryStatus))*p=option;return queryStatus;}
static void WdfRegistryClose(WDFKEY k){assert(k==1);keysClosed++;}
static NTSTATUS WdfDeviceStopIdle(int d,int wait){(void)d;assert(wait);return idleStatus;}
static void WdfDeviceResumeIdle(int d){(void)d;idleResumes++;}
static NTSTATUS QCPNP_ResetUsbPipe(PDEVICE_CONTEXT p,int pipe,int ms){assert(p==&context&&ms==500);if(pipe==1){inCount++;return inStatus;}assert(pipe==2);outCount++;return outStatus;}
static void QCMAIN_Wait(PDEVICE_CONTEXT p,int64_t t){assert(p==&context&&t<0);}
static void QCSER_SerialClrDtr(PDEVICE_CONTEXT p){assert(p==&context);dtr++;}
static void QCSER_SerialClrRts(PDEVICE_CONTEXT p){assert(p==&context);rts++;}
static void KeSetEvent(int *p,int inc,int wait){assert(p==&context.FileCreateEvent&&inc==0&&!wait);wakes++;}
static void WdfRequestComplete(int req,NTSTATUS s){assert(req==1);completed=s;}
static BOOLEAN QCPNP_EudPreserveToggleOnOpen(PDEVICE_CONTEXT pDevContext)
{
    USB_DEVICE_DESCRIPTOR descriptor;
    WDFKEY key;
    ULONG enabled = 0;
    NTSTATUS status;
    DECLARE_CONST_UNICODE_STRING(valueName, L"QCEudPreserveToggleOnOpen");

    if (pDevContext->UsbDevice == NULL)
    {
        return FALSE;
    }
    WdfUsbTargetDeviceGetDeviceDescriptor(pDevContext->UsbDevice, &descriptor);
    if (descriptor.idVendor != 0x05c6 || descriptor.idProduct != 0x9505)
    {
        return FALSE;
    }
    status = WdfDeviceOpenRegistryKey(pDevContext->Device,
                                    PLUGPLAY_REGKEY_DRIVER, KEY_QUERY_VALUE,
                                    WDF_NO_OBJECT_ATTRIBUTES, &key);
    if (!NT_SUCCESS(status))
    {
        return FALSE;
    }
    status = WdfRegistryQueryULong(key, &valueName, &enabled);
    WdfRegistryClose(key);
    return NT_SUCCESS(status) && enabled == 1;
}

VOID QCPNP_EvtFileCreate
(
    WDFDEVICE     Device,
    WDFREQUEST    Request,
    WDFFILEOBJECT FileObject
)
{
    PDEVICE_CONTEXT pDevContext = QCDevGetContext(Device);
    NTSTATUS        status = STATUS_SUCCESS;
    BOOLEAN         preserveToggle = FALSE;

    QCSER_DbgPrint
    (
        QCSER_DBG_MASK_CIRP,
        QCSER_DBG_LEVEL_TRACE,
        ("<%ws> QCPNP_EvtFileCreate request: 0x%p\n", pDevContext->PortName, Request)
    );

#ifdef QCUSB_MUX_PROTOCOL
    pDevContext->QcStats.SessionTotal = 0;
    pDevContext->QcStats.ViCurrentAddress = -1;
    pDevContext->QcStats.ViCurrentDirection = 0;
    pDevContext->QcStats.ViCurrentDataSize = 0;
#endif

    // reset bulk in & bulk out pipes
    status = WdfDeviceStopIdle(pDevContext->Device, TRUE);     // unblocking call, return immediately
    if (status == STATUS_PENDING || status == STATUS_SUCCESS)   // otherwise, the device may fails
    {
        preserveToggle = QCPNP_EudPreserveToggleOnOpen(pDevContext);
        if (preserveToggle)
        {
            status = STATUS_SUCCESS;
            QCSER_DbgPrint
            (
                QCSER_DBG_MASK_CIRP,
                QCSER_DBG_LEVEL_TRACE,
                ("<%ws> QCPNP_EvtFileCreate preserving EUD COM data toggles\n", pDevContext->PortName)
            );
        }
        for (int i = 0; !preserveToggle && i < QCSER_RESET_RETRIES; i++)
        {
            status = QCPNP_ResetUsbPipe(pDevContext, pDevContext->BulkIN, 500);
            if (!NT_SUCCESS(status))
            {
                QCSER_DbgPrint
                (
                    QCSER_DBG_MASK_CIRP,
                    QCSER_DBG_LEVEL_ERROR,
                    ("<%ws> QCPNP_EvtFileCreate reset bulk in pipe FAILED status: 0x%x\n", pDevContext->PortName, status)
                );
                if (i < QCSER_RESET_RETRIES - 1)    // should not wait if the last attempt failed
                {
                    QCMAIN_Wait(pDevContext, -(4 * 1000 * 1000));  // 0.4 sec
                }
            }
            else
            {
                QCSER_DbgPrint
                (
                    QCSER_DBG_MASK_CIRP,
                    QCSER_DBG_LEVEL_TRACE,
                    ("<%ws> QCPNP_EvtFileCreate reset bulk in pipe SUCCESSFUL status: 0x%x\n", pDevContext->PortName, status)
                );
                break;
            }
        }
        for (int i = 0; !preserveToggle && i < QCSER_RESET_RETRIES; i++)
        {
            status = QCPNP_ResetUsbPipe(pDevContext, pDevContext->BulkOUT, 500);
            if (!NT_SUCCESS(status))
            {
                QCSER_DbgPrint
                (
                    QCSER_DBG_MASK_CIRP,
                    QCSER_DBG_LEVEL_ERROR,
                    ("<%ws> QCPNP_EvtFileCreate reset bulk out pipe FAILED status: 0x%x\n", pDevContext->PortName, status)
                );
                if (i < QCSER_RESET_RETRIES - 1)    // should not wait if the last attempt failed
                {
                    QCMAIN_Wait(pDevContext, -(4 * 1000 * 1000));  // 0.4 sec
                }
            }
            else
            {
                QCSER_DbgPrint
                (
                    QCSER_DBG_MASK_CIRP,
                    QCSER_DBG_LEVEL_TRACE,
                    ("<%ws> QCPNP_EvtFileCreate reset bulk out pipe SUCCESSFUL status: 0x%x\n", pDevContext->PortName, status)
                );
                break;
            }
        }
        WdfDeviceResumeIdle(pDevContext->Device);
    }

    if (NT_SUCCESS(status))
    {
        QCSER_SerialClrDtr(pDevContext);
        QCSER_SerialClrRts(pDevContext);

        // wake up read thread
        KeSetEvent(&pDevContext->FileCreateEvent, IO_NO_INCREMENT, FALSE);
        QCSER_DbgPrint
        (
            QCSER_DBG_MASK_CIRP,
            QCSER_DBG_LEVEL_TRACE,
            ("<%ws> QCPNP_EvtFileCreate completed status: 0x%x\n", pDevContext->PortName, status)
        );
    }
    else
    {
        QCSER_DbgPrint
        (
            QCSER_DBG_MASK_CIRP,
            QCSER_DBG_LEVEL_ERROR,
            ("<%ws> QCPNP_EvtFileCreate FAILED status: 0x%x\n", pDevContext->PortName, status)
        );
    }

    WdfRequestComplete(Request, status);
}

VOID QCPNP_EvtFileCreate_Baseline
(
    WDFDEVICE     Device,
    WDFREQUEST    Request,
    WDFFILEOBJECT FileObject
)
{
    PDEVICE_CONTEXT pDevContext = QCDevGetContext(Device);
    NTSTATUS        status = STATUS_SUCCESS;

    QCSER_DbgPrint
    (
        QCSER_DBG_MASK_CIRP,
        QCSER_DBG_LEVEL_TRACE,
        ("<%ws> QCPNP_EvtFileCreate_Baseline request: 0x%p\n", pDevContext->PortName, Request)
    );

#ifdef QCUSB_MUX_PROTOCOL
    pDevContext->QcStats.SessionTotal = 0;
    pDevContext->QcStats.ViCurrentAddress = -1;
    pDevContext->QcStats.ViCurrentDirection = 0;
    pDevContext->QcStats.ViCurrentDataSize = 0;
#endif

    // reset bulk in & bulk out pipes
    status = WdfDeviceStopIdle(pDevContext->Device, TRUE);     // unblocking call, return immediately
    if (status == STATUS_PENDING || status == STATUS_SUCCESS)   // otherwise, the device may fails
    {
        for (int i = 0; i < QCSER_RESET_RETRIES; i++)
        {
            status = QCPNP_ResetUsbPipe(pDevContext, pDevContext->BulkIN, 500);
            if (!NT_SUCCESS(status))
            {
                QCSER_DbgPrint
                (
                    QCSER_DBG_MASK_CIRP,
                    QCSER_DBG_LEVEL_ERROR,
                    ("<%ws> QCPNP_EvtFileCreate_Baseline reset bulk in pipe FAILED status: 0x%x\n", pDevContext->PortName, status)
                );
                if (i < QCSER_RESET_RETRIES - 1)    // should not wait if the last attempt failed
                {
                    QCMAIN_Wait(pDevContext, -(4 * 1000 * 1000));  // 0.4 sec
                }
            }
            else
            {
                QCSER_DbgPrint
                (
                    QCSER_DBG_MASK_CIRP,
                    QCSER_DBG_LEVEL_TRACE,
                    ("<%ws> QCPNP_EvtFileCreate_Baseline reset bulk in pipe SUCCESSFUL status: 0x%x\n", pDevContext->PortName, status)
                );
                break;
            }
        }
        for (int i = 0; i < QCSER_RESET_RETRIES; i++)
        {
            status = QCPNP_ResetUsbPipe(pDevContext, pDevContext->BulkOUT, 500);
            if (!NT_SUCCESS(status))
            {
                QCSER_DbgPrint
                (
                    QCSER_DBG_MASK_CIRP,
                    QCSER_DBG_LEVEL_ERROR,
                    ("<%ws> QCPNP_EvtFileCreate_Baseline reset bulk out pipe FAILED status: 0x%x\n", pDevContext->PortName, status)
                );
                if (i < QCSER_RESET_RETRIES - 1)    // should not wait if the last attempt failed
                {
                    QCMAIN_Wait(pDevContext, -(4 * 1000 * 1000));  // 0.4 sec
                }
            }
            else
            {
                QCSER_DbgPrint
                (
                    QCSER_DBG_MASK_CIRP,
                    QCSER_DBG_LEVEL_TRACE,
                    ("<%ws> QCPNP_EvtFileCreate_Baseline reset bulk out pipe SUCCESSFUL status: 0x%x\n", pDevContext->PortName, status)
                );
                break;
            }
        }
        WdfDeviceResumeIdle(pDevContext->Device);
    }

    if (NT_SUCCESS(status))
    {
        QCSER_SerialClrDtr(pDevContext);
        QCSER_SerialClrRts(pDevContext);

        // wake up read thread
        KeSetEvent(&pDevContext->FileCreateEvent, IO_NO_INCREMENT, FALSE);
        QCSER_DbgPrint
        (
            QCSER_DBG_MASK_CIRP,
            QCSER_DBG_LEVEL_TRACE,
            ("<%ws> QCPNP_EvtFileCreate_Baseline completed status: 0x%x\n", pDevContext->PortName, status)
        );
    }
    else
    {
        QCSER_DbgPrint
        (
            QCSER_DBG_MASK_CIRP,
            QCSER_DBG_LEVEL_ERROR,
            ("<%ws> QCPNP_EvtFileCreate_Baseline FAILED status: 0x%x\n", pDevContext->PortName, status)
        );
    }

    WdfRequestComplete(Request, status);
}


typedef struct {const char *name;uint16_t vid,pid;ULONG value;int noUsb;NTSTATUS idle,key,query,in,out;int expectedIn,expectedOut,preserve;} CASE;
static void reset(CASE c){
 context=(CONTEXT){.Device=1,.UsbDevice=c.noUsb?NULL:(void*)1,.BulkIN=1,.BulkOUT=2};
 desc=(USB_DEVICE_DESCRIPTOR){c.vid,c.pid}; option=c.value;
 idleStatus=c.idle;keyStatus=c.key;queryStatus=c.query;inStatus=c.in;outStatus=c.out;
 inCount=outCount=idleResumes=dtr=rts=wakes=keysOpened=keysClosed=queries=0;completed=99;
}
static int flow[7];
static void snapshot(int *p){p[0]=inCount;p[1]=outCount;p[2]=idleResumes;p[3]=dtr;p[4]=rts;p[5]=wakes;p[6]=completed;}
int main(void){
 CASE cases[]={
  {"opt_in_eud",0x05c6,0x9505,1,0,0,0,0,0,0,0,0,1},
  {"absent_value",0x05c6,0x9505,0,0,0,0,FAILURE,0,0,1,1,0},
  {"disabled",0x05c6,0x9505,0,0,0,0,0,0,0,1,1,0},
  {"unsupported_value",0x05c6,0x9505,2,0,0,0,0,0,0,1,1,0},
  {"wrong_vendor",0x1234,0x9505,1,0,0,0,0,0,0,1,1,0},
  {"control_pid_excluded",0x05c6,0x9501,1,0,0,0,0,0,0,1,1,0},
  {"no_usb_device",0x05c6,0x9505,1,1,0,0,0,0,0,1,1,0},
  {"registry_open_error",0x05c6,0x9505,1,0,0,FAILURE,0,0,0,1,1,0},
  {"wrong_registry_type",0x05c6,0x9505,1,0,0,0,FAILURE,0,0,1,1,0},
  {"registry_query_error",0x05c6,0x9505,1,0,0,0,FAILURE,0,0,1,1,0},
  {"idle_failure",0x05c6,0x9505,1,0,FAILURE,0,0,0,0,0,0,0},
  {"pending_idle_opt_in",0x05c6,0x9505,1,0,STATUS_PENDING,0,0,0,0,0,0,1},
  {"legacy_in_reset_failure",0x05c6,0x9505,0,0,0,0,0,FAILURE,0,3,1,0},
  {"legacy_out_reset_failure",0x05c6,0x9505,0,0,0,0,0,0,FAILURE,1,3,0}
 };
 printf("[\n");
 for(size_t i=0;i<sizeof(cases)/sizeof(*cases);i++){
  CASE c=cases[i];reset(c);QCPNP_EvtFileCreate(1,1,1);
  assert(inCount==c.expectedIn&&outCount==c.expectedOut);
  assert(keysOpened==keysClosed);
  if(c.vid!=0x05c6||c.pid!=0x9505||c.noUsb||c.idle==FAILURE)assert(keysOpened==0&&queries==0);
  if(c.preserve)assert(completed==STATUS_SUCCESS&&idleResumes==1&&dtr==1&&rts==1&&wakes==1);
  snapshot(flow);
  printf("%s{\"case\":\"%s\",\"in_resets\":%d,\"out_resets\":%d,\"keys_balanced\":true,\"status\":%d}",i?",\n":"",c.name,inCount,outCount,completed);
  if(!c.preserve){int old[7];reset(c);QCPNP_EvtFileCreate_Baseline(1,1,1);snapshot(old);assert(memcmp(old,flow,sizeof(flow))==0);}
 }
 printf("\n]\n");return 0;
}
