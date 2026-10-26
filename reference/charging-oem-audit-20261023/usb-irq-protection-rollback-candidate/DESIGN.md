# Exact R8 rootfs rollback: design before implementation

This leaf is currently **design only**. No current request, guard, lease, endpoint, transaction or device action is produced. The phone remains outside this offline work. The payload already exists: `rollback-r8-payload.tar.gz`, 44194 bytes, SHA256 `5ecae1f5799a1c01d132553b1ad4fb5923d643d1e13fcde8007f5380253fa339`. It contains only the original R8 USB module, protection module and manifest. It never changes Image, boot, logdump, manager, charger, startup, desktop or configuration limits.

## Three explicit current identity profiles

The caller chooses one profile and supplies actual current original-key evidence. The worker never infers the profile from whatever bytes happen to be present. All profiles require exact release `7.3.0-rc6-rmx1931-samurai-k363+`, exact #502 version, SoC/compatible/rootfs matching the authenticated source stage and retained Image502/logdump `ace2e261…63ed1`. #501/#503 are rejected.

| Profile | Current boot | UUID relation to original stage | Required actual live notes |
| --- | --- | --- | --- |
| `staged_same_boot_old_resident` | `97811cc4…7f695` | exactly the original successful stage boot | old USB `f0edb792…04b0`, old protection `930e0e1f…fe76`, unchanged charger `f4d5768a…680d` |
| `booted_irq_new_resident` | IRQ `eddadec3…f6e06` | different new boot | new USB `a845cd08…8c6d`, new protection `fc0d253d…33ec`, same charger |
| `booted_original_new_resident` | explicitly restored `97811cc4…7f695` | different new boot | the same exact new notes; reverting boot alone does not revert disk modules |

The first profile requires the complete original stage request, original worker/supervisor PID/start-ticks/argv, real terminal0, exact saved inputs/results and raw file evidence, using frozen `stage-proof.py::review_stage/guard_stage_fields`. A passed label or absent PID is insufficient. The other profiles retain that source-stage proof and additionally require the actual saved activation or original-boot rollback/reboot action chain, plus a fresh original-key current-identity capture. The existing completion API qualifies the candidate boot only. Its pure `review_action` can audit the already-saved `rollback-original` and `reboot-original` originals, but the original-boot profile still needs a separate explicit completion selector/order check; it must not call candidate-completion and ignore a later original rollback.

Each current profile rereads full boot/logdump length/hash O_RDONLY, uname/UUID before and after, exact rootfs/board metadata, current three resident notes/initstate and retained manager/service/charger/startup files. Every profile starts with the exact *new* three disk files, mode0600; partial/unexpected/corrupt files are reported separately and are not silently treated as this successful-stage rollback. No successful new-boot postboot/adoption is required: the IRQ registration, UPower, camera-service or other acceptance checks may be the reason for rollback. Current identity, known software provenance and safe stopping are independently re-established.

## Recovery permission is narrower than whole-postboot health

The old stage's `safe_sample/healthy/unchanged` cannot be copied unchanged: they require old notes, all healthy fields zero and enabled/precise-Full behaviour. A rollback needs a distinct `safe_stopped` predicate that does **not** erase a prior latched error/timeout or require an irrelevant successful IRQ/UI check.

The worker holds the original `/run/lock/samurai-charging.lock` and uses the exact installed manager614 and its original known read-only live register set (no REG14). It reads current telemetry, limits, independent `protection_state/health`, charge_behaviour, notes and bounded BOOTTIME brackets. Normal protection reads synchronously refresh under the provider's original lock/segment lock, including its error; an old cached-looking word is not enough. This worker does not issue the new three-query capture, use a second I2C owner, or perform any raw I2C write.

Two stop paths:

1. If charge_behaviour already selects `inhibit-charge` and actual REG08 bits0x18 read as0x08, record `stop_action=already_inhibited` and issue no repeat control request. Independently verify that condition again immediately before replacing files and afterwards.
2. Otherwise, after proving the exact managed R8 charger and its existing bounded electrical configuration, invoke the fixed manager's `command(meta, 'stop')` directly under the held original flock. Do not invoke the CLI or rc-service, and do not call `loaded_matches(new_disk, old_live)` in profile1. The actual stop branch only calls its original `inhibit`; it neither loads nor unloads modules. Read back charge_behaviour and REG08, preserving primary/stop errors. Stop failure gives zero rootfs replacement.

The normal manager CLI is unsuitable because its entry calls `verify()` before `command`; direct fixed-code use avoids accidental coupling to a previous manifest or live/disk note comparison. Manual exact current-new-file/retained-file verification is still mandatory. After restoration, the original manifest/files can be reverified without comparing the new resident modules with the old disk ko.

For replacement permission, fresh independent protection must report the established normal id0x2719/error0/safety0/pf0 and the existing sealed/autonomous operation/manufacturing masks. The managed charger must provide a fresh complete sample and actual bounded registers: both input limits within the actual source budget and900mA cap, CC no greater250mA, inherited CV no greater8.725V, safe pack/cell consistency and a supported temperature. No source is guessed and no unknown/ENODATA is replaced with100/500. A *known* existing latched/timeout/charge-stop history is recorded and retained; it is not a reason to enable charging, clear a latch, reload modules, call AUTO or raise limits. `safe_stopped` may admit such history only while independent protection and electrical observations are complete and normal INHIBIT is physically proved. It does not label the charger healthy or fault-cleared.

If current identity/carrier/required retained code is inconsistent, if independent protection fails/is unknown, if sample freshness/electrical limits cannot be proved, or if normal INHIBIT cannot be read back, the worker reports the exact failed gate with zero file replacement. Already-known INHIBIT can be reported separately even when subsequent protection blocks restoration. This tool cannot recover a missing/broken charger or protection provider through blind I2C/FET writes. A physical protection failure is not bypassed by restoring disk bytes. These are real recovery boundaries, not a claim that every unhealthy boot is automatically recoverable.

## One bounded disk transaction

Proposed new request schema `samurai-usb-irq-protection-rollback-request-v1` has a new `usb-irq-protection-rollback-*` transaction, explicit profile, actual current identity, original source-stage projection, profile-specific saved activation proof, exact worker/payload/cohort identities and a short current BOOTTIME lease. Root creates the actual material only later, using the original key and coordinated window. Default worker/host checks read software inputs only.

The worker uses the same exclusive once-directory and original service flock as stage. The detached owner must retain one actual Popen, fsynced request regular-file stdin, child birth/argv and input hash, and finally wait that child. Unknown results are fetch-only; no second launch, timeout kill, reboot or retry. The new source must not import a stage main or trigger a stage.

After identity/protection/INHIBIT gates, back up exact current new bytes and mode plus observed live identities and error history. Reuse stage's actual `atomic_replace` body: exclusive temporary regular file, complete write, file fsync, replace, directory fsync, exact readback. Restore USB old bytes, protection old bytes, then old manifest. Recheck current identity, lease and safe stopped state before each replacement. Do not depend on the manifest for resolving the running providers. A mid-write or receipt/close failure remains an explicit partial/unknown result with old/new/unexpected final hashes, retained temporary files and the original child identity; no automatic rollback of the rollback or replay.

Success is exactly `staged_original/runtime_pending`, old three disk hashes fsynced/readback, actual old/new resident notes recorded unchanged, and INHIBIT retained. It does not assert that old R8 modules are resident, even in profile1; it records the independently observed notes. Profile2/3 must keep their new modules resident until an independent normal restart and fresh verification. There are no hot-unload/insmod/AUTO, carrier writes or process/service restarts here.

## Planned affected tests

Only new actual worker predicates/transaction functions: all three identity profiles, same-UUID/boot/note mismatch refusal, real source-stage terminal requirement, new-boot postboot failure independent of restore gates, known stopped fault history retained, unavailable protection/stop zero replacements, already-inhibited zero control, explicit stop once, per-target lease/fresh/identity failures, only-two-ko-then-manifest order, partial rename/fsync/readback and receipt/close failures. Reuse original atomic helper/test results where byte-identical. No old stage/codec/IRQ/Full or activation matrix rerun, no module build and no device validation.

## Fixed source anchors

- `charging-ui-audit-20261023/usb-irq-protection-stage-candidate/stage-worker.py` SHA47794e53…5c83a: `atomic_replace`, backup/result/error semantics, original flock and exact manager path.
- `charging-session-20261023/r8-source-integration/rootfs-sources/usr/sbin/samurai-charging` SHA61451ffe…55aa4: `inhibit` and `command(...,'stop')`; no module lifecycle in that branch.
- Its `rootfs-sources/usr/lib/samurai-charging/live-session.py` SHA2199d7d4…15f2b: existing nondestructive register reads only; no new direct bus writer.
- `protection-query-observer-candidate/samurai-gauge-protection.c::protection_state_show` calls fresh normal `sm_protection_read`; the one-shot observer is unrelated and remains off.
- Frozen cohort delivery3d5b78bc…2a07b and exact retained archive5ecae1f5…fa339, stage-proof85c9…e093 and boot-only operator/completion deliveryff805108…362a41 remain unchanged.
