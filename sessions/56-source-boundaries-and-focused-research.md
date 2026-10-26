# Session 56: consolidate the remaining faults and search at the missing boundary

2026-10-10 (Asia/Shanghai). Read-only exact-driver/source/research audit after
RX55. No serial open, USBIP attach, host OUT, flash, reboot, reset, registry
write, driver replacement or new administrator capture. The stability goal is
unresolved. Original audit files: `E:\edk2-samurai-out\rx56`; selected evidence:
[reference/rx56](../reference/rx56/README.md).

## What has actually improved

The growing experiment count is not a growing repair count. Repeating ordinary
passing commands has diminishing value and is no longer an accepted next step.
The following separates repairs from corrections and measurements:

| Finding | Current meaning | Evidence |
|---|---|---|
| TOP_CFG=0x11 with whole-frame RX | Verified repair of repeated first payload byte; retained | RX41: two UEFI boots, Linux ABC/DEFG/LEN14 and shell execution |
| Previously reported native id/echo/console missing output | Those samples were already complete in raw; display filtering corrected | RX43; this does not explain later actual TX gaps |
| RX during long console output | Targeted repair verified on both host paths, nine further overlaps and console F1 | RX53/54; other missing receipts remain possible |
| Startup input lacks receipt | Still unresolved; RX55 first Ctrl-U absent, second accepted, then 19 once-only data frames accepted | Host write completion is not a phone RX receipt |
| One issued TX frame absent | Still unresolved; RX55 seq7376 wire `90 04 5b 20 31 36` absent, 511 other records directly match | CPU journal records MMIO issuance, not physical USB ACK |
| RX55 received counter equals raw: 309 vs issued 315 bytes | New localization, not a repair | This sample's gap is before the installed driver's accepted-buffer counter; a solely later application/display loss is excluded |

No evidence establishes an unavoidable silicon/fuse limit. Successful COM
traffic also does not prove every other EUD debug peripheral is authorized.
SWD/JTAG/DAP access is a separate question and supplies no demonstrated fix for
these intermittent COM faults.

## Exact installed driver: new boundaries

The PE/PDB identity remains the installed **WDM 2.1.3.5**, not the public newer
WDF tree: sys SHA ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151,
PDB SHA ee203464fc2ab419eaa66c90e345e24eba3fa0e103c0fe11f91e428897ef9155,
GUID 66581f50-52c9-4a32-9ac6-fe0c57b94a80, age 1. Exact .pdata function bounds
and PDB section-header equality are checked. RX50/54 identities are dependencies.

1. **Open/reset request, now traced to its selector.** QCSER_Open at 2a786 calls
   QCUSB_ResetInput with selector 2; successful return leads to selector 2 for
   QCUSB_ResetOutput at 2a797. Each reset function maps selector 0 to URB 0x30,
   selector 1 to 0x31, other selectors (including 2) to **0x1e**. This is the
   reset-and-clear-stall operation in the Microsoft documentation already used
   in RX47. These calls are conditional; code alone does not prove the branch
   ran in RX55. RX47's old ETW independently observed endpoint resets.
2. **The acceptance counter is downstream of more than USB completion.**
   A full direct-call scan identifies ReadIrpCompletion's 25467 call as the
   only direct call to vPutToReadBuffer in executable function bounds. Successful
   status with nonzero active bytes first calls QCRD_AdjustPaddingBytes, then
   vPutToReadBuffer. Error/status paths can bypass it. Direct-call uniqueness is
   not a claim that indirect calls or every runtime branch were observed.
3. **An earlier raw-data observation path exists.** QCSER_ReadThread's successful
   URB-completion path calls QCSER_LogData at 24e22 with the URB buffer/actual
   length, before later ReadIrpCompletion/padding/buffer acceptance. It requires
   EnableLogging and hRxLogFile. The exact logger writes time/type/length/data
   and requires PASSIVE_LEVEL. This is a potential observation boundary, not
   proof of runtime logging or a lossless physical capture. File writes may
   change timing; the selected worker must first be established.
4. **Padding does not explain the RX55 missing frame by itself.** The exact
   adjustment only subtracts four bytes for lengths congruent to 5 or 6 mod 64
   with terminal `de ad be ef` and its capability enabled. Missing payload
   `5b 20 31 36` is not that sentinel; subtracting four bytes also would not
   remove the whole six-byte wire frame. Do not repeat generic padding/ZLP tests.

Decoded exact registry-name references include QCDriverConfig and
QCDriverLoggingDirectory. A read-only snapshot of the service root, actual
device class key and Device Parameters finds neither configured there. It does
not establish all possible registry locations or live worker flags. No key was
written; logging was not enabled. A concrete reversible logging experiment is
not ready until actual configuration scope/worker/lifecycle are established.

The startup reset/toggle hypothesis is plausible: resetting only the host's
sequence state while the device retains its state could discard a first packet
and then recover. **This is still a hypothesis.** No physical DATA0/DATA1 was
measured, and it is not a universal explanation for RX52's already repaired
same-owner long-console trigger. Reset code plus similar symptoms is not proof.

## Search extracted from the combined evidence

General searches for EUD/RX lost receipts produced mostly unrelated EDL and
other uses of the acronym. Search terms now carry the actual boundary:

| Query/topic | Result read this session | Use and limit |
|---|---|---|
| `Qualcomm EUD COM USB clear halt data toggle` | Microsoft URB reset/toggle documentation; already used in RX47 | Reused material, now connected to exact installed selector 2. It describes a possible mechanism, not an EUD-specific fix |
| `site:github.com/quic/eud` COM support/issues | [Issue 6](https://github.com/quic/eud/issues/6), dated 2026-05-20; inspected current [com_api.cpp](https://github.com/quic/eud/blob/main/src/com_api.cpp) | Newly inspected issue, with an independent source check: the sample data loop is inside a FIXME comment. The issue is a user's report, not a maintainer promise or a hardware limitation |
| EUD implementation outside QUIC | [OpenOCD EUD commit](https://github.com/openocd-org/openocd/commit/d06edabdcdad9c4ed5d66102311c89c5c44e4e87) and [official guide](https://openocd.org/doc/html/Debug-Adapter-Configuration.html) | New reference: implementation configures SWD, not a COM terminal. Its included [COM descriptor](https://github.com/openocd-org/openocd/blob/d06edabdcdad9c4ed5d66102311c89c5c44e4e87/doc/usb_adapters/eud/05c6_9005_eud_com.txt) independently shows PID9505, IN81/OUT02, max packet16; no COM loss fix |
| `QCSER_LogData` / `ReadIrpCompletion` / installed-driver pre-buffer boundary | Newly read QCRD.c at the older [Qualcomm-copyright source mirror](https://github.com/David112x/qualcomm-usb-drivers/blob/ec7480366fc322a7473ec02f6941e8b3e813bbe9/QMI/win/qcwwan/serial/QCRD.c), checked against exact PE/PDB | Reveals useful pre-buffer log flow; older mirror is not source-identical to installed 2.1.3.5. Exact binary is the implementation authority |

Primary background: [Microsoft URB semantics](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usb/ns-usb-_urb_header),
[Microsoft error/status recovery](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/how-to-recover-from-usb-pipe-errors),
[libusb device handling](https://libusb.sourceforge.io/api-1.0/group__libusb__dev.html).
The public [Qualcomm driver tree](https://github.com/qualcomm/qcom-usb-kernel-drivers)
was revisited; no source-identical installed-driver fix was found. GitHub's
unauthenticated API requests were rate-limited; raw source/browser retrieval
worked. No issue/comment was posted and no third party was contacted.

## Reuse the existing capture before asking for another

Offline RX46 ETW audit: 196 target transfer events, 95 target IN completions.
Lengths: 79x6, 2x3, 1x5, 1x4, 12x0 bytes; sum **489**, equal to that capture's
180-byte native plus 309-byte metrics raw. These are old aggregate lengths,
not the RX55 reproduced-gap payload. No payload event or physical data PID was
captured; the equality cannot locate seq7376. Full other-device ETL/XML remain
local. No second administrator capture was performed or authorized here.

## Next decision, with a stopping rule

Prioritize a measurement **before buffer acceptance during an actual gap**:
identify the live single/multi-read worker and a usable pre-buffer byte source,
then prepare one bounded capture that retains original URB data/status alongside
GET_STATS/raw/journal. If the missing wire frame exists there, investigate the
driver's later status/queue/refusal path. If it is already absent, focus upstream
on EUD/USB; physical PID/ACK is still required to prove toggle desynchronization.

A startup parity contrast is only worth doing with a justified, observable
packet-state prediction; raw frame parity alone is not established physical
toggle state. No unchanged reopen/reset loop is scheduled. A passing run without
the gap does not resolve the boundary. After a bounded inconclusive sample,
record exactly what was missing and change the observation method before another
hardware cycle. Do not retransmit data commands or hide missing TX as warm-up.

Final read-only checks: three EUD nodes OK, no known helper owner, COM14 listed,
9505 Shared/not Attached. Installed terminal SHA9c7a16f1... and RX53 driver,
Image/logdump hashes unchanged. TOP_CFG=0x11, F1/console, compatible/native
terminal and RX48 rollback retained. This session adds source exclusions and a
more useful next observation; **it installs no repair**.
