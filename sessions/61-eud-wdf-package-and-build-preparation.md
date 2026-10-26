# Session 61 — dedicated EUD WDF package inputs and build preparation

2026-10-10 Asia/Shanghai. Goal-turn audit: **PROGRESS**. Native terminal
stability remains open. No serial/USB I/O or new phone experiment this session.

## What is located, and the intended fix

RX59's forced 75-IN ordinary reopen loses exactly the first six-byte frame;
RX60's pre-defined 74-IN reversal receives all 512 journal records directly.
The installed Open path resets both bulk pipes with URB 0x1e. This supports
host/device data-toggle mismatch as a concrete explanation for ordinary-reopen
first-packet loss, without physical DATA0/1 capture or proof that every missing
startup receipt and command output has one cause. See sessions 59 and 60.

The repair candidate skips only ordinary FileCreate IN/OUT resets for
VID 05c6/PID 9505 with the new opt-in DWORD QCEudPreserveToggleOnOpen=1.
Preparation, close, recovery and other devices retain upstream behavior.
The RX60 patch and its 14 mocked dispatch tests remain the implementation;
they are not a full driver build or a measured repair. Microsoft documents
the lost-sequence mechanism and a way to preserve host toggles.
[URB documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usb/ns-usb-_urb_header).

## Complete pinned source and a dedicated package

Fetched the complete official Qualcomm source at
14b6fe1ee69cdd9182502629da9192156b9d206a. ZIP SHA256
ed5b4309139a286f3ef22ad846495bd7dbcb879dce4b4fa66e1d54d3663641a9.
Validated archive paths, retained notices, applied the unchanged RX60 patch.
All nine C modules were compared byte-for-byte with the pinned archive:
only QCPNP.c changes; every function after FileCreate is unchanged.
[Pinned release source](https://github.com/qualcomm/qcom-usb-kernel-drivers/tree/14b6fe1ee69cdd9182502629da9192156b9d206a).

The release's stock qcwdfser.inf has **no 9505/EUD match**. Authored qceudexp.inf
matches only USB\VID_05C6&PID_9505, uses separate service qceudexp and catalog
qceudexp.cat, and enables the new candidate flag. The qceudexp.vcxproj retains
the production project's nine modules and replaces its broad modem/serial
INFs with this one EUD INF. It does not modify the production project.

The package declares KmdfService and the literal $KMDFVERSION$ stamp token,
and uses DIRID 13 / ServiceBinary %13% for a package-owned binary. No global
USB flags, other hardware IDs or QCDeviceZLPEnabled change. XML and authored
input checks pass; **WDK InfVerif, Inf2Cat, linking and signing have not run**.
[WDF INF directives](https://learn.microsoft.com/en-us/windows-hardware/drivers/wdf/specifying-wdf-directives-in-inf-files),
[Driver Store execution](https://learn.microsoft.com/en-us/windows-hardware/drivers/develop/run-from-driver-store).

Source review confirms two bulk endpoints without interrupt enter the serial
branch. Baud/line coding and DTR/RTS use local state there; CDC requests are
confined to CDC devices. GET_STATS is implemented. D0Entry wakes workers and
contains no reset call. FileClose cancels outstanding I/O. The new registry
lookup runs in a callback documented at PASSIVE_LEVEL. This is source review,
not observed compatibility of a loaded candidate.
[FileCreate callback](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfdevice/nc-wdfdevice-evt_wdf_device_file_create).

QCWT still adds a zero-length OUT after a transfer whose length is a multiple
of endpoint maximum packet size. The separate RX59 16-byte/ZLP XACT_ERROR
boundary is unchanged. Do not mix a ZLP change into the initial toggle
comparison or claim this candidate already fixes all long-command failures.

## Build environment and actual loading prerequisites

No located MSBuild/Visual C++ compiler/WDK kernel build kit in the prior audit.
Started eight exact HTTPS ranges for Microsoft's self-contained supported
26100 EWDK ISO, with Hidden curl processes. At
2026-10-09T21:20:48.4237718Z: **11,459,821,568 / 20,002,537,472 bytes, 57.29%,
eight live processes**; all ranges return 206 with the HEAD ETag. This is a
download in progress, not a launched driver build. Do not restart it merely
because a tool observation has ended. Observer matches PID, process name and
UTC start time; refresh it before assembly.
[EWDK](https://learn.microsoft.com/en-us/windows-hardware/drivers/download-the-wdk),
[Supported other kits](https://learn.microsoft.com/en-us/windows-hardware/drivers/other-wdk-downloads).

assemble-ewdk.py requires fresh terminal-success observations, exact ranges,
sizes and common ETag before creating an ISO. It computes reproducibility
hashes; an opaque ETag is not called an official SHA256. No full ISO, source
ZIP, binaries or private signing keys belong in Git. After completion inspect
the kit's launch scripts, build only this Release|x64 project with signing
disabled, validate INF/catalog, and record actual results. Do not run the
vendor's all-project installer or submit anything to a signing service.

Read-only host checks: installed qcusbser 2.1.3.5 is bound by oem102.inf and
has a valid Microsoft Hardware Compatibility Publisher signature. Secure
Boot registry reports 1; VBS is running with SecurityServicesRunning=[2]
(memory integrity). A newly compiled unsigned driver cannot simply replace
it. A supported signing/test-loading route remains unresolved; **no BCD,
Secure Boot, HVCI, trust-store or driver-store changes were made**.
[Test-signed loading requirements](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/the-testsigning-boot-configuration-option).

Read three local qcser package directories, selected exactly one by matching
both the installed INF and SYS hashes, and copied its four files byte-for-byte
to external rollback-qcusbser-2.1.3.5. This creates a rollback artifact only;
it is not an export/install/removal of a driver. Rollback bytes and source
paths are in rollback-package.json; binaries stay external.

## Workflow corrections and preserved device state

The first download observer parsed an auto-converted JSON date through a
locale string, losing its UTC kind; it reported eight processes absent while
they were live. An independent PID/start-time/growth read identified the
observer error. DateTimeOffset conversion and explicit total accumulation
were corrected; no download was restarted. Preserve the early snapshot as
an erroneous observation, not a terminal-download result.

One inline WSL amendment expanded $KMDFVERSION$ to a malformed intermediate
draft. Direct file edits restored the literal token, and authored-input
validation now asserts it. No build or device action consumed that draft.
These are local tooling corrections, not additional phone failures.

Independent baseline at 2026-10-09T21:12:27.9077015Z: three nodes OK, no known
owner, Shared/not Attached, temporary logging values absent, no EUD trace.
Installed driver/terminal/RX53 logdump hashes match RX60. No flash, reboot,
kernel change, driver install, registry mutation or new capture. TOP_CFG=0x11,
whole-frame payload, RX53 console/IRQ, F1, compatible/native terminal and
RX48 rollback remain. Finally-close requirements still apply to the next
actual owner; this session opened none.

## Next bounded causal comparison

Finish the existing kit download, full build, INF/catalog checks and a
reviewable package first. Resolve a supported loading environment before
installation. Use the **same built candidate binary**, new flag disabled
versus enabled, and observe the reset calls in each case; this avoids
confounding the reset change with switching driver implementations.

Predefine odd and even successful-IN close boundaries and ordinary reopen,
short OUT only, fresh startup receipt before once-only data. Compare exact
first status/frame bytes with the CRC journal, driver counter/raw and USB
trace. Stop at the bound and finally Close/Dispose/Detach. After the specific
fault boundary is addressed, check executed BusyBox output, compatibility and
F1; evaluate full-packet/ZLP separately. Do not repeat RX60's passing contrast,
random echo/reset loops, fuse/PHY/clock experiments or startup padding as a
replacement for the original native stability goal.

Frozen authored inputs and evidence: reference/rx61. Record and push only
fork/master. Previous published tip 6f8ec50. Goal remains active.
