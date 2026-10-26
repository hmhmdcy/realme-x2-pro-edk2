# RX64 — supported driver-loading environment remains blocked

2026-10-10 Asia/Shanghai. Previous goal turn RX63 was **PROGRESS**: actual
native compatibility/current policy observations, guarded trial tools and
independently verified publication of 32ae015. This turn is **NO PROGRESS**
toward the actual repair: it revalidates the same environment blocker.
It is not a verified wait. All known build/download/sign jobs are terminal;
no current live test/process handle is available to wait on.

## Fresh authoritative state

At 2026-10-09T22:49:56.7246310Z, the native CI query still returns F401:
TESTSIGN off, HVCI kernel enforcement on; Secure Boot is 1. This exact public
test certificate has zero matches in machine Root and TrustedPublisher.
Three EUD nodes are OK; COM14 still binds the exact oem102.inf/qcusbser2.1.3.5.
Original driver, terminal and RX53 logdump hashes are unchanged; exact RX62
candidate and RX61 rollback package hashes pass. USBIP target is Shared,
not Attached; no known owner, temporary logger, active EUD trace or mounted
kit. Current inspector ended with exit0; stage/install calls remain zero.

The inspector only reads host state and compiles the existing native helper
for the CI query. No compatible-list re-enumeration, serial open, phone USB
data, package staging/binding, registry/trust/security/BCD change, UAC, flash
or phone/PC reboot. Raw snapshot bytes are preserved. The helper is consumed
historical evidence and requires the external RX63 helper; do not rerun with
the same output path. No private keys or driver binaries are published.

Microsoft's current documentation confirms test-signing needs administrator
boot configuration and a PC restart; Secure Boot can block that setting.
HVCI requires a signed binary. A file-only test signature is insufficient
under the current observed policy.
[Microsoft test-signing requirements](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/the-testsigning-boot-configuration-option).

## Blocked audit and complete original scope

The same supported-loading-environment condition appears in RX62's concrete
loading proposal/pending question, RX63's actual CI audit, and this fresh RX64
observation: three consecutive goal turns. RX62/63 completed useful offline
work; it is now exhausted. There is no remaining meaningful safe action that
can load/validate this candidate without the selected environment or an
external state change. An automatic continuation is not a loading-environment
answer. Do not resend the pending question or repeat old passing hardware
captures while leaving the goal running indefinitely.

| Original requirement | Current evidence / completion audit |
|---|---|
| Preserve TOP_CFG0x11, whole-frame payload, RX53 console/IRQ, F1 and both terminals | Existing verified fixes retained; current files/images unchanged, no new phone operation |
| Build candidate and prepare exact rollback | RX62 actual nine-module build, INF/catalog/file-signature checks; RX63 exact metadata recognition/gates; fresh package hashes agree |
| Load candidate and validate actual rollback | Neither native stage/bind nor kernel load has run; prepared tools and gate tests are insufficient |
| Reopen first-frame causal repair | Prior RX59/60 odd/even evidence supports a candidate; same-binary reset-flag off/on intervention is unexecuted |
| Startup and once-only LEN1/3..14 BusyBox execution/output | Existing successes do not prove corrected startup/no-loss behavior under the candidate; full acceptance remains open |
| Full wire16/ZLP | DeviceAdd loading phase identified; actual reread/zero-byte OUT contrast and full LEN14 acceptance remain unexecuted |
| Long console, IRQ/F1, compatible terminal after intervention | Existing RX53/54 validation retained; candidate regression matrix still unexecuted |
| Manual steps, one owner, finally closure, only boot/logdump flashing if needed | No owner/data/flash this turn; unchanged bounds remain required for the future trial |
| Record and publish fork/master only | RX63 independently verified 32ae015; this blocked audit is scoped for fork/master publication |

The full goal is **not complete**. Mark it **blocked** after publishing this
audit, because the same actual blocker persists at an impasse. Resume when
the supported physical Windows environment is selected or made available;
continue RX62's full validation-plan.md via RX63's guarded single-device path.
Keep the original target, reserved LEN2 header-only F1 and once-only native
data semantics. A VM relay, retained handle, padding or short passing variant
does not substitute for the original native terminal stability requirement.
