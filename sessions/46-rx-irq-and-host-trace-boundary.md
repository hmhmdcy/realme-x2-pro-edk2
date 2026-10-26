# Session 46: real IRQ reception and the missing host-frame boundary

2026-10-09, Asia/Shanghai. Continues sessions 41–45; preserves the verified
TOP_CFG=0x11 and complete-frame payload method. **Native terminal stability
is still unresolved.** Current diagnostic is IRQ candidate B, not RX44.
The exact captures and sources are in [reference/rx46](../reference/rx46/README.md).

## Result and evidence boundary

Actual IRQ reception works. The vendor EUD route is GIC SPI 492, translated
to hwirq 524; boot requested virq 19 and armed RX-only INT1 mask 01 after
the existing boot delay. Successful commands have exact complete payload,
`via=irq`, expected shell output and prompt. None of the measured frames
used the polling fallback.

Nevertheless Windows native C, `echo R46C\n` (LEN=10, one OUT), has an empty
raw response. The next counter query adds only its own one-byte Ctrl-U:
no additional IRQ entry, empty IRQ, pending observation, rejected header,
frame or tty byte is attributable to C. IRQ stayed active, fault=0, and
the query itself arrived by IRQ. This moves the observation boundary to
absent receive notification; it does not identify the cause or prove a
physical USB OUT happened. Notification could be lost before handler entry.
There is no evidence in this sample of BusyBox rejecting an accepted frame.

| Capture | Host OUT attempts / receipt | Device evidence |
|---|---|---|
| irq-native-a, echo R46A, LEN=10 | 1 / yes | Exact payload, IRQ, output and prompt; first candidate emits workqueue warning |
| irq-metrics-after-a | 2 / yes | irqs=pending=frames=irq_frames=2, bytes=11, tty_before=10 |
| irq-native-id, LEN=3 | 1 / yes | Exact payload, IRQ, uid=0 gid=0 and prompt |
| irq-native-b, echo R46B1234, LEN=14 | 1 / yes | Exact payload, IRQ, output and prompt |
| irq-metrics-after-b | 1 / yes | irqs=pending=frames=irq_frames=5, bytes=29, tty_before=28 |
| irq-native-c, echo R46C, LEN=10 | 1 / no | Zero captured bytes; no additional observation in next snapshot |
| irq-metrics-after-c | 2 / yes | irqs=pending=frames=irq_frames=6, bytes=30, tty_before=29 |
| libusb-native-d-ready / e / f-full | 1 each / yes | Three exact commands, LEN=10/10/14, each IRQ/output/prompt |
| libusb-metrics-after-f | 1 / yes | irqs=pending=frames=irq_frames=10, bytes=65, tty_before=64 |
| irq-f1 | 1 / yes | Deferred IRQ F1, irqs=11/fault=0; fastboot product independently msmnile |
| irq-b-native-h, echo R46H1234, LEN=14 | 1 / yes | Candidate B exact payload/output/prompt, no new workqueue warning |
| irq-b-metrics-after-h | 1 / yes | irqs=pending=frames=irq_frames=2, bytes=15, tty_before=14 |
| irq-b-f1 | 2 / yes | Deferred IRQ F1, irqs=3/fault=0; fastboot product independently msmnile |
| final-live-ctrl-u, fresh B reboot | 1 / yes | irqs=pending=frames=irq_frames=1, bytes=1, tty_before=0 |
| etw-before-ctrl-u | 1 / no | Zero captured bytes; bounded retry then obtained a fresh baseline |
| etw-before-ctrl-u-retry | 2 / yes | irqs=pending=frames=irq_frames=2, bytes=2, tty_before=1 |
| etw-r46g-capture.native, echo R46G, LEN=10 | 1 / yes | Exact IRQ payload, output and prompt under Windows USB ETW |
| etw-r46g-capture.metrics | 2 / yes | irqs=pending=frames=irq_frames=4, bytes=13, tty_before=12 |

All snapshots show poll_frames=empty=watchdog=drops=fault=bad=no_tty=overrun=
bad_id=bad_len=0 and active=1. Counter snapshots precede delivery of their
current Ctrl-U. Two OUT attempts with one receipt do not identify which
attempt was accepted. No exactly-once or long-term reliability claim.

Same-boot libusb captures use OUT 02 / IN 81, max packet/read size 16, no
COM setup/reset/ZLP. Each of the four OUTs has exact submitted bytes and a
matching status-zero full-length completion in usbmon (12/12/16/3 bytes).
This small successful set neither proves libusb reliability nor establishes
a Windows-only cause. WSL usbmon sees virtual host-controller URBs, not
physical bus ACKs. Older RX43 libusb receipt loss remains valid history.

The first libusb invocation, libusb-native-d, failed before any OUT because
usbmon was missing in that WSL instance. It is not a lost-receipt sample.
An explicit read-only usbmon preflight loaded the module/mounted debugfs,
then a fresh capture prefix was used. No USB filter/driver changed. The
later detach reported already not Attached; final Windows enumeration was
checked independently without assuming why attachment had ended.

## Source review and diagnostic implementation

See [source audit](../reference/rx46/source-audit.md) for fixed vendor links,
Linux IRQ/workqueue sources and host trace documentation. The actual samurai
node lacks interrupts, and the firmware configuration-table DTB is
authoritative. A kernel diagnostic supplies the vendor route only on
realme,samurai at 0x088e0000 with a direct three-cell GICv3 parent, validates
hwirq 524 and requests IRQF_NO_AUTOEN. No DTB or boot firmware was changed.
This workaround is not the final platform resource representation.

The handler reads STATUS1 then ID/LEN/all DAT under the shared UART lock,
without printk/tty/restart in hard IRQ context. A 32-frame queue separates
capture from work-context receipts and tty dispatch. After the existing
20-second delay from probe, save original INT1 mask 1c, enable only RX=01,
verify readback and enable the requested IRQ. TX/VBUS/charger interrupt
levels are excluded. No INT0 or STATUS1 write was added.

An eight-empty-IRQ guard, bad-header/queue fault and 20 ms watchdog can
disable IRQ, restore the original mask and retain polling. The watchdog
records pending observed while IRQ is active before falling back. F1 stops
IRQ and restores mask, then work context synchronizes IRQ, restores TOP_CFG,
disables EUD and calls kernel_restart("bootloader"). Remove stops/free_irq,
cancels work and disposes only a newly owned IRQ mapping. **Exceptional
fallback/remove paths were reviewed, not exercised on hardware.**

Console TX locking/pacing is unchanged; it still holds the UART lock for an
entire printk message and can delay IRQ handling. Zero stray bytes is only
a framing result, not proof of lossless TX. Some receipt timestamp prefixes
are incomplete even though the expected commands and responses are present.

Candidate A used deprecated system_wq for mod_delayed_work and emitted a
runtime warning on its first native command. Candidate B changes that call
to system_percpu_wq, matching this tree's schedule_delayed_work wrapper.
Both final Image builds have no compiler warnings. An earlier API-name
compile error was fixed to of_fwnode_handle before flashing. Existing
earlycon/ioremap boot warnings have not been resolved by this change.

RX45's source audit incorrectly said the vendor RX branch was gated by the
software mask. It reads the mask, but tests only STATUS1 for RX; TX also
tests the mask. That text is corrected without changing RX45 raw evidence.
Its verifier now checks an archived RX44 source, so a later current driver
does not invalidate historical evidence. The archived source is byte-identical
to the old external baseline, SHA256 e17acbd5….

## Windows USB trace: authorized capture and completion evidence

Built-in USBXHCI and UCX providers are present. Microsoft's
[USB ETW instructions](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/how-to-capture-a-usb-event-trace)
describe default/completion and PartialDataBusTrace payload events and require
administrator execution. The actual standard-user logman preflight failed
with -2147024891/E_ACCESSDENIED and explicitly requested administrator access.
No ETW session or ETL was started. This is an OS permission denial, not an
automatic approval-review rejection.

[eud-etw-step.ps1](../linux-port/scripts/eud-etw-step.ps1) is prepared and
PowerShell syntax-checked: one native echo R46G OUT, then a bounded counter
query; serial close/dispose and trace stop in finally; no flashing, resets,
filter or driver installation. The user explicitly authorized one administrator
capture. First the launch wrapper wrote metadata with the capture prefix,
creating a conflict with the helper's preflight protection; that process exited
with code 1 and no trace/manifest or device capture. Its exception was not
captured, so the exact failure message is unavailable. The wrapper was corrected to
use a separate metadata prefix and log errors. This failed launch is not an
RX or USB result. One actual elevated capture then completed successfully.

Before tracing, one Ctrl-U OUT had no receipt, and a bounded retry accepted
its second OUT. The resulting fresh baseline has two IRQ frames/two bytes.
Under tracing, echo R46G succeeds on its first OUT; its 10-byte payload,
`via=irq`, output and prompt are exact. The subsequent Ctrl-U sends two OUTs,
with one receipt after the second. Its snapshot has four IRQ frames/13 bytes,
so only echo10 plus one Ctrl-U1 added device frames/bytes. All fault/fallback
counters remain zero, active=1. The trace helper closes both serial owners,
then stops its session; completed=true/trace_stopped=true. An independent
logman query reports that exact session not found; both elevated PIDs exited.

The ETL has 3,692 events and its header reports EventsLost=BuffersLost=0.
Rundown identifies VID 05c6/PID 9505 and maps bulk OUT 02 / IN 81, MPS 16.
Three paired UCX dispatch/completion events on that OUT pipe have lengths
12, 3, 3 and USBD/NT status zero. The native command's 12-byte transfer and
both counter transfers therefore reached the measured Windows USB completion
boundary, while only two new frames were observed by the device. This is
stronger evidence than application Write/Flush alone, but is still not a
physical bus ACK or proof of original payload bytes. The reviewed normal and
less-restricted tracerpt XML provide header fields/buffer pointers, without
verified OUT payload data. Do not say the captured on-wire bytes are exact.

Original all-device ETL/XML remain local. Reviewed target rundown, endpoints,
six OUT events and trace header are in etw-eud-selected.xml, with source hashes
and matched summaries in etw-eud-summary.json. Other USB devices are excluded
from this export. tracerpt emits an unusual +07:59 timestamp offset; preserve
the original strings and compare intervals, without guessing UTC conversion.

The next distinct instrument must recover original Windows OUT payload bytes
or lower-level physical completion detail and correlate them with IRQ counts.
Search the provider/schema and actual qcusbser implementation before changing
capture keywords or installing any instrument. The one authorized capture is
finished; do not start an unattended elevated loop. Do not repeat
the mask-only, zero-wait DAT, reset/ZLP or generic delay experiments without
new evidence. A passing short libusb set alone is not a terminal fix.

## Build, image and final live state

Live enumeration/ownership was checked first; fresh RX44 Ctrl-U and F1 were
recorded. Every serial owner closed/disposed in finally. All probes were
manual, short and bounded with unique captures. Only logdump was flashed,
twice (A then B); boot and other partitions were unchanged. Incremental
builds preserve the actual initramfs and existing kernel changes. Packaging
copied the RX41 FAT, replaced only Image and byte-compared extracted Image
and DTB. Do not use stale build-image.sh to replace the real initramfs.

| Artifact | SHA256 |
|---|---|
| Current logdump-rx46-rx-irq-b.img | ba1689b380b40aeee2714ae7c41b44a7db3365ef61c0937b607b12537b6c320e |
| Current Image / Image-irq-candidate-b | e0f256d7b08410bc7cd17db03aa2351338753bb7b9add562d3bcedc29964fba3 |
| Current linux-port/eud.c / eud-irq-candidate-b.c | 673c485843bc551788a0eb90499207371110807d4700a1f3f20d42b76e4e921f |
| First logdump-rx46-rx-irq.img | 22e7ceb4f74bcafe93d1dd5ec1c907b075657137521f0e8c02e867e6c40dbef4 |
| First Image / Image-irq-candidate | ddefb54c52963acc9a8ad447e3da8d4da56b6e60abddd213937d3b875378b8cc |
| First source / eud-irq-candidate.c | 2666a654225f898f07b8e3696f7ba6cc203ee3d0746ce4bf66286cc190f035cb |
| Rollback logdump-rx44-rx-stats-ctrl-u.img | cefc82252e203e3bbb5a27b9b302c807d6d1ee82c49318ed2d6a54661660db9d |
| Rollback Image / Image-before-rx46 | 937960d0754b92c8797404b7cdd9159a710b9897c6f2be576bd980d0bca0a87e |
| Rollback source / eud-before-rx46.c | e17acbd5d6139c94c3e22f6d6bcd442186d3bd24e9292a10e29f3d5781970dd2 |

Images/backups remain in E:\edk2-samurai-out; evidence originals in rx46.
Actual init SHA256 e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab
and BusyBox SHA256 999cb969d09093a71716cfc747bb53cdada3f332c05eb5046c56e0f66a4d6d22
remain unchanged. Compatible terminal scripts were not modified.

Final B was rebooted without reflashing after its F1 test. final-boot has
13,919 decoded frames, zero stray, TOP_CFG=0x11/original zero, requested and
armed IRQ and shell startup. Fresh post-reboot Ctrl-U succeeds on its first OUT.
Later the authorized USB trace counter receipt confirms irqs=frames=4,
bytes=13, tty_before=12 with active=1/fault=0. COM14 is closed/disposed and
ETW is stopped; 9501/9500/9505 OK;
USBIPD 6-5 Shared/not Attached. This is a last measured snapshot, not a
promise of future live state. Current Windows and actual Linux eud.c/Image
match candidate B.

`reference/rx46/verify.py` checks 25 raw capture sets, hashes, exact outputs,
counter deltas, USB completions, F1/fastboot and builds. RX45 historical
verification and docs-health-check must also pass before pushing fork/master.
The goal remains open until native terminal stability has been demonstrated.

## Production debug access

Rechecked the public QUIC EUD description and Linaro's firsthand report.
There is no universal five-peripheral "retail fuse list" established for
RMX1931. This unit's CTRL/COM are usable; SWD/JTAG USB transport works but
the tested AP DAP returns no acknowledgement; TRACE is unvalidated and
debug-fuse values have not been read. A permitted OEM-signed debug policy or
debug-enabled device could provide additional instruments, but no unlock
method has been demonstrated here. TRACE is not a USB wire analyser. Keep
the [qualified access evidence](../SWD-JTAG.md) separate from COM failure
evidence; do not switch DAP mux or flash APDP/fuses to pursue this sample.
