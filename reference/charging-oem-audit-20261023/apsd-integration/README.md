# APSD integration: existing-storage inspection

This continuation is read-only and offline. It uses the requested `reference/kernel461/storage.py` entry, performs no SDK binding, mount/recovery, phone/SSH, build or deployment operation, and does not change shared sources. Existing OEM restoration and tests in `../apsd-lifecycle/` are reused without rerunning them.

## Actual result

The kernel461 storage chain resolves `storage.mount` to `reference/kernel284/storage.py`. This is the existing `mounted_build()` implementation, not a new storage locator. Its implementation opens the original storage lock and, when `/mnt/samurai-full282` is not mounted, invokes `mount -o loop,noatime` on the ext4 backing image. Therefore calling it without checking current mountinfo would violate this task's explicit no-remount constraint.

The actual bounded inspection found no exact mount at `/mnt/samurai-full282` in `/proc/self/mountinfo`; `build/.config` and the previously named `source354` were absent. It did not call the recovery branch. `inspection-result.json` retains timestamps, exact locator/module hashes and source, absence checks, requested paths, and operation flags. This is an unavailable-source result, not a claim that R7 lacks any particular API.

`inspect-mounted.py` can inspect an already mounted volume later. It first requires the exact existing mount; if present, it calls the original `storage.mount.mounted_build()` with a boundary allowing only read-only `findmnt`. A race that would enter the mount branch is rejected before execution. It never calls `candidate()` or `sdk_candidate()`. Source selection uses build/source or the generated build Makefile, not a guessed source354 path; ambiguous/missing selection is preserved as a refusal. All retained source bytes remain only in this candidate directory, and retained source alone is not marked as deployed-R7 linkage.

## Specific integration questions still requiring the selected R7 bytes

| Question | Existing API to inspect | Why its name is insufficient |
|---|---|---|
| Generic PHY BC1.2/DPDM entry | `phy_ops`, `phy_set_mode_ext`, femto driver modes and submodes | A generic USB device mode or reset does not establish high-Z detection ownership or a restoration receipt. |
| Quiesce data path | `usb_role_switch_get/set_role`, DWC3 role-switch registration and callback | USB_ROLE_NONE must be wired to this board and synchronously stop the relevant gadget/glue/PHY users; the enum alone does not prove it. |
| Restore data path | Previous role plus exact controller/glue completion and runtime-PM state | Setting a role value can schedule work; success need not mean endpoints, clocks and data path have returned. |
| EUD ownership | qcom_eud, actual EUD COM driver and DT role-switch endpoints | Console/hub routing may bypass or separately consume the PHY; a DWC role switch cannot be assumed to quiesce EUD. |
| PD/role state | Board TCPM Type-C and PD-PHY nodes/drivers, role-switch/connector endpoints | A missing property/driver is unknown PD state, not PD inactive; cached APSD bits do not supply this owner. |
| Serialize/cancel | USB/PHY locks, role work completion, PM callbacks and detach event source | Original OEM phy_lock and single-IRQ ONESHOT do not provide a full cross-driver transaction. |

The intended smallest boundary remains an explicit PHY detection-mode owner with balanced acquire/release, a real USB/EUD quiesce/restore handshake, and authoritative current PD/role/swap cancellation feeding one bounded per-attach APSD session. It should reuse existing APIs only after their actual wiring/completion semantics are established. It must not use default PD=false, reset the entire PHY as a prerequisite, or put hardware writes into a power-supply getter/decoder.

No driver patch or tests of an invented integration model were created without the selected source baseline. The next concrete input is the already mounted build/source locator and its R7 artifact linkage; this task does not start a restoration flow to obtain it. Once available, the listed paths allow an exact diff and small tests of affected real functions. The current storage absence does not justify changing EUD, PMIC registers or USB roles.
