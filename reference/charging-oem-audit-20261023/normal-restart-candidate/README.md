# R7 restart review: current boot, disk R7, live R6

Pure offline audit and **unrun review candidates**. No handset/SSH/EUD/SDK access,
shared source edit, Image change, module unloading, reboot or deployment occurred.
Root owns the R7 two-file update transaction and the device window. The current
taint0 / k449 adopted boot and resident R6 providers are the supplied premises;
this audit has not independently remeasured them.

## Decision

Use the already validated quiet-hardware → EUD retirement →
`RESTART2("bootloader")` → fresh exact fastboot identity → **one fastboot reboot**
sequence for this one module activation. Keep the current Image, boot/logdump
contents and USB100 descriptor policy. A plain Linux `RESTART` is fewer steps,
but no successful plain-RESTART receipt was found in the inspected originals.
Do not introduce that unverified reboot-path change together with FLOAT decoding.

The old `recovery-restart.py` first-line description “normal Linux restart” is
not its actual syscall: lines 27–29 pass `0xa1b2c3d4`, `"bootloader"` to AArch64
syscall142. `kernel367/restart-bootloader.py:27–29` is the same. Earlier72–75
“same-image reboot” receipts also lead to F1/fastboot reboot; e.g.
`kernel73/reboot-fastboot.ps1:24–25`, not ordinary Linux RESTART. The normal
baseline in `kernel367/README.md:5–9` meant no partition flash and no A5 release.
`kernel367/restart-validation.json` records exact fastboot identity, one reboot,
no partition write, and retained kernel/firmware/logdump. The later charging
`recovery-result.json` confirms a fresh taint0 boot with formal440/loaded434
camera baseline and four UID10000 services.

## Why EUD was retired; what is and is not proven

Actual source354 `drivers/tty/serial/eud.c:619–620` explicitly describes the
bootloader handoff: disable EUD to give the USB PHY back to gadget/ABL, otherwise
the host does not see fastboot. `eud_reboot_cmd:651–693` stops RX, drains printk,
unregisters console, serializes the last TTY writer, restores AHB2PHY, disables
CSR_EUD_EN with readback, then calls `kernel_restart("bootloader")`. The copied
userspace sequence unbinds the console driver (whose remove restores AHB2PHY)
and disables CSR before the RESTART2 syscall. This is a bootloader-transition
operation, not a proven normal DWC data bypass.

The actual `qcom_eud_com` platform driver at eud.c1409–1418 has `.probe` and
`.remove` but no `.shutdown`. Actual platform.c1527–1538 calls `drv->shutdown`
only when supplied. `device_shutdown` at core.c4875–4942 does not call `.remove`.
Actual reboot.c767–769 uses `kernel_restart(NULL)` for plain RESTART, whereas
788–797 uses the supplied string for RESTART2; both reach restart preparation
(reboot.c101–107 calls `device_shutdown()`).
Thus a plain reboot does **not** automatically perform the EUD-specific remove
and CSR-disable sequence. This does not establish that plain reboot must fail;
the present evidence simply does not validate it as an equivalent safe shortcut.
Source hashes and numbered excerpts are in `source-excerpts.json` and the four
`*.excerpt.txt` files, copied from the existing source354 via mounted_build().

Full DSP/DRM quiesce is not a generic Linux ABI requirement. It is this project's
repeatedly validated baseline, with independent offline/running, PCM/amp,
camera-provider, framebuffer and DRM-idle proofs. The historical #69 F1 shutdown
block was associated with an already fixed display cleanup failure
(`kernel75/update-docs.py:67–68`); it is not proof today's kernel requires every
manual step. Equally, no current healthy-board shortened quiesce trial proves
those steps dispensable. For this R7 fix, retain the existing sequence rather
than testing that second variable. Keep camera providers bound and require
closed video/media descriptors and regulators off/users0; do not unbind cameras.

## Minimum corrections to the old charging recovery scripts

1. Start from the **taint0** `usb-quiesce.py` / `usb-restart.py`, not the earlier
   taint512 recovery variant. Never accept512, rewrite taint or reuse its proof.
   Replace original-private boot identity, fixed output directory and fixed
   `/run` phase with a fresh current-boot guard and a unique R7 transaction ID.
   Match exact uname release **and version**, rootfs identity, the root-owned
   committed module/manifest pair, and the still-loaded **old R6** USB build note.
2. Root must first have exclusive device ownership after Bluetooth completion,
   camera handoff and no live collector/PM/update worker. Preserve the prior
   INHIBIT baseline. Explicitly invoke `/usr/sbin/samurai-charging stop` before
   hardware quiesce even if OpenRC already labels the service stopped. The real
   command at samurai-charging.py54–60,99–104 validates synchronous REG08 INHIBIT
   and deliberately retains USB providers. No forced rmmod/unbind/reprobe of the
   native provider is a legitimate replacement for the next boot.
3. After R7 disk pair commit and before reboot, **do not start/restart charging**:
   the live module is intentionally R6 while the manifest names R7. The service
   `load_module/loaded_matches` path would reject the mismatch. `stop` verifies
   the disk manifest and inhibits; it does not require the new USB note loaded.
4. The restart's inspect phase must not open `/dev/mem` R/W. Candidate inspect
   checks sysfs/identity/quiesce only, explicitly reports CSR not read; CSR is
   checked on the committed path. Place an exclusive one-request claim before
   freeze/unbind. A lost SSH connection is neither accepted syscall proof nor
   permission to retry: EUD disable itself disconnects USB before the syscall.
5. Host completion must use newly observed single expected fastboot serial and
   msmnile product, then one `fastboot reboot`, with an exclusive host request
   receipt. There is no flash/boot/erase command in this plan. The review workers
   do not implement host completion; root can reuse the validated identity-only
   part of run-recovery.py108–119 with **new** markers.

## Review candidates and guard contract

`prepare.py` only reads the two old workers and writes local candidate scripts,
diffs and hashes. It never imports their executable bodies. It has generated
`r7-quiesce-review.py` and `r7-restart-review.py`; neither was run. The behavioral
hardware sequence is retained. Explicit options are required:
`--guard /absolute/fresh-private.json --commit-quiesce`, or restart
`--guard /absolute/fresh-private.json --inspect` /
`--guard /absolute/fresh-private.json --commit-restart2-bootloader`.
These are review interfaces, not an instruction to execute them now.

Root supplies a new root-owned private guard with fields:

| Field | Meaning |
|---|---|
| `schema` | `samurai-r7-restart-review-v1` |
| `transaction_id` | New `charging-r7-` plus8–64 lowercase alphanumeric/hyphen characters; never an old terminal directory |
| `boot_id` | Fresh exact current boot UUID, not original-private's historical boot |
| `kernel_release`, `kernel_version` | Exact current uname release/version; version remains actual #363 |
| `rootfs_release_sha256` | Fresh exact `/etc/samurai-rootfs-release` hash |
| `disk_pair` | Exactly R7 `samurai-usb-input.ko` and manifest absolute paths→SHA256, from root's committed transaction |
| `old_loaded_usb_note_sha256` | Current accepted R6 `/sys/module/samurai_usb_input/notes/.note.gnu.build-id` hash |

The explicit disk pair paths are `/usr/share/samurai-charging/manifest.json` and
`/lib/modules/<kernel_release>/extra/samurai-charging/samurai-usb-input.ko`.
The module's manifest `modules` and `installed_files` hashes must also match.
Root must bind these fields to its own fresh snapshot/update receipt; the guard
is not a substitute for that transaction or for sibling-session ownership.

`test-guard.py` executes the **same emitted guard** against fake files:17 vectors
cover current diskR7/liveR6 acceptance, old boot/schema/transaction, exact version,
taint512, native retention, loaded-note mismatch, disk/manifest mismatch,
extra path, rootfs, owner/mode/symlink, existing phase and architecture. It also
parses both full workers and checks inspect precedes MMIO open, the exclusive
claim precedes FIFREEZE, and the syscall remains RESTART2 bootloader. All pass.
No syscall, freeze, sysfs write or hardware validation is represented by this.

## Rollback and completion boundaries

Before disk commit, root retains both exact old files, hashes/modes and its
transaction. If failure occurs before reboot, leave hardware INHIBIT and restore
the **old ko and old manifest together** before any service start. The live R6
provider has not changed; no module unload is needed. Record partial quiesce
stage and actual states before deciding what to resume. Do not rerun the whole
old worker over an existing terminal directory or clear a failure marker.

After EUD retirement/restart claim, an SSH timeout cannot distinguish syscall
execution from a handoff failure. Do not launch another restart or automatically
rebind EUD. Use fresh host fastboot/USB observation and the single existing
worker's state if access remains. If the syscall returns, candidate only thaws
rootfs; it does not pretend to restore stopped services/EUD. Escalation requires
actual state inspection and root's recovery decision.

After new boot, abandon all old-boot guards and transactions. Root must establish
new boot UUID, original host key, exact new USB **loaded note**, unchanged charger
and protection notes, correct manifest/disk hashes, taint0 and no new relevant
faults before claiming R7 active. Restore/verify camera formal packages and
current modules, fresh PM/m2m idle/resource states and the four user services with
new PIDs, plus Bluetooth/SSC/SensorProxy dependencies. Do not reuse preboot PIDs
or describe process death across reboot as a camera regression. Fresh charging
source/protection/telemetry and the native budget are separate acceptance gates;
UDC configured alone does not establish physical power permission or icon timing.

If the new provider cannot be validated, keep charging INHIBIT. Root can restore
the backed-up old disk pair, then use a **new** controlled reboot transaction to
load old USB again. Do not force unload a DWC-owned provider. Restoring these two
disk files does not itself reverse the already loaded module. This plan changes
no Image, PMIC configuration, source-budget interface, descriptor, EUD topology,
boot/logdump partition or protection policy.
