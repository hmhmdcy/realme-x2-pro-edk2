# RX54: installed Windows read workers and a cumulative buffer count

Read-only analysis of the same installed qcusbser 2.1.3.5 identified in RX50.
PE SHA ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151;
PDB SHA ee203464fc2ab419eaa66c90e345e24eba3fa0e103c0fe11f91e428897ef9155;
GUID 66581f50-52c9-4a32-9ac6-fe0c57b94a80, age 1. Matching section headers and
AMD64 exception-directory bounds establish the selected function identities.
This does not use the newer public WDF implementation as the installed driver.

| Exact observed code | Consequence / limit |
|---|---|
| QCSER_Open 2a5fc..2a8c2: calls QCUSB_ResetInput at 2a786, QCUSB_ResetOutput at 2a797, then QCSER_StartDataThreads at 2a89d | The open path contains endpoint resets before read-thread startup; agrees with historical ETW. It does not measure physical DATA0/1 or establish that a reset caused a missing frame. |
| QCSER_StartDataThreads 2a8c4..2a9e3: QCRD_StartReadThread at 2a93e | Read worker startup belongs to open, rather than being demonstrated only by application Read. Live scheduling/pipe readiness remains unknown. |
| QCRD_StartReadThread 23fcc..243f2: +11c0 compared with 1 at 24139..24149; worker targets c52c or 2445c before thread creation at 24153 | Exact PDB names +11c0 UseReadArray. Both multi-read and single-read paths exist. The live choice was not read; absent registry values do not establish it. |
| QCSER_ReadThread 2445c..253cd: CountReadQueue/threshold at 2489a..248b8, bulk URB setup at 248b8..24910, lower-driver submission at 24922, completion event processing later | Buffer pressure can change requests independently of the PowerShell UI loop. Do not equate every app Read gap with a gap in Windows USB IN requests. This is control-flow analysis, not measured runtime. |
| SerialGetStats 2b81c..2b97f: 24-byte pPerfstats (+2e0) copy at 2b8e2..2b8f4 | A read-only cumulative-statistics output is implemented. Unlike the error query, this path does not clear the source counters. No live request was made in RX54. |
| RX50 vPutToReadBuffer 29783..29795: pPerfstats->ReceivedCount (+0) += r14d; early rejection 293b3..293bd precedes it | A received-byte delta can observe this driver's buffer-acceptance boundary. It is not physical bus evidence; refused blocks can be absent from the count. Retain errors/queue together. |

Microsoft specifies cumulative received/error fields for
[IOCTL_SERIAL_GET_STATS](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddser/ni-ntddser-ioctl_serial_get_stats).
The exact copy above and RX50 PDB type _SERIALPERF_STATS (24 bytes, ReceivedCount
offset 0) are the evidence for this release. Do not call CLEAR_STATS.

The standard [pipe recovery documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/how-to-recover-from-usb-pipe-errors)
describes cancellation and data-toggle reset. It supports the historical
reset hypothesis only; no reset is proposed or run here. Public framework
[continuous-reader documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wudfusb/nf-wudfusb-iwdfusbtargetpipe2-configurecontinuousreader)
explains a generic alternative, not this WDM implementation or a phone fix.
Broad EUD COM/first-packet searches did not yield a primary silicon TX FIFO
acceptance specification; existing TX status/pacing facts stay unchanged.

Next use a bounded overlapped GET_STATS on the existing diagnostic native handle
and compare ReceivedCount's modulo-32-bit delta with saved **wire** bytes and the
issued TX journal. A count/raw match or deficit requires an actually reproduced
gap before attributing a layer. An opening baseline may include preexisting data;
record queue/drain boundaries and timing. Keep the ordinary terminal, EUD MMIO,
TOP_CFG=0x11 and all reset/fuse policy unchanged.
