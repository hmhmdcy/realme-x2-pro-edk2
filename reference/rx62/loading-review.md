# RX62 — concrete driver loading decision

Prepared 2026-10-10 Asia/Shanghai. No installation, certificate import,
BCD/security change, flashing or reboot has occurred. This document is a
reviewable next-step proposal, not an executable authorization.

## Candidate and exact rollback

Candidate: `E:\edk2-samurai-out\rx62\package-test-signed`.
Only `USB\VID_05C6&PID_9505`, separate service `qceudexp`, AMD64,
minimum Windows build 26100, KMDF 1.15. The current host is build 26300;
runtime compatibility is not proved by the INF/catalog checks.

The actual nine-module driver build passed with zero warnings/errors.
InfVerif /w /v is VALID and Inf2Cat explicitly generated the Windows 11
24H2/25H2 catalog. SYS and CAT are SHA256 test-signed with a file-only,
self-created certificate valid until 2026-10-23T22:03:18Z. They are not
Microsoft release-signed. The public certificate was not imported anywhere.
CMS signatures and the PE image digest verify; all original code bytes match
the unsigned driver. Only PE signing headers and the appended certificate
changed. The temporary encrypted PFX was removed in finally.

Test-signed SYS SHA256:
`245e88c2c5818440e04345490159869243a542e997ffa1997aba5460309c777c`.
INF SHA256:
`f0217c8ec587fccc0f24e701a3a1cf405f2e25961cd11e56a19682ec923b1495`.
CAT SHA256:
`9df033f24f3effac2fc29bb5a440d1c54b29c6472ade1165fa6121518d63354f`.
Full local manifest: `offline-signing.json`. Original unsigned package and
original build outputs remain intact.

Exact original driver rollback:
`E:\edk2-samurai-out\rx61\rollback-qcusbser-2.1.3.5`.
Original installed package is `oem102.inf`, SYS SHA256
`ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151`.
The copy has all four files selected by exact INF/SYS match. Before a later
installation validate its manifest and resolve the target's live PnP software
key; don't assume Ports slot 0008 will remain the same.

## Supported environment choices

1. A separate physical Windows x64 test computer already permitted to run
   test-signed kernel drivers. Copy this exact package and its public cert,
   confirm its actual Windows/USB/security state and record that topology.
   Use physical USB for the reopen causal observation. A VM/USB relay can
   change transfer handling and is not equivalent proof of this host fault.
2. This Windows computer, after explicit agreement on the new scope:
   temporary test-signing boot configuration, PC reboot and, if Secure Boot
   blocks it, a user-operated firmware change. First inspect BitLocker state
   without reading or printing any recovery key and confirm recovery access.
   Document the original settings and a restore procedure before change.
   Retain memory integrity for the initial signed-driver test if compatible;
   a load failure is diagnostic, not approval to turn it off automatically.
3. A Microsoft signing route, if the user has the necessary developer account
   and agrees to submission. Attestation/preproduction signing has its own
   enrollment and target provisioning requirements. No account enrollment,
   certificate purchase or external submission has been made.

File-only self-signing does not make a driver trusted on the current retail
host. Microsoft documents that test-signing requires administrator rights
and a PC restart, can be blocked by Secure Boot, and that HVCI requires a
signed driver binary. The prior administrator log-capture scope explicitly
excluded installing drivers or rebooting; global host security changes are a
new step requiring an environment decision, not another log-capture UAC.

## Later authorized trial, with an explicit bound

Scope the installation/binding to the single present EUD COM 9505 device.
Do not change Control 9501, other ports, USB filters or global USB flags.
No phone flash/reboot is needed for the initial ordinary-reopen comparison.
Preserve RX41 TOP_CFG=0x11/full-frame input and RX53 kernel/console/IRQ,
F1, native/compatible terminals, RX48 firmware rollback and the installed
terminal's once-only command semantics.

After installation verify the exact SYS hash, actual binding, signature
and option location. Compare the **same compiled binary** with
QCEudPreserveToggleOnOpen off/on. Observe whether the ordinary FileCreate
pipe resets actually occur in each mode, then predefined odd/even short-IN
close boundaries and exact first-frame status/journal/raw/counter evidence.
Separate full 16-byte wire OUT/ZLP from this initial causal trial.

One owner at a time; manual small bounded steps. Obtain a fresh startup
receipt before any once-only data, allow only the existing bounded Ctrl-U
startup retry, and always Close/Dispose/Detach in finally. Stop on unexpected
node/security state, a failed driver load or the declared time bound; record
and restore the original driver binding before broad stability claims.
The full original acceptance matrix remains in `validation-plan.md`.

Sources:
- https://learn.microsoft.com/en-us/windows-hardware/drivers/install/the-testsigning-boot-configuration-option
- https://learn.microsoft.com/en-us/windows-hardware/drivers/dashboard/driver-signing-offerings
- https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/signtool

Original goal remains open. A built/test-signed package is concrete progress,
not a verified fix or permission to change Windows boot/security settings.
