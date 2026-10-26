# Session 62 — full EUD WDF build and file-only test-signed package

2026-10-10 Asia/Shanghai. Goal-turn audit: **PROGRESS**. The original native
terminal stability goal remains active. No new phone experiment or serial open.

## Finding and actual repair status

The strongest located candidate concerns **ordinary-reopen first-packet loss**:
the installed driver resets both bulk endpoints at each Open; RX59's forced
75-IN close loses exactly the first six-byte IN frame, whereas RX60's
predefined 74-IN reversal preserves it and matches all 512 journal records.
This supports host/device data-toggle mismatch. Physical DATA0/1 is unmeasured;
neither this comparison nor a passing build proves that every missing RX
receipt/output has the same cause. The full 16-byte OUT/ZLP boundary remains
a separate fault. Do not repeat these old device contrasts unchanged.

The unchanged RX60 patch skips only ordinary FileCreate resets for the new
candidate's 05c6:9505 opt-in DWORD QCEudPreserveToggleOnOpen=1. It preserves
initial preparation, recovery, close, and other devices' paths. This key has
no effect in the installed proprietary qcusbser driver. The existing
14-case mocked dispatch result remains relevant; code did not change here.
The repair is now a **built/test-signed candidate**, not a measured fix.
[Microsoft reset/toggle semantics](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usb/ns-usb-_urb_header).

## Completed build environment and real full build

All eight existing HTTPS download ranges finished with curl exit 0, exact
sizes, 206 responses and the common HEAD ETag. The ISO was assembled from
those terminal observations, without restarting downloads. Total bytes
20,002,537,472; SHA256
9f48251dd24ad31aac206d8256e95bda5f90a9783982c45a8aafeb9054562379.
This is a computed artifact hash, not a located official published hash.

Mounted the ISO read-only, inspected its launch scripts, and called
BuildEnv/SetupBuildEnv.cmd amd64 directly in a bounded child cmd /d /c.
LaunchBuildEnv.cmd uses cmd /k and was not launched. No kit installation or
global environment change. All mounts were dismounted in finally.
Compiler/amd64 MSBuild/InfVerif/SignTool signatures verify. Inf2Cat's internal
Microsoft signing root is untrusted on this host; that status was retained,
not reported as Valid, and no root was installed.

Actual Release|x64 MSBuild builds all nine C modules, links qcwdfserial.sys,
stamps INF, runs package validation and generates a catalog. Final attempt
03 returned exit 0 with **zero warnings and zero errors**. Signing and
deployment were disabled during this build. Compiler 19.44.35209, EWDK
26100.6584, amd64 MSBuild 17.14.10.27608. Full raw commands/logs are frozen.
[WDK build guidance](https://learn.microsoft.com/en-us/windows-hardware/drivers/develop/building-a-driver).

Two earlier local build failures were corrected before success:

1. Default 32-bit MSBuild could not load the kit's x86 InfVerif DLL. Vendor
   UTF8 comments also raised C4819 under the host's code page 936 and /WX.
   Switched to amd64 MSBuild and added /utf-8 to the candidate project.
2. Real InfVerif rejected DIRID 13 without a sufficiently decorated minimum
   Windows version. The EUD-only INF now specifies NTamd64.10.0...26100.
   Checks were retained; no warning/error suppression or disabled validation.

Only these project/INF metadata changes differ from RX61's frozen authored
inputs. QCPNP SHA256 stays
7cf3f3db7878d4a1a037da075e4dfda6985851b7805a42434cf3ae2202c014fd;
the other eight C modules still match the pinned official archive exactly.
These were offline tool failures, not additional failures on the phone.

## INF, catalog, binary and file-only signatures

The package matches only USB\VID_05C6&PID_9505 and uses separate service
qceudexp. Standalone InfVerif /w /v reports **INF is VALID**. A separate /info
reports the expected model/service, AMD64/minimum 26100. KMDF stamps 1.15;
DriverVer stamps 10/10/2026,5.47.2.26. Those are actual stamped values,
not the earlier authored placeholder version.
[InfVerif](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/running-infverif-from-the-command-line).

Inf2Cat explicitly generates a catalog for 10_GE_X64,10_25H2_X64 with
Errors None / Warnings None. An initial invocation combined an argument
array incorrectly and returned Parameter format error; its failed log is
preserved. The corrected direct invocation succeeded. The original build
package and the generic-target unsigned package remain intact.
[Inf2Cat options](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/inf2cat).

The produced driver is AMD64 PE32+ / Native, NX-compatible, aligned to 4096,
with no writable/executable section; the new key appears in the linked image.
This static inspection does not prove HVCI runtime compatibility or stability.

Created an ephemeral RSA3072 self-certificate in memory for **file-only test
signing**, with code-signing EKU. The encrypted one-use PFX was restricted to
the owner/Admin/SYSTEM directory and removed in finally. No certificate was
imported, no signing service/timestamp request was made. SYS was embedded
signed with SHA256/page hashes, a new Windows 11 catalog generated afterward,
then CAT signed. The public certificate expires 2026-10-23T22:03:18Z.
[SignTool](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/signtool).

SYS/CAT CMS signatures verify cryptographically against the exact public
certificate. A separate parser recomputes the PE image SHA256 and matches
the digest within its verified CMS content. Comparing unsigned/signed SYS
confirms all original bytes outside the checksum/security-directory fields
are unchanged; only the certificate was appended. All six checked user/machine
My/Root/TrustedPublisher stores have zero matches for the test certificate.
These checks do not grant retail kernel-loading trust.
[PE signature hash boundaries](https://learn.microsoft.com/en-us/windows/win32/secbp/understanding-pe-signatures).

| Local artifact | SHA256 |
|---|---|
| Unsigned qcwdfserial.sys | 3cceeafcb3c5656e87de130d938f748cdc3875e826c63f9826440b56674b4a2a |
| Test-signed qcwdfserial.sys | 245e88c2c5818440e04345490159869243a542e997ffa1997aba5460309c777c |
| Stamped qceudexp.inf | f0217c8ec587fccc0f24e701a3a1cf405f2e25961cd11e56a19682ec923b1495 |
| Test-signed qceudexp.cat | 9df033f24f3effac2fc29bb5a440d1c54b29c6472ade1165fa6121518d63354f |

Candidate folder: E:\edk2-samurai-out\rx62\package-test-signed.
Unsigned folder: E:\edk2-samurai-out\rx62\package-windows11.
Exact old-driver rollback: E:\edk2-samurai-out\rx61\rollback-qcusbser-2.1.3.5.
Retained Qualcomm BSD notices in both candidate packages. Full source ZIP,
ISO/shards, SYS/PDB/catalog/certificate binaries and private material stay
outside Git. Proprietary Microsoft kit script bodies also stay external;
only their hashes and inspection summary are frozen.

## Current state and remaining loading decision

Fresh state after file-only signing is in post-signing-state.json. Three
EUD nodes are OK, COM14 has no known owner, USBIP 6-5 is Shared/not Attached,
logging values absent, no active EUD ETW, kit ISO unmounted. Original installed
oem102.inf/2.1.3.5 retains its valid Microsoft signature and exact SYS hash.
Native/compatible terminal and RX53 logdump hashes are unchanged.

The current Windows host is build 26300, Secure Boot registry 1, VBS running,
SecurityServicesRunning=[2] (memory integrity). The test-signed candidate
has **not been installed or loaded**. No registry/driver-store/trust/BCD/
security change, phone flash/reboot or serial/USB data action occurred.
TOP_CFG=0x11/whole-frame RX, RX53 console/IRQ, F1, terminals and RX48 rollback
remain preserved. Finally-close still applies to later owners; none opened here.

An unsigned/self-signed candidate cannot simply replace the current driver
under this host's policy. A separate physical Windows test host or explicitly
agreed local test-signing/firmware/reboot route is needed; a Microsoft signing
route has different account/provisioning requirements. This is a new driver/
host security scope beyond the prior no-install/no-reboot log-capture plans.
The user was asked to choose the environment after the concrete package and
loading-review.md were prepared. No elapsed time is treated as approval.
[Test-signing requirements](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/the-testsigning-boot-configuration-option),
[Microsoft signing choices](https://learn.microsoft.com/en-us/windows-hardware/drivers/dashboard/driver-signing-offerings).

Next: load only in the selected supported environment, verify the actual
9505 binding/hash/option path, and compare **the same built binary's option
off/on** while observing the actual FileCreate reset behavior. Predetermine
odd/even short-IN close boundaries; exact first wire/status bytes must match
CRC journal, receive counter/raw and USB trace. Retain manual bounded steps,
one owner, fresh startup receipt before once-only commands and finally close.
Then verify BusyBox output, console overlap, F1/compatibility and the separate
LEN14/16-byte OUT/ZLP boundary against validation-plan.md. Do not count a
build, broker/padding workaround or narrow passing sample as the original goal.

Frozen evidence/reference/rx62 verifier distinguishes offline package checks
from hardware proof. Previous fork/master tip ac16146; publish fork/master
only. Original stability goal remains open.
