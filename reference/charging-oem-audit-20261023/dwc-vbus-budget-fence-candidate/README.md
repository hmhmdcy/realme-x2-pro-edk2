# DWC3 native-PSY software allowance across system PM

This is an independent **source/test candidate only**, based exactly on fixed
core`bd8a8aab…7ffcf`, gadget`9eec86e4…ff0c5` and header`525c1d5d…1373c`.
It fences only `vbus_draw_work` and its software current allowance. It does not
include any outcome/exit/HALT/DMA/UDC-ops experiment, kernel object build, Image,
deployment or device action. The frozen provider2691 and flat candidate are not
modified.

## The actual gap and existing protections

Original `dwc3_vbus_draw_work()` (core:2177–2189) reads `current_limit` without
`dwc->lock` into a local `val`, then calls the PSY setter. `dwc3_gadget_vbus_draw()`
(gadget:3156–3181) and late PSY discovery (core:2217–2226) instead update/store the
value under that lock. Only core removal drains this work (core:2503–2505).
System suspend/resume wrappers (2791–2827) neither join it nor invalidate its
stored value. A device link orders PM callbacks, not arbitrary system work.

There **is** a normal zero draw request: successful gadget system suspend calls
the sleepable disconnect callback (gadget:4993–5010,4007–4021), and
`composite_disconnect()` requests0 (composite:2305–2308). Reset requests100
(2311–2319), SET_CONFIGURATION requests the configured maximum (1059), bus
suspend requests2 (2606) and configured resume requests the maximum (2645).
Those requests do not invalidate a running worker's already-captured local500.

The old actual-function fixture demonstrates a permitted transient sequence:
worker snapshots500 → blocks before the provider setter → normal DWC suspend
requests0 → provider suspend/resume clears native validity → old worker proceeds
and its captured500 is accepted before a new positive native request. The queued
zero may subsequently reduce it again. This is a possible transient stale
authorization, **not** proof that it permanently remains500, that hardware drew
500, or that it caused r5 or the icon delay. Kernel scheduling/PSY boundaries in
the fixture are controlled; no actual system-PM observation is claimed.

The paired R8 provider already clears validity in suspend/resume and rejects
setters while paused. The separate stateless provider-first link candidate2691
prevents fresh DWC resume callbacks racing ahead of provider resume. This fence
and that ordering solve different windows: the fence alone does not ensure a
fresh draw avoids a paused provider, and the link alone does not drain an old
already-running worker. Neither reuses an old accepted allowance.

## Current PM scope and direct-complete boundary

Root's existing strict read-only501 snapshot is pinned in `runtime-evidence.json`:
controller `power/control=on`, `runtime_status=active`, suspended time0 and
autosuspend5000ms; provider runtime status is `unsupported`. No new sampling was
performed here. The source enables PM/PM_SLEEP/GADGET and disables HOST/DUAL_ROLE.
Core probe sets runtime active and calls `pm_runtime_forbid()` (2377–2383).
DEVICE runtime checks additionally reject suspension when connected (2693–2699).

Original `.prepare` can return1 only in DEVICE mode when already runtime
suspended and with no pinctrl (2842–2855). PM core then may skip normal suspend
and resume. That condition is false under the actual on/active premise. This
candidate leaves `.prepare`, `.complete` and all runtime-PM functions byte-for-byte
unchanged. **Auto/runtime-suspended/direct-complete is not supported or newly
guarded by this candidate.** Changing that premise needs a separate review;
there is no general claim that these system-only hooks cover skipped callbacks.

## Exact implementation

One `vbus_draw_blocked` boolean in `struct dwc3` controls the native PSY path.
No gate is added to the existing `usb_phy_set_power()` path, and the fence helpers
return without action outside DEVICE mode or without a successful
`usb-psy-name` interface. The latter matters: the work was never initialized
when the original property lookup failed, so such a path must not cancel it.

- Worker takes PSY pointer, current and gate in one `dwc->lock` snapshot. It
  skips closed/no-PSY/UNSPEC and calls the setter after unlocking. Its error log
  uses that same local current; no retry is added.
- A closed gadget draw request returns **`-EBUSY`**, with no current storage,
  work queueing or later replay. Existing composite callers may ignore that
  return; the gate is a software allowance rule, not a USB transfer/enumeration
  or producer-quiescence guarantee. Late PSY discovery still takes its normal
  reference but cannot enqueue an old stored allowance while closed.
- Only after `dwc3_suspend_common()` succeeds, close under `dwc->lock` and clear
  current to UNSPEC; unlock, then `cancel_work_sync()` this one work. This joins
  any captured500. Afterwards synchronously publish0 to the already-bound PSY.
  A revoke error is logged with its exact errno and does not change the original
  successful PM return after core exit. Common suspend failure returns unchanged
  before touching the gate/current/work.
- Resume keeps the existing pinctrl/runtime-PM order. Only after
  `pm_runtime_set_active()` succeeds, clear UNSPEC and open before hardware
  resume, without queueing old data. Actual new native draw callbacks can now
  provide an allowance. Early set-active error leaves the existing closed gate;
  any resume error closes/clears/joins and attempts only zero again. The original
  primary errno, set-suspended handling and runtime-enable tail are preserved.

PSY references keep their existing DWC lifetime; this change is not the abandoned
full controller/request/ops lifetime framework. No spinlock is held across a
setter or cancel/join. Cancel only joins the software budget work, and does not
prove IRQ, controller, producer, DMA or request resources stopped.

Close snapshots the PSY pointer **before** the join. If it was NULL and late
discovery acquires a supply while closed, this particular zero operation does
not cover that new pointer. The late-PSY fixture uses the actual paired Samurai
provider starting invalid; the actual current device already has its supply
bound. Neither case proves comprehensive revocation of arbitrary pre-existing
allowances in some other late provider. No notifier/retry framework is added.

## Actual verification

`prepare.py` reconstructs the three files and full patch from the pinned fixed
sources. It reverses only the five changed old core functions/new helpers and
one gadget function and verifies every other core/gadget byte unchanged.
The original common PM, runtime PM, prepare, complete and remove functions are
also explicitly checked byte-identical. Header delta is one documented boolean.

20 new actual-function cases passed with ASan/UBSan, real pthreads and compiler
warnings as errors. They execute actual old/new workers/system-PM wrappers,
new helpers/notifier/discovery/gadget draw, and actual R8 provider setter/PM.
Hardware, PSY discovery and queue APIs are fake. The key new test blocks a real
worker thread at its captured500 setter, starts actual suspend in a second
thread and proves it cannot return until its actual cancel boundary performs
`pthread_join` on that same worker. Only afterwards are actual provider PM and
DWC resume invoked. This is stronger than merely counting fake cancel calls;
it remains an offline boundary test, not Linux workqueue or real sleep testing.

Cases also cover original suspend failure, exact zero-revoke errno, closed
requests, UNSPEC skip, normal new100 permission, set-active early failure,
resume primary/revoke dual failures, late PSY, no initialized interface,
notifier registration failure, old PHY and non-DEVICE paths. No old matrix was
rerun. The first **compile-only** attempt failed on the original notifier's
unused `event` argument; its runner/receipt are retained. The final runner uses
the kernel's existing `-Wno-unused-parameter` policy, without changing that
actual old argument/body. The20 cases then passed in one execution.

All test ELF/raw logs remain in the unique private test outputs. No original284
storage helper/volume, private kernel build, Image link, SDK, Git, phone, SSH or
USB operation was performed. Future adoption would need an actual consistent
Image build and independent review; this leaf delivers source and offline tests.
