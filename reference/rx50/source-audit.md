# RX50 source and binary boundary audit

2026-10-09. This is receive observability, not a demonstrated stability fix.
Sources downloaded locally have URLs and SHA256 in source-manifest.json.

## Actual managed implementation

[Microsoft's reference implementation](https://github.com/microsoft/referencesource/blob/main/System/sys/system/IO/ports/SerialStream.cs)
uses ClearCommError to obtain BytesToRead and in its background event loop.
The public property returns the queue size without exposing the error mask.
The terminal previously polled it without an ErrorReceived listener.
`audit-runtime.ps1` opens no port; it resolves call operands in this machine's
actual managed IL. installed-managed-runtime.json confirms both call sites
in System.dll SHA 2b3c17c6..., runtime 4.0.30319.42000. This is independent
of assuming a website branch matches the installed framework.

[ClearCommError](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-clearcommerror)
returns flags including receive overflow and clears accumulated error state.
[COMSTAT](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-comstat)
reports unread provider bytes. The diagnostic replaces the existing polling
call with the same API on the existing handle and saves its flags/queue depth.
It refuses a nonempty SerialPort character cache rather than undercounting.
A C# handler collects secondary-thread error notices without PowerShell
callbacks or display/file I/O on that thread. No second port handle is opened.

[ErrorReceived](https://learn.microsoft.com/en-us/dotnet/api/system.io.ports.serialport.errorreceived)
can be delayed and reordered. Polling and background flag clearing still
race, so both paths are recorded; no-error logs are observations, not proof
that every possible drop is reported. No DataReceived/string reader is added.
[ReadBufferSize](https://learn.microsoft.com/en-us/dotnet/api/system.io.ports.serialport.readbuffersize)
is a requested Windows buffer setting. The logged 4096 is not a measurement
of the installed driver's internal high-water threshold. No buffer or flow
control setting was changed.

## Exact installed qcusbser, instead of another source release

The installed binary and local CAB copy both hash to
ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151
(version 2.1.3.5, 252288 bytes). The local PDB hashes to
ee203464fc2ab419eaa66c90e345e24eba3fa0e103c0fe11f91e428897ef9155.
PE RSDS and PDB stream 1 both identify
66581f50-52c9-4a32-9ac6-fe0c57b94a80, age 1. All retained section headers
match byte for byte; selected public function starts match AMD64 exception
directory bounds. inspect-qcusbser.py checks these before disassembly.
Three generated guard symbols outside retained PE sections are reported
unmapped and never used as code addresses.

The reader follows [LLVM's MSF](https://llvm.org/docs/PDB/MsfFile.html),
[PDB info](https://llvm.org/docs/PDB/PdbStream.html),
[DBI](https://llvm.org/docs/PDB/DbiStream.html) and
[TPI](https://llvm.org/docs/PDB/TpiStream.html) formats. inspect-pdb-types.py
reads complete named C structures and rejects unsupported selected leaves.
qcusbser-selected-types.json retains only the relevant member offsets.

| Exact local function / RVA | Audited behavior and evidence |
|---|---|
| vPutToReadBuffer, 29250..298bb | CountL1ReadQueue above lReadBufferHigh (+408), or an incoming block larger than lReadBufferSize (+3f8) minus queued bytes, reaches 293b3..293bd: sets pSerialStatus (+2f0)->Errors bit 08 and returns without copying that block. Thus loss need not be a decoder error and can occur at a driver threshold. No such branch was observed live. |
| vPutToReadBuffer, 29599..295ae / 29664..296e4 | Pointer-crossing/full-buffer branches update pPerfstats (+2e0)->BufferOverrunErrorCount (+10); subsequent 29739..29740 sets the same status error. The early block-refusal branch does not increment that statistic here. A zero statistic alone would therefore be insufficient. |
| SerialGetCommStatus, 2b11c..2b32d | Counts read/write queues; copies the 20-byte SERIAL_STATUS to the caller at 2b2ef..2b2f9, then clears Errors at 2b2fd. The matching PDB names Errors offset 0 and AmountInInQueue offset 8. This installed version does not unconditionally return zero errors. |
| vResetReadBuffer, 298bc..2994a | Resets get/put pointers and read count. It was only inspected, never invoked as an experiment. |

The [official SERIAL_STATUS definition](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddser/ns-ntddser-_serial_status)
describes queue-overrun flags and their clearing on status queries;
[ntddser.h](https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/shared/ntddser.h)
defines SERIAL_ERROR_QUEUEOVERRUN as 08. These are driver-layer bits, distinct
from the Win32 CE_* mask returned by ClearCommError.

The modern local Qualcomm WDF source writes zero to SerialStatus.Errors,
but it is a different driver release and cannot describe this installed WDM
binary. RX36's 2.1.3.8 source also remains a version-qualified comparison.
No driver replacement, registry edit or endpoint reset follows from this audit.

## EUD TX boundary retained

Rechecked the QUIC COM header/source and the already archived matching
vendor EUD implementation. They provide no newly verified SM8150 TX-ready
handshake to replace the current timing. RX38 timeout/reset results remain
excluded. RX48's journal records issued MMIO, not hardware acceptance.
No kernel/TOP_CFG/pacing change is justified by this normal Windows sample.
