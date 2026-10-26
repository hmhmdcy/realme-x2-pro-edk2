# Session 60 — even-IN reversal and a host toggle candidate

2026-10-10 Asia/Shanghai. Goal-turn audit: **PROGRESS**. The original native
terminal stability goal remains open; this session does not claim a repair.

## Result and implication

RX59 deliberately closed after 75 short IN frames and two short OUT, then
ordinary reopen reproduced missing seq12407 while the first Ctrl-U succeeded.
The pre-defined RX60 reversal closes after **74 short IN frames** with two
short OUT. Ordinary reopen receives the entire first timestamp/status and
accepts its first Ctrl-U. CRC **ada51499**, seq **13654..14165**: all **512**
records match directly, including 169 prior RX59 records, 74 owner-1 records
and 269 owner-2 records. No interpolation or timestamp-only inference.

This changes a predicted fault boundary and strengthens toggle mismatch as
the ordinary-reopen explanation. It is one contrast, not a failure-rate
estimate, physical DATA0/1/ACK capture, or proof that every historical RX/TX
failure shares this cause. RX41 whole-frame/TOP_CFG and RX53 console handling
remain separate, previously measured fixes.

| Measurement | Owner 1 | Owner 2 |
|---|---:|---:|
| Observed IN frames | 74 | 1415 |
| Raw/GET_STATS bytes | 442 | 8450 |
| First status bytes | 324 | 336 |
| First Ctrl-U TX / receipt, ms | 3019 / 3094 | 3011 / 3043 |
| Manual close, ms | 38237 | 55168 |

Owner 1 sends unexecuted `abc` once at 30138 ms, receipt at 30177 ms. The original
aim was around 22000 ms; this later send is a recorded timing deviation. It
still closes manually near RX59's 39798 ms and well before its 60-second bound.
Owner 2 measures the initial status then freezes one 3120-byte journal with
`dd ... bs=4096 count=1`, exports base64, drains, and manually closes. Nine data
frames are sent once only; no startup or data retry. All read offsets/counter
deltas match raw; both finally Close/Dispose/Detach, with no pending/queued/
stray/buffered/retained query. No BusyBox execution-output gap appears here.

## Coverage and workflow corrections

Human continuing authorization covered the prepared same-scope two-value
logger/ETW helper. Its UAC launch stayed pending, pid null; after approximately
489 seconds a control-directory late-Arm guard was set, then the exact launcher
was stopped. No helper/backup began and no registry/PnP/ETW mutation occurred.
The original joint plan is preserved; the no-admin replacement was separately
recorded **before** execution. It lacks initial PnP reload, driver raw logger
and new ETW; do not represent it as another joint capture.

The first combined read-only preflight incorrectly matched its own parent's
command text as an owner. UAC was launched before noticing that failed baseline
result. No helper ran; a separate baseline passed before any device IO. The
late-Arm block and fresh no-admin baseline prevent carrying that mistake into
the hardware experiment. This is a workflow error, not another phone failure.

## Concrete repair direction and candidate limits

Microsoft documents that reset-and-clear-stall resets the host toggle; a
device that preserves its toggle can treat the next packet as a duplicate.
The exact installed qcusbser Open path calls reset selector 2 -> URB 0x1e for
both endpoints (RX54/RX56). Its audited settings contain no identified supported
skip-reset knob. [Microsoft URB documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usb/ns-usb-_urb_header).

The newer Qualcomm release source still performs IN/OUT reset on FileCreate
through WdfUsbTargetPipeResetSynchronously; upgrading alone is unproven.
[Pinned Qualcomm source](https://github.com/qualcomm/qcom-usb-kernel-drivers/blob/14b6fe1ee69cdd9182502629da9192156b9d206a/src/windows/wdfserial/QCPNP.c).

An **offline experimental patch** is prepared against that open-source driver.
Only VID 05c6/PID 9505 with newly defined `QCEudPreserveToggleOnOpen` DWORD=1
bypasses ordinary FileCreate resets. Defaults, other devices, missing/wrong
settings retain the existing path. Idle power reference, DTR/RTS, worker wake
and completion remain. All functions after FileCreate, including preparation,
close and recovery, are byte-identical to the pinned source. The flag is not
an existing setting for installed qcusbser; no registry value was written.

Patch applies and reverse-checks against the SHA-pinned source. An extracted
actual patched/baseline FileCreate harness compiles with gcc and passes 14
dispatch/error/resource cases. It checks exact inactive lifecycle equality,
zero reset calls for opt-in EUD, balanced keys and idle references. This is
**mocked WDF testing**, not a full WDK build, signed package, driver installation
or hardware repair. Current machine has SDK headers but no located WDK build
environment in this audit. Full-packet OUT/ZLP XACT_ERROR is also unchanged.

Next work must evaluate this concrete preservation route or another supported
host route, then validate original native receipt/output across ordinary
reopens. Complete build/signing and a controlled reversible driver comparison
are prerequisites to installing this candidate. Preserve working firmware;
do not repeat the same even passing contrast, random echo/reset loops or
arbitrary fuse/PHY/clock changes. Keep startup-only sync retry distinct from
once-only command input. SWD/JTAG/TRACE do not supply a measured solution here.

## Restored state and publication

Independent post-state at **2026-10-09T20:42:30.6746670Z**: all 9500/9501/9505
nodes OK, no known owner, COM14 closed, USBIP 6-5 Shared/not Attached, two
temporary values absent, no EUD trace. Installed qcusbser, terminal and RX53
logdump hashes equal the baseline. No flash, phone reboot, driver install or
kernel change; TOP_CFG=0x11, F1/console/compatible/native and RX48 rollback
remain. Prepared late Arm is blocked; no admin helper remains active.

Frozen evidence and offline replay: [reference/rx60](../reference/rx60/README.md).
Full source/PE/PDB/images/scratch binaries stay local. Record and push only
fork/master. Previous published tip da915a8; this session is the next commit.
