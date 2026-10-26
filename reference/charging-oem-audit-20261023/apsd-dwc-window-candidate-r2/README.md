# Optional DWC3 gadget window, offline candidate

This patch supplies the missing DWC3 data-controller serialization component. It installs no caller and performs no APSD, PD, EUD, PMIC, or PHY operation. The running Image, shared kernel source/output, package ABI, and phone were not changed.

This is revision 2. The frozen first candidate (`../apsd-dwc-window-candidate/`, patch `e708a98c…fc287`) has a confirmed default teardown regression and is retained only as history. Its original fixture skipped UDC's disconnect callback before stop, so its 13 groups did not cover the no-window exit path. The independent actual-function reproduction is retained in `r1-failure-review.json`. R2 changes only two `dwc3_gadget_pullup` conditions: stopping rejects an **on** request while an **off** request still follows the original runtime-PM/disconnect path. `r1-to-r2.patch` is the complete incremental diff; the other 19 extracted functions and `core.h/core.c/window-functions.c.txt` are unchanged.

`baseline.json` pins the three original-Image-associated source files to commit `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`. The source/Image association and actual peripheral/legacy-glue DTB are recorded in `../apsd-integration/current-r7/`. `make-candidate.py` applies exact anchored changes to these saved bytes and emits `dwc-window.patch`; it never patches the mounted source.

## Internal calling contract

The three entry points are declared only in DWC3's internal `core.h`, with no `EXPORT_SYMBOL`, UAPI, sysfs control, timer, or automatic consumer. A future session owner must be compiled into the same kernel/DWC3 context. The current `samurai-usb-input` module cannot directly call these APIs. The owner must run in process context, serialize calls for its one cookie, and provide normal bound-object lifetime protection against UDC unbind/DWC removal. A device reference alone does not pin the gadget binding or controller state.

| Call | Success | Failure / retained state |
|---|---|---|
| `begin(dwc, &r)` | Nonzero cookie, HALTED, actual `DSTS.DEVCTRLHLT` readback, one active runtime-PM reference retained | Inactive controller: `-EAGAIN`; PM-disabled/error propagated. Unbound/stopping, wrong role, existing error, another window/PM transition/system prepare are rejected before hardware use. HALT failure returns a cookie and FAILED: it is still owned and requires explicit cleanup. |
| `cancel(dwc, cookie, &r)` | Attempts HALT, marks cancelled, keeps cookie/reference and blocks reconnect/PM | It never reconnects or releases the window. A failed HALT is not described as quiet. Stale cookies return `-ESTALE`. |
| `end(dwc, cookie, &r)` | Restores the latest known pullup intent, releases the window and exactly one PM reference | Restore failure attempts HALT again and retains the cookie/reference. `restore_error` and `halt_error` remain independent. Two intent changes during restore yield bounded `-EAGAIN`, followed by a park attempt, rather than success. |

Always inspect the return code **and** receipt. A nonzero `begin` return with a nonzero cookie owns cleanup. `halted=false` after any error means HALT was not established; it is not permission for analog detection. A successful `end` with `restore_wanted=true` means the existing controller connect path completed; it does not prove host enumeration or network recovery. There is no background retry, expiry, or forced reconnect.

`begin` uses this kernel's `pm_runtime_get_if_active(dev)` before taking either DWC lock. It never invokes resume to obtain a window and cannot make a PHY reset its quiesce prerequisite. Callers receive `-EAGAIN` when inactive. Any future activity/resume policy needs a separately reviewed lifecycle. `end` is allowed only after the owner's own PHY operation has been restored; no such operation exists here.

## Serialization and teardown

`connect_mutex` serializes actual disconnect/connect, window operations, and error recovery. The short `dwc->lock` protects claim/PM gates and `softconnect` intent. No runtime-PM get/put is performed while holding `connect_mutex`; no spin lock is held while acquiring that mutex or waiting for IRQ completion.

While CLAIMED/HALTED/RESTORING/FAILED, pullup records intent under `dwc->lock` and returns without resuming or taking `connect_mutex`. This includes pullup reentry from disconnect callbacks during restore. Normal pullup rechecks the window after its original PM/IRQ preparation and mutex acquisition. The existing error worker defers recovery; explicit end reuses the actual recovery sequence, including its existing recovery-count cap. A queued worker cannot reset the controller inside the window.

The held PM reference prevents ordinary runtime suspension. A shared atomic gate additionally excludes the begin/PM-callback race across the full core suspend/resume functions, including PHY teardown/init. System `.prepare` rejects an active window and fences new begin through `.complete`, including direct-complete paths. These markers do not infer any PD condition.

UDC stop marks stopping before waiting for `connect_mutex`, attempts HALT, invalidates the window as SHUTDOWN, and drops its retained reference once. A begin that lost this race preserves SHUTDOWN. Old cookies cannot affect a new bind because the generation is retained. Gadget exit calls `usb_del_gadget` while `connect_mutex` still exists; after UDC/IRQ stop it joins recovery work, then destroys the mutex. This order is necessary because the added stop path uses that mutex.

In ordinary no-window teardown, shutdown has no owned PM reference and does not access hardware. It must therefore permit UDC unbind's subsequent pullup(0) through **both** stopping checks. That original path synchronizes runtime PM, skips resume if already suspended, or performs the usual active soft disconnect. It must not be silently replaced by a stopping error. When an owned window is active, off remains intent-only until shutdown parks using the held reference. Existing failures of the underlying hardware disconnect are still errors, not evidence of HALT.

Ordinary remove may subsequently reset or power down the controller/PHY. SHUTDOWN does **not** promise analog quiet survives teardown. Before a future consumer is enabled, its work must be cancelled and joined as part of the bound DWC lifecycle before stop/exit; this candidate installs no external work to join. Keeping an unbounded FAILED window would deliberately block PM, so a future owner must define a bounded session and an explicit failure policy.

## Agreed EUD software-layer integration boundary

The separate EUD candidate is also internal, returns without holding its component mutex, never calls DWC, and its first version touches neither CSR nor AHB2PHY. A future owner can serialize whole transactions under its own session mutex:

1. EUD `begin` returns a software-quiet cookie; then DWC `begin` returns a verified HALT cookie. Neither component's lock is held across the other's call.
2. Only a separately reviewed PD/route/PHY owner may authorize analog work. Both tokens must still be valid and uncancelled. Neither software quiet nor DWC HALT proves DP/DM high impedance or route ownership.
3. After the owner's PHY restoration, DWC `end` returns, then EUD `end` restores its own producer intent. DWC restoration failure retains both components quiet for explicit recovery; it must not be followed by an unconditional EUD reconnect. Removed/cancelled tokens and `ENODEV` are not restoration success.

DWC end releases its own active PM reference. The future cross-component owner must independently retain its power/PM/cancellation constraint through EUD end; the DWC reference is not a lease that survives that call. A PHY cookie must be restored successfully before releasing the DWC HALT window. No component mutex is held across another component call.

There is no cross-component call or automatic implementation of this sequence in the patch. Actual PD-controller register snapshots may become independently checked session preconditions; disabled DT nodes and observed engine bits do not prove a bootloader-negotiated contract is inactive.

## Validation

`test-result.json`: five new focused groups run the affected actual functions with the corrected source354 UDC call order at the fake `usb_del_gadget` boundary: unbind → disconnect/pullup(0), then UDC stop. IRQ-free additionally asserts HALT or an already-suspended controller. Cases cover active no-window exit, suspended no-resume exit, owned-window off/shutdown, stopping rejecting on but permitting off, and shutdown racing after off's PM acquisition. ASan/UBSan and `-Werror` pass. The original 13 groups are not rerun and are explicitly historical evidence; the runner verifies 19 unchanged function bodies and one changed pullup body against their original hashes. These are fake OS/PM/MMIO/IRQ boundaries, not kernel lockdep or hardware validation.

`build-result.json`: only the newly affected `gadget.o` is rebuilt after `modules_prepare`, using the mounted build configuration in a separate private source view/O directory under `/home/cy122/charging-management-20261023/apsd-dwc-window-candidate-r2/`. R1's unchanged core/header/glue object checks remain historical receipts and are not presented as a new R2 four-object build. No SDK is invoked, no Image/package is built, and hashes confirm shared source/config remain unchanged. `delivery.json` binds this revision, its five tests/build, unchanged-body evidence, and the known R1 regression.

Offline reproduction, from WSL, using only this directory:

```sh
python3 make-candidate.py
python3 run-teardown-tests.py
python3 build-private.py
```

The build helper uses the authorized original `storage.mounted_build()` helper to locate/restore the existing source volume. It does not create an SDK binding or edit its source/build output. There is no deploy command.

