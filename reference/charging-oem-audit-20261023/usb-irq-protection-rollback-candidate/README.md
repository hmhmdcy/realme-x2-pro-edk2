# Exact three-file R8 rollback worker

This is an **offline device-worker and saved-proof component**, not a connected rollback dispatcher. No actual request, guard, lease, current identity or endpoint was generated; no device, SSH, USB, PM, SDK, module build, Image or Git operation was performed. The original design and its source/archive inspection remain in `DESIGN.md`/`design-evidence.json`. The following final implementation narrows/supersedes the design where stated.

Default entry points are inert and read software sources only:

```powershell
python -B reference/charging-oem-audit-20261023/usb-irq-protection-rollback-candidate/restore-worker.py
python -B reference/charging-oem-audit-20261023/usb-irq-protection-rollback-candidate/saved-proof.py
```

The exact old archive remains private at `E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-cohort-private-01/rollback-r8-payload.tar.gz`, 44194B, SHA `5ecae1f5799a1c01d132553b1ad4fb5923d643d1e13fcde8007f5380253fa339`. The worker reparses it and admits exactly original USB7d4…, protection75b… and manifest320… with their original metadata. Its only rootfs replacement order is **USB ko → protection ko → manifest**. Manager614, charger10ec, limits, startup500 and all other installed files remain required retained inputs.

`restore(request, device, execute=False)` is the transaction API. Actual root execution requires `--execute-rollback` and bounded JSON on stdin; the source-only contract lists the fields. The actual `Device` acquires the original charging flock, rechecks current identity/lease, original source stage14 evidence and three backups, original real worker/supervisor terminals, fresh source adoption raw, exact current new disk, full boot/logdump hashes and actual live notes. It never calls `loaded_matches` against a mismatched disk file. The ten old helpers listed in `source-reuse.json`, including the atomic writer, stage terminal chain and original stage-state audit, are copied from frozen actual source without changes. No old suite is executed by extraction or import.

Three explicit profiles are implemented and tested:

| Profile | Current complete boot hash | Relation to stage UUID | Actual live modules |
| --- | --- | --- | --- |
| `staged_same_boot_old_resident` | original97811 | same UUID | exact old three notes |
| `booted_irq_new_resident` | IRQedd | different new UUID | new USB/protection, retained charger |
| `booted_original_new_resident` | explicitly restored original97811 | different new UUID | new USB/protection, retained charger |

Every profile requires exact #502, release, SoC/compatible/rootfs and retained ace2 logdump. #501/#503, mixed profile/notes/carrier and unexpected or partial current disk are refused. New-boot rollback does **not** depend on passing the new whole-postboot audit: IRQ registration or unrelated service/UI acceptance may have failed. Current direct identity, provenance, protection and safe stopping still have to be independently established.

`saved-proof.py::review_profile_sources(profile, stage_directory, stage_fetch_directory, context_path=None)` is pure read/hash authentication. It calls the frozen original `review_stage`. Candidate profile calls frozen `review_completed_activation`; original-boot profile instead calls frozen actual `review_action` for `rollback-original`/`reboot-original`, checks their original child terminal0/write-before-reboot proof and refuses any later opposing candidate action. It never dispatches an operator action. The returned original source identity/projection and selected action binding can be used by root's future request wiring; it never manufactures the current new identity.

The worker checks the saved activation **binding** and actual physical current carrier/profile. Device digest fields alone are not claimed to authenticate host commands. The host must first use the pure saved-proof reviewer and bind a fresh original-key current-identity capture. That current request materialization and connected supervision are **not implemented or run here**. Reuse the existing stage host owner pattern later: one actual detached owner, fsynced regular request fd as worker stdin, PID/start ticks/exact argv and stdin SHA bound before sending, same Popen finally-wait terminal receipt, unknown fetch-only, no timeout kill/relaunch. This leaf adds no dispatcher or new approval policy.

`safe_electrical` requires complete bounded fresh pack/cell/temperature, synchronous independent normal protection, actual managed charger and the original full nondestructive register set. Both hardware input registers/limits must agree and remain ≤900mA, CC≤250mA and inherited pack CV≤8.725V. `safe_stopped` additionally requires charge_behaviour INHIBIT and REG08&0x18==8. If these already hold, there is no repeated stop write. Otherwise the fixed manager614 `command(meta,'stop')` is called once under the flock, followed by actual readback. No CLI/rc-service recursion, module lifecycle, AUTO, current/CV write, FET, raw I2C write, REG14 read, observer capture or carrier write is present.

**Source budget is evidence only while restoring inert disk files.** Zero, ENODATA and unavailable source properties are retained without filling100/500 and do not themselves block an otherwise complete safe stopped state. Existing known latch/timeout/error history is saved and is not cleared or used to enable charging. The inherited physical limits are still checked. A real limitation remains: R8 `sm_collect` returns before gauge sampling when source budget is missing; if actual telemetry is therefore valid0/age−1/zero cells, this tool has no fresh cell/temperature proof and refuses replacement for that reason. It never invents values or creates a second gauge/I2C owner. Missing/broken charger/protection, unknown sample, inconsistent limits, unsafe temperature or unproved INHIBIT also give zero replacement.

Before each replacement the worker rechecks current identity/lease/profile, fresh safe stopped state, unchanged inherited configuration and retained latch/timeout. The old atomic helper writes an exclusive temporary, completes writes, fsyncs file, replaces, fsyncs directory and reads back; failed temporaries and every actual old/new/unexpected final hash are kept. The lease is an entry/check-before-step bound, not an interruptible filesystem or bus deadline. A mid-step failure, receipt failure or close error prevents transaction success; no partial rollback/replay or background recovery is attempted. Identity/carriers are fully re-read after the three files; module notes remain whatever the explicit profile proved.

Success is only `staged_original/runtime_pending`. It never asserts old R8 runtime acceptance or that new resident modules were replaced. An independent matching normal restart and fresh verification are still needed before old-runtime acceptance. No such restart is included here.

Validation is 21 new actual worker/profile/safe-stopped/atomic/manager-stop cases and six pure-wrapper cases. OS, real hardware, current source authentication and already-tested stage/completion authentication are explicit fake boundaries where stated. The unchanged old fake filesystem class is reused without executing its old test module. The 18/13/31/26/149 or other prior suites are not rerun. Default worker and saved-reviewer subprocesses are separately joined at actual terminal0. This is software evidence only.
