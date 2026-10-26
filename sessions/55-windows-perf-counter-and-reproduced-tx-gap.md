# Session 55: reproduced TX loss before the Windows accepted-buffer counter

2026-10-10 (Asia/Shanghai). The RX53 kernel/image and installed terminal remain
unchanged; no flash, reboot, USBIP owner, reset or new administrator ETW.
One bounded Windows diagnostic owner uses the existing COM14 handle, manual
commands and finally Close/Dispose. The stability goal remains active.

## Finding

A fresh first-status TX loss recurs: software journal **seq 7376**, console
payload `[ 16`, wire `90 04 5b 20 31 36`, is absent from Windows raw. The raw
starts `88.479011] eud: tty byte=15`. The CRC-valid 512-frame journal spans
7349..7860, CRC b7e6a803. Its preceding 27 records directly match the unchanged
RX54 restored-native raw tail; the following 484 directly match this owner's
raw prefix. All other 511 records match without interpolation.

The new read-only `IOCTL_SERIAL_GET_STATS` observes the exact installed WDM
driver's accepted-buffer counter. Before startup it reports ReceivedCount=53667,
with queue=0 and raw offset=0. After the drained first status, its delta is
**309 wire bytes**, exactly the raw length; the journal requires **315** including
the absent six-byte frame. The missing bytes therefore were not counted at
that boundary. A loss solely in application Read, decoding or display is
excluded for this sample. EUD TX, physical USB and the driver before/in buffer
acceptance are still unresolved; the CPU journal is not a physical TX ACK.

All six snapshots have zero in/out queue and error flags. The cumulative error
fields also remain zero; no overflow/error event is observed. That does not
exclude every early refusal: RX50 established that some refusal branches occur
before ReceivedCount, and .NET's background error observer can clear flags.
Do not claim a USB/silicon fault solely from these counters.

## Other current behavior and measurement bounds

The first startup Ctrl-U still receives no RX acceptance; the second does.
RX54 left two accepted frames; the new status has three. Nineteen subsequent
data frames all execute once with receipts; final accepted total is 22,
bytes/tty=249, IRQ frames=22, poll/watchdog/bad/drops/fault=0, active=1,
console_frames=0. This is a session-start problem alongside the TX loss. It
does not invalidate RX53/RX54's independently verified long-console RX fix.
Only startup sync retries; no data command is retransmitted.

ReceivedCount 53667..64558 gives 10891 wire bytes, matching all 1831 raw frames
and 288 saved reads. Every drained interval matches separately: 309, 2672,
6724, 1186, 0 bytes. TransmittedCount delta 277 matches the host's submitted
wire lengths, including both startup attempts. It is not proof that both
startup writes reached phone RX. Six GET_STATS queries are pending initially,
complete with 24 bytes and report 0 ms in the C# timer. No periodic query is
inserted during output: baseline, manual idle snapshots and before-close only.

The first read-only journal command used the wrong tty-child sysfs path and
returned ENOENT. Correcting it to the known platform path in the same owner
produced the immutable 3120-byte snapshot; original commands/errors remain in
raw/events. No reconnect or extra hardware cycle was needed. The first offline
ABI check also used a MethodInfo-only inspector on a constructor and failed
before opening a port. The diagnostic copy accepts MethodBase for that static
inspection; compilation, installed constructor BindHandle identification,
PowerShell syntax and the x64 ABI then pass.

## Shared-handle query implementation and research

The separate diagnostic derives from RX50; `EudSerialPerf.cs` borrows its
already-open .NET Framework SerialStream SafeFileHandle. GET_STATS is
0x001b008c, output 24 bytes / six uint32 fields. The local Windows SDK 26100
ntddser.h and RX54's exact PE/PDB type/handler establish the layout. GET_STATS
does not clear counters; CLEAR_STATS is never sent.

The installed constructor's IL calls ThreadPool.BindHandle. A valid private
manual-reset event in the 32-byte OVERLAPPED has its hEvent low bit set, preventing
this native request from entering the CLR completion port. Wait is bounded to
500 ms. If necessary, CancelIoEx targets **only this query's** OVERLAPPED, then
waits another 500 ms. Native buffers/event remain alive until completion; a
still-pending failure stops further queries and retains at most one allocation
through close/process lifetime. These timeout paths did not occur in this run.
The port retains handle ownership and is closed before probe disposal.

Primary sources consulted before execution:

- [GET_STATS](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddser/ni-ntddser-ioctl_serial_get_stats): cumulative serial statistics.
- [DeviceIoControl](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-deviceiocontrol): valid OVERLAPPED required on this handle.
- [GetOverlappedResultEx](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-getoverlappedresultex): bounded result/completion retrieval.
- [GetQueuedCompletionStatus](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-getqueuedcompletionstatus): hEvent low bit suppresses completion-port notification.
- [CancelIoEx](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-cancelioex): cancellation is a request; retain storage until completion.
- [Microsoft SerialStream source](https://github.com/microsoft/referencesource/blob/main/System/sys/system/IO/ports/SerialStream.cs): managed overlapped owner and completion-port binding, checked against installed IL.

Next audit the exact installed receive-worker/completion path before
vPutToReadBuffer, and correlate a reproduced gap with evidence at that boundary.
For startup loss, retain OUT/RX count distinction. Do not run unchanged idle
echo, mask-only/reset/ZLP or zero-wait loops as stability proof, and do not
change TX MMIO pacing/TOP_CFG or invoke SWD/JTAG/fuses without new evidence.

## Preservation and artifacts

Originals: `E:\edk2-samurai-out\rx55`. Export and strict reproducible analyzer:
[reference/rx55](../reference/rx55/README.md). Raw/bin and executed helpers are
byte-identical; derived JSON/text is UTF-8 LF with original/exported hashes.
Images, installed driver/PDB and other-device traces stay outside Git.

Kernel driver 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4;
Image 33efc6bc0c1c2d7b82b80b39dc7cea2331d05cca2005376399dade92b1597952;
logdump-rx53-console-rx.img 50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93;
installed terminal 9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57.
Immediate rollback is unchanged RX48 B. TOP_CFG=0x11 whole-frame RX,
header-only F1/console/default compatible and installed native terminal remain.

Owner closes at 135439 ms: no pending input/wire, zero stray, no retained
query, probes disposed. Final independent state: three nodes OK, COM14 closed,
no known owner, 9505 Shared/not Attached. Zero flashes/reboots. Publish only
reviewed evidence/docs to fork/master after the required health check; this
narrows an actual fault and is not a stability fix.
