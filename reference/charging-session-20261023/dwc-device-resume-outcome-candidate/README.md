# DEVICE resume attempt outcome — internal candidate

The candidate separates the first connect errno from the final synchronous reconnect outcome. `dwc3_gadget_resume()` still returns the original primary errno, including when recovery reconnects successfully. Its skip/OTG prefix and all existing export declarations remain unchanged. Core does **not** consume the new result in this leaf: the existing core PM caller still ignores the legacy gadget errno. No complete PM unwind or physical resume has been proved.

Inputs are frozen retry [gadget.c](../../charging-ui-audit-20261023/dwc-suspend-retry-candidate/gadget.c) `1f47ecbd…cf354`, [core.c](../../charging-ui-audit-20261023/dwc-pm-error-unwind-candidate/core.c) `5331ae94…6a17f`, and [core.h](../dwc-device-start-recovery-candidate/core.h) `9a8dc48a…97a67`. The patch changes only gadget.c and the internal header. The persistent `struct dwc3` declaration is byte identical.

## Interface and result meaning

`void dwc3_gadget_resume_result(struct dwc3 *, struct dwc3_device_resume_result *)` is an internal same-Image DEVICE interface, with a non-NULL caller-owned stack result. The caller must keep the controller bound and the core/PHY powered for the entire operation. This interface supplies no lifetime reference, abort ownership or permission to turn off resources. It has no EXPORT/UAPI and no persistent controller fields.

- `requested` records accepted DEVICE connect intent at entry. No driver/no intent returns a fully initialized skipped result. A requested non-DEVICE call is rejected with `-EOPNOTSUPP` and no connect; the legacy OTG path still calls its original connect operation.
- `primary` is the original first connect result. `recovery_attempted` must be checked before interpreting `recovery`; a default zero does not mean recovery succeeded.
- The existing stack `dwc3_recovery_result` moves to core.h and adds `reconnected`. Every recovery entry initializes it false; only an actual `soft_connect()` return of zero sets it true. A stale worker or disconnect-only zero cannot assert a reconnect.
- Initial connect also captures the real error sequence under the existing spinlock. `operation_completed` requires a successful connect, no error generation pending at publication, and a non-suspended PM context. A first-connect zero does not clear an older RECOVERY/UNRECOVERABLE state and is conservatively incomplete while either persists.
- `detail.pending` retains its exact meaning: generation changed since this attempt's snapshot. A later IRQ/work can arrive after publication. Neither a true completion nor `reconnected` proves USB enumeration, exclusion of later producers, HALT, DMA safety or safe PM failure unwind.

The declaration and complete HOST-only initialization stub follow the original `!IS_ENABLED(CONFIG_USB_DWC3_HOST)` PM guard. Existing legacy HOST stubs still return zero. The new HOST result remains skipped/incomplete, so that zero cannot be mistaken for a successful operation.

## New verification

[test-result.json](test-result.json) records native GCC `-Wall -Wextra -Werror`, ASan/UBSan terminal success for 18 new outcome checks and one actual header HOST-stub check. The fixture compiles ten exact candidate function bodies extracted by [prepare.py](prepare.py), with fake MMIO, endpoint, IRQ/work timing and PM boundaries. It tests initialized skip/no-driver/non-DEVICE paths, first success, recovered success with negative primary, independent stop/connect errors, disconnect-only zero, old failure/count policy, initial/recovery pending generations, post-publication IRQ, the suspended run-stop skip, and stale-work zero. Sixteen current scenarios also compare the actual old wrapper to the new wrapper for primary errno, register/call counts, scheduling and state. These are new interface controls, not reruns of old suites.

The old 7/15/13/24/20/126 suites were not run. The native fixture used only a unique private `/home/cy122/charging-management-20261023/dwc-device-resume-outcome-test-01` output; no storage guard, kernel object, Image, device, SSH, USB, SDK or Git operation was used. All four child compile/run processes reached terminal return code zero; stdout/stderr hashes and PIDs are in the receipt.

## Remaining integration

The existing [unwind audit](../dwc-resume-unwind-candidate-r2/README.md) remains changes-required. A future core consumer must distinguish a genuinely completed operation from failed/pending outcomes while retaining both errors. It cannot simply return the primary errno: runtime/system PM can then report suspended while resources remain powered. Nor may it call core_exit without actual HALT, producer exclusion, IRQ/work join and bind-lifetime ownership. No new core consumer, abort loop or deployment patch is included here.

The header addition is stack type/API only; a future consistent kernel integration must still use matching gadget/header/core consumers. This leaf does not authorize mixing objects, rebuilding Image, deployment or physical PM validation.
