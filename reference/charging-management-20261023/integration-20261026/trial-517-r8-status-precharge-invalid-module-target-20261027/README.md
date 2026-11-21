# Trial charging-integration-r8-status-precharge-20261027

This is the r8 status/Full and precharge full-boot trial. It was materialized
offline by `prepare-trial-517-r8.py`; no phone, SSH, adb, fastboot, device
wrapper, reboot, or charging-hardware operation was performed.

## Pins

- Kernel version: `#518 SMP PREEMPT Tue Oct 27 04:21:36 CST 2026`
- Kernel release: `7.3.0-rc6-rmx1931-samurai-k363`
- Image: `3b6ac0f7f2ebf0ce027a8cf63ea65e5b44960a3943edd61504c807b171770f6b` (59374080 bytes)
- New boot: `13c98860646fa80241a0a042e17781fceb7873f13263c69433839fd11ab9f756`
- New logdump/FAT: `432ce058e0e220dbcee90db8468cd24c91f79e83e3136c42c9349abed3802721`
- `samurai-mp2650.ko`: `7b5b76deeacadd961a6790a8a0aa857e47b002425bb450fa319e4b6294c11bb0`
- `samurai-usb-input.ko`: `37d74184e3e6f71dfc0abccd77f63dba0715550e54fd492df4ac0db59237947f`
- Rollback boot: `13c98860646fa80241a0a042e17781fceb7873f13263c69433839fd11ab9f756`
- Rollback Image: `6e45cbb780b7de690f714a17b54524369b630eccff8ee773acbbb38a59f90f2f`

The manifest requires the built-in `vmlinux` export
`bq27xxx_battery_set_status_override` with owner `vmlinux` and type `EXPORT_SYMBOL_GPL`.

## Scope

The package replaces the current boot and logdump while preserving the current
#517 boot/Image as the rollback baseline. It installs both the primary MP2650
module and the existing wake USB module, updates all trial userspace files, and
patches only the matching entries in the main charging manifest.

High voltage, PD/PPS/QC takeover, charger-register experiments, and device
hot-unload are outside this package.

## Required gates

1. Run the local test suite from this directory.
2. Review `TRIAL-R8-PREPARATION.json` and confirm every SHA-256 is final.
3. Run stage preflight and require the exact kernel version and main-manifest
   old hash recorded in `manifest.json`.
4. Execute stage only after the guard tests and preflight pass.
5. Continue with the fastboot operator; it writes logdump then boot and allows
   one reboot.
6. After boot, require accepted state, both module hashes, the new main
   manifest hash, protection Good, NCM, Type-C, and MP2650 telemetry.

Physical low-battery precharge and Full/recharge behavior are not proven by
this package and must be validated on the new boot.
