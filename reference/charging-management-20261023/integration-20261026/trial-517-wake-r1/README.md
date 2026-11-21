# Charging integration #517 wake-r1

This is a module-only follow-up trial for the already running #517 charging
baseline. It replaces only `samurai-usb-input.ko`, refreshes the charging
userspace guard/audit files, patches the matching manifest pins, and performs a
normal reboot. It does not flash or modify boot, logdump, the kernel Image, DTB,
charger/core driver configuration, protection settings, or charger registers.

## Scope

- Kernel pin: `#517 SMP PREEMPT Tue Oct 27 00:17:40 CST 2026`
- Trial id: `charging-integration-517-wake-r1-20261027`
- Device: serial `62bc28a1`, product `msmnile`
- Fixed SDP/5 V only. PD/PPS/QC high voltage is forbidden.
- Stage mode: `module-only`; restart mode: direct Linux reboot syscall.
- Acceptance window: 300 seconds, bound to the boot id and exact manifest hash.
- Physical USB insertion/removal wake remains **unproven** until a real s2idle
  test records a USB/Type-C/PMIC wake source without an RTC fallback.

## Module change

- Current module: `161bcc3376864e6f867aa5cc0371b5ab61ba9d716108aad0f45e6c765d378f86`
  (26128 bytes)
- New module: `22604106772b89758ea745531e99dd70a6ab696b7740705107a767599e9a6529`
  (91896 bytes)
- The new provider requests the existing `usbin-plugin` and
  `usbin-src-change` IRQs.
- On system suspend it calls `enable_irq_wake()` for those IRQs when the USB
  power-supply wakeup switch permits it. Partial arm failures roll back and
  restart polling.
- On resume it drops only the wake references it owns and restarts polling.
- Polling remains the fallback. The provider still hides the unbind attribute
  and is not hot-unloaded.

## Transaction behavior

`trial_stage.py` supports two modes. This package uses `module-only`, which:

1. Requires the live #517 kernel rather than the old pre-trial kernel.
2. Requires current boot and logdump hashes to equal both the `old` and `new`
   pins in the manifest; no carrier write is possible.
3. Stops managed charging before changing files.
4. Backs up the original service, userspace trial files, main manifest, MP2650
   module, and USB input module.
5. Installs the new userspace files and auxiliary USB input module.
6. Updates the main manifest entries for both modules and every trial file in
   one patch, then fsyncs the result.
7. Requests one direct reboot. It never invokes fastboot, busybox reboot, or
   carrier writes.

`trial_guard.py` treats the USB input module as an auxiliary pinned module. On
the next boot it verifies both modules, the patched manifest, the unchanged
carriers, and the device-local acceptance token. Failure or timeout restores
the original service, main manifest, MP2650 module, and USB input module, then
reboots.

## Acceptance logic

`trial_autoaudit.py` starts from OpenRC `start_post`. It writes a boot-bound
token only after `postboot_audit.py` proves:

- same `#517` kernel and same boot;
- a healthy Type-C/TCPM fixed-5 V source and NCM gadget;
- MP2650 budget and charge limits;
- fresh managed telemetry in active charge or an explicit Full hold;
- protection profile `0x2719` with fault fields clear;
- expected APSD/ADC and EUD-off routing;
- no new critical kernel log or unexpected taint.

The module replacement itself is not proof of USB wake. A separate physical
test operator must verify that only USB insertion or removal caused resume.

## Tests and preflight

- Windows local suite: 106 passed, 0 failed, 5 platform skips.
- WSL/Linux symlink controls: 5 passed, 0 failed.
- Device read-only stage preflight passed on boot
  `97612ad1-d3ac-4721-b2b0-6d2456300559`.
- Preflight confirmed the old main manifest hash
  `b07f7b4bda544a9631ce682221f1e78601d9b38e78d3151e8ac294b57873272d`
  and produced the expected new manifest hash
  `d9f231dc4bef591875d7607c4eab6a7471fa66ac10c04d8f13cc9e3a790a97b7`.
- `package-result.json` records the package tarball, test results, module
  hashes, and preflight evidence.

## Execution gate

Do not execute this package while the r7 long soak is active. After the soak
finishes and its strict audit passes, stage execute may be run. The expected
behavior is one controlled reboot, then a new 300-second acceptance window.
If acceptance fails, the guard restores the previous module and userspace
files. Do not hot-unload `samurai_usb_input`.

No physical USB cycle or wake claim is made by this package alone.
