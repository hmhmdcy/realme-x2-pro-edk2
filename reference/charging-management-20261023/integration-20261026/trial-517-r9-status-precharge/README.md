# Trial charging-integration-r9-status-precharge-20261027

This is the r14 MP2650 hardening and full-boot trial. It was materialized
offline by the pinned `build-r9-final.sh`, FAT/boot packaging, manifest-update,
and `finalize-trial-517-r14.py` pipeline; no phone, SSH, adb, fastboot, device
wrapper, reboot, or charging-hardware operation was performed.

## Pins

- Kernel version: `#528 SMP PREEMPT Tue Oct 27 08:49:26 CST 2026`
- Kernel release: `7.3.0-rc6-rmx1931-samurai-k363+`
- Image: `8a4aea91b809423561ffd7cb9bf6f651dd01c1952815e0fce467ce860d944312` (59374080 bytes)
- New boot: `13c98860646fa80241a0a042e17781fceb7873f13263c69433839fd11ab9f756`
- New logdump/FAT: `b91279466383d04ec17fbdb75d6e08bf2bb4be16d38d383083ee52f8e1dd67b1`
- `samurai-mp2650.ko`: `dbe445cfef6e095f8d028034f0fbba9231484b6510ab6f60354c6ff55e9c23d1`
- `samurai-usb-input.ko`: `22604106772b89758ea745531e99dd70a6ab696b7740705107a767599e9a6529`
- Rollback boot: `13c98860646fa80241a0a042e17781fceb7873f13263c69433839fd11ab9f756`
- Rollback Image: `6e45cbb780b7de690f714a17b54524369b630eccff8ee773acbbb38a59f90f2f`

The manifest requires the built-in `vmlinux` export
`bq27xxx_battery_set_status_override` with owner `vmlinux` and type `EXPORT_SYMBOL_GPL`.

## Scope

The package preserves the current boot identity and updates the FAT Image.
The verified boot carrier is rewritten as part of the atomic boot/logdump pair,
then the guard validates both carriers. It installs both the primary MP2650
module and the matching-release wake USB module, updates all trial userspace
files, and patches only the matching entries in the main charging manifest.

The r14 userspace correction accepts the charger's intentional
`Not charging` status while telemetry proves an explicit Full hold. The physical
wake launcher also uploads the matching `trial_common.py`, avoiding a remote
module-import dependency. Active audit and soak states now require at least one
real `Charging` indicator, reject simultaneous `Not charging` on both supplies,
and include `gauge_charge_stop` in the physical recovery health gate.

Physical wake and cable-cycle control deliberately use the phone's Wi-Fi
address. NCM disappears during a physical disconnect and therefore cannot be
the control and evidence channel for those tests.

Proven active 5 V charging now remains hardware-autonomous through system
suspend, matching the board's disabled OEM `suspend_after_full` property.
Unknown, unsafe, latched, timed-out, Full-hold, or already-disabled targets
still stop before suspend. The resume work immediately takes a fresh sample.

High voltage, PD/PPS/QC takeover, charger-register experiments, and device
hot-unload are outside this package.

## Required gates

1. Run the local test suite from this directory; the frozen gate requires 215 tests.
2. Review `TRIAL-R14-PREPARATION.json` and confirm every SHA-256 is final.
3. Run stage preflight and require the exact kernel version and main-manifest
   old hash recorded in `manifest.json`.
4. Execute stage only after the guard tests and preflight pass.
5. Continue with the fastboot operator; it writes logdump then boot and allows
   one reboot.
6. After boot, require accepted state, both module hashes, the new main
   manifest hash, protection Good, NCM, Type-C, and MP2650 telemetry.

Physical low-battery precharge, physical USB wake, and a full low-to-high
charge cycle remain separate runtime tests. A non-crash audit or attention
state is repaired in place; automatic carrier rollback is disabled.
