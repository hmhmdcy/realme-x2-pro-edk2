# USB IRQ + protection observer: offline rootfs cohort

This leaf prepares one future charging cohort. It is not an installer, stage worker, activation guard or deployment receipt. The private forward archive contains exactly **two replacement modules and the manifest**; its rollback archive contains exactly their original R8 bytes. No analyzer, evidence query, service, startup script, desktop change or firmware image is inside either archive.

The sole offline materialization completed with rc0 and the subsequent read-only re-audit passed. Private output is `E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-cohort-private-01/`. The forward payload is `usb-irq-protection-payload.tar.gz`, 51736B, SHA `9dee06ddea1190ea70a188efe47742afb8b104bf53ac31cb57598f079ee4fb3c`; the exact new manifest SHA is `5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417`. The rollback archive is 44194B, SHA `5ecae1f5799a1c01d132553b1ad4fb5923d643d1e13fcde8007f5380253fa339`.

The real protection module is `7848cfab…a3044`, 88856B, linked against the exact Image502 inputs with 31 strong builtin imports, intree Y, matching release/vermagic and terminal zero child commands. Its frozen module delivery is `de4b680c…35b40`; the new resident build-id note SHA is `fc0d253d…733ec`. The payload uses these actual bytes, not the earlier object-only result or a placeholder. All ko files and archives remain private; public files contain only manifest/identity/check receipts.

## Exact changes

The manifest base is the actual R8 `320316c3…c10a1f`. Only `samurai-usb-input` and `samurai-gauge-protection` SHA256 values, the corresponding two `installed_files` values and `adapter_revision=usb-irq-protection-observer-01` change. Both modules retain their original target paths under `/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/`. The manifest remains `/usr/share/samurai-charging/manifest.json`.

Every archive member is an exact regular file with uid/gid 0, root names, mode 0600 and mtime 0. The archive validator rejects extra members, duplicate paths, symlinks, other metadata and different bytes. The independently named offline cohort JSON stays outside the rootfs payload.

The retained inputs are the R8 charger `10ec06fb…6297f`, manager `61451ffe…55aa4`, OpenRC script `bfed48eb…e570a`, the original control/live dependencies, and actual USB500 startup script `2a364e12…9a54a`. Their bytes are verified from cached sources; the payload cannot replace them. Camera, Bluetooth, rootfs recipes, limits and protection policy are outside the payload. Requested input remains 900mA and CC 250mA. The startup descriptor still requests 500mA; native allowance remains the actually observed host-authorized value, not a value forced by this cohort. Source classification continues to constrain the actual budget, so CDP may legally permit a different hardware input limit under the existing 900mA cap.

The existing manager continues to load each exact module path with `register_board=1`. The actual `61451ffe…55aa4` manager does not read or compare `adapter_revision`: its `verify()` checks release and `installed_files`, and `load_module()` uses the manifest module path and exact resident build-id note. The independent revision therefore needs no manager compatibility change. The IRQ provider's already-reviewed DT detection suppresses its legacy software-board duplicate when the new enabled native DT node exists. No manager or OpenRC change is required. The protection observer adds no default new query: normal Health/protection reads retain their old commands. This package never writes `capture`.

## Required kernel and boot pairing

The new USB module `7cbf10c0…4ff5f` is inseparable from native DTB `13d359c4…dee9f`, contained by the already-built IRQ boot `eddadec3…f6e06`. The required kernel is Image502 `085d0306…25955` in the existing logdump carrier `ace2e261…63ed1`. Original BDS parameters, the instant-current flag and every other boot payload remain as proved by the frozen boot receipt. This leaf streams hashes of existing carriers; it does not construct or modify them.

`input-pins.json` binds the frozen USB/DT, boot, Image502/logdump and protection linking receipts and the physical cached bytes. `cohort.json` records old/new module hashes and exact resident build-id notes, plus the unchanged charger's identity. Imported-symbol checks are reused from the actual individual module link receipts against Image502; this is not live ABI or hardware acceptance.

## Stage, boot and rollback boundary

A future authorized stage must use its own transaction, fresh boot/SoC identity and explicit device window. It must acquire the original service flock, validate the exact old R8 disk files and all three current resident notes, synchronously request the manager's normal INHIBIT and verify REG08, back up the old three files, then replace only the two module files and manifest with exact bytes and fsync. This leaf supplies bytes and identities only; no stage code is executed or delivered here.

Before reboot, the new manifest verifies **disk** files while both old modules remain resident. The old USB provider is still owned by DWC3 and must not be force-unloaded. The result can only be `staged/runtime_pending`; calling the old `loaded_matches(new_file, old_resident)` is invalid. A separate new guard must bind staged disk identities, the original resident identities, the stage terminal receipt and the exact boot/DT/Image502 cohort. The already-prepared Image502 notification transaction and its guard cannot be reused or altered.

Rollback bytes are physically retained in `rollback-r8-payload.tar.gz`: original USB `7d4e0f94…c4f70`, original protection `75b97e0d…783c7` and the exact R8 manifest. Original boot `97811cc4…7f695` is the matching native-DT rollback. Image502/logdump is a required baseline for this future cohort, not a claim that it has already been adopted. If the separate Image502 transaction has been adopted, an IRQ-cohort rollback normally retains that transaction's exact current logdump; it must not blindly downgrade to the older Image501 carrier. The future transaction must save its actual preflight carrier/guard facts and current rollback evidence before any write. Partial/unknown writes require same-child/evidence reconciliation, not automatic retry or blind rollback.

## Offline entry points

All commands run on the host and contain no SSH, USB, SDK, service or module action:

```powershell
python -B 'reference/charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/cohort.py'
python -B 'reference/charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/cohort.py' build --execute
python -B 'reference/charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/cohort.py' audit
```

Default `check-local` verifies only existing inputs and computes the exact new manifest; it writes nothing. Explicit `build --execute` creates only the fixed new private directory `E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-cohort-private-01`. Existing output is rejected before writing. Every completed artifact is reparsed; partial failure stays in that output and is not replayed. `audit` rechecks physical artifacts without modifying them. The seven small local tests execute the actual packaging/delta/identity functions; the proved IRQ/observer function suites are not repeated.

Actual acceptance remains future work: same new DT/provider probe, both named IRQs genuinely registered, physical detach/attach changing their counts/event times while budgets and protection remain correct, and new protection resident identity/ordinary Health checks. Optional-IRQ legacy polling can load successfully, so a successful module load, DT presence or Online change alone is not IRQ or icon-latency acceptance. After the new adopted identity matches, root explicitly starts the already-authorized single evidence capture; it is never a default poll and needs no repeated query authorization. Protocol completion is not new 2719 bit compatibility or TCA/Full classification. This cohort grants no APSD, PD, route, PHY or role permission.
