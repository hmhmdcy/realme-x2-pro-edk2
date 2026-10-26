# Session 63 — live single-device compatibility and guarded rollback tools

2026-10-10 Asia/Shanghai. Goal-turn audit: **PROGRESS**. Previous RX62 was
progress: real full build, valid package/file-only signatures and published
727657e. This session adds actual native compatibility and current kernel
policy evidence, plus prepared trial/rollback tools; no new phone experiment.

## Actual compatibility and loading boundary

At the fresh RX63 baseline, three nodes are OK, original oem102.inf/2.1.3.5
bound, no known owner/logging/trace, Shared/not Attached. Original driver,
terminal and RX53 logdump hashes agree with RX62. Existing builds/downloads
are terminal; no live process handle justifies a verified-wait classification.
The loading environment question sent in RX62 is still unanswered.

Compiled an in-process C# SetupAPI adapter in native Windows PowerShell.
The adapter opens exactly the present 9505 device-info element and confines
each compatible-list search to one exact INF. Two actual metadata audits
identify **exactly one** EudInstall candidate node at 5.47.2.26 and exactly
one QportInstall00 original node at 2.1.3.5. Observed x64 structure sizes:
32/584/1568/1584. The installed binding is identical before/after; all
candidate and rollback package hashes remain unchanged, including the old
PNF. No package was staged, bound or loaded. Compatible-list recognition
does not establish functional driver compatibility.
[SetupAPI list scope](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/nf-setupapi-setupdibuilddriverinfolist).

Read current Code Integrity through NtQuerySystemInformation, without an
administrator BCD query or any boot-setting write. Runtime options are
**0x0000F401**: TESTSIGN 0x2 absent, HVCI kernel enforcement 0x400 present.
Secure Boot remains 1. The public certificate does not satisfy the required
machine Root/TrustedPublisher trust gate. Current Install guard returns
three refusal reasons (non-elevated, unsupported current loading policy,
certificate trust); actual stage/install call counters are both zero.
This is a host-policy boundary, not another device fault or automatic
approval-review rejection.
[Documented CI bits](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntquerysysteminformation).

## Prepared single-device installation and rollback

Microsoft explicitly says PnPUtil /add-driver /install does not force a
lower-ranked driver. It also updates any matching devices. A newer candidate
can therefore make an assumed simple old-INF reinstall an ineffective
rollback. The prepared alternative stages the fixed package, then passes an
explicit driver node and one device-info element to DiInstallDevice. Initial
selection of both exact driver nodes has now been exercised read-only;
the actual stage/bind calls remain **unexecuted**.
[PnPUtil rank behavior](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/pnputil-command-syntax),
[Specific-device API](https://learn.microsoft.com/en-us/windows/win32/api/newdev/nf-newdev-diinstalldevice).

EudDeviceDriver.cs / eud-driver-trial.ps1 default to Audit and never request
UAC or change trust/BCD/security. They guard exact candidate/rollback bytes,
one present 9505, 64-bit/elevated execution for mutation, owner/USBIP status,
actual driver binding and current policy. Install requires the exact original
binding, current test-signing support and an unexpired/trusted public cert.
Restore is confined to this exact candidate; it allows a failed 9505 node
while the hub/Control nodes are healthy, so a candidate load failure does not
itself block rollback. No broad driver update, package deletion, null driver,
force bind, 9501 change, implicit retry or automatic reboot. NeedReboot stops
before any serial test. Actual return/binding behavior is not yet validated.

Fifteen pure-gate cases passed, including wrong control PID, extra 9505,
active owner/relay, altered package, wrong trust/time/kernel policy, non-admin,
unknown binding and failed-load recovery. They also read live COM14. Zero
mutation calls. These tests cover the potentially consequential tool gates;
they do not simulate a successful kernel load or USB stability.

Initial audit read PortName from the software key and returned null. Corrected
it to the hardware Enum/.../Device Parameters key: live COM14 is verified.
The WDF option keys remain in the separate PnP-resolved software key. The
first guard-test reader used Windows PowerShell's ANSI default against UTF8
JSON; explicit UTF8 corrected its read. Original raw JSON is intact. These
are tooling corrections; no phone operation consumed those errors.

## Separate ZLP option needs DeviceAdd, not ordinary reopen

Checked the exact compiled QCPNP/QCWT/QCMAIN.h source hashes. The vendor
registry processor runs from **QCPNP_EvtDeviceAdd** (call line91); it is not
called by ordinary FileCreate. QCDeviceZLPEnabled defaults true, accepts
DWORD0 as false, positive as true; absent/failed lookup retains true. Its
device software-key value populates driver-global gVendorConfig.

QCWT bases additional ZLP on requested write length being a multiple of
nonzero maximum packet size, after submitting the original async write;
it does not wait for successful completion. The historical RX52 endpoint
descriptor is max_packet16, so native payload14/wire16 meets that condition.
No fresh descriptor control query or payload test occurred this session.

Keep ZLP unchanged for the first same-binary FileCreate flag-off/on trial.
Later, change ZLP separately and prove DeviceAdd/registry reread plus actual
zero-byte OUT behavior. Ordinary close/open will not refresh that option;
a power-only/restart path must not be assumed to recreate the device object.
No registry flag, INF, C module, signed binary or terminal was changed here.
The full original LEN14/F1/console/native/compatible acceptance remains open.

## Delivery and next action

reference/rx63 contains actual audits, native/script sources, gate results,
source-phase audit and trial-review.md. The exact signed driver package is
still external RX62; RX61 old-driver rollback is unchanged. Private keys,
SYS/PDB/catalog/certificate binaries and full source/kit stay outside Git.
Current post-state preserves TOP_CFG0x11/full-frame/RX53 console/IRQ/F1/
terminals/RX48 firmware rollback. No serial/USB data owner, driver install,
trust/registry/security change, UAC, flash or phone/PC reboot. Native info lists
and detail buffers are released in finally; no serial handle opened.

The original stability goal is **not achieved**: candidate kernel loading,
actual off/on reset behavior, exact first-frame preservation, once-only native
BusyBox output, long console, full LEN14/ZLP and F1/compatibility still need
the selected supported environment and real measurements. Do not substitute
metadata/gate success, padding, a retained handle or a short passing variant.
No elapsed time or automatic goal continuation counts as approval for new
driver/host security scope. Do not resend the already-pending environment
question or repeat RX59/60's old hardware contrasts.

Next available hardware action: use the selected supported physical Windows
environment, validate the protected single-device path, then execute RX62's
same-binary toggle comparison and full acceptance matrix with manual bounded
steps, fresh startup receipts, once-only data and finally Close/Dispose/Detach.
Record/push fork/master only. Previous published tip727657e; goal remains open.
