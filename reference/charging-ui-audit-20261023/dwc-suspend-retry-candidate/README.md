# DWC no-pullup suspend retry candidate

This is a limited kernel source candidate after the frozen HALT-error return fix. It prevents the next **software-no-pullup** suspend attempt from treating that flag as proof of hardware HALT. It is not an Image, has not been deployed, and does not serialize the complete asynchronous PM/producer lifecycle.

## Exact failure and minimal change

The actual `dwc3_gadget_run_stop(false)` clears RUN_STOP and `pullups_connected` before its HALT poll. The prior errno candidate correctly returns a first `-ETIMEDOUT`, retaining active core/PHY/event-buffer resources. However, on the next call the unchanged `dwc3_gadget_soft_disconnect()` returns zero immediately because the software flag is false. The core can then exit without observing HALT. The new tests reproduce that exact two-attempt path using the previous gadget plus the same SUSPHY core.

Only `dwc3_gadget_suspend()` changes. Before entering soft-disconnect, it takes the existing short `dwc->lock` and, **only when the software flag is false and runtime PM is active**, reads DSTS.DEVCTRLHLT and requires DCTL.RUN_STOP to be clear. A missing HALT or pending RUN request returns `-EAGAIN` before the original stop/reconnect block. It issues no additional ENDXFER, request/DMA teardown, reset, run/stop write, IRQ operation or callback. There is no added polling, timer, status field or permanent broken flag.

The first actual stop and its original true-intent reconnect/`-EAGAIN` policy remain byte-identical. In a later false-flag attempt the new miss deliberately returns before that reconnect policy, avoiding a newly introduced blind reset/reconnect. If HALT arrives by a subsequent attempt and RUN_STOP is zero, the original already-stopped path can complete without repeating request teardown. A never-connected active gadget must meet the same hardware predicate. The new hardware reads are skipped when runtime PM already says suspended; the original caller/no-pullup behaviour is retained, with no new access to powered-off MMIO.

Inputs are exact gadget `aabfc928ca916d5b40492996153a03c08b837dcbb1d0c07091f23a35c2debfe2`, SUSPHY core `5331ae946cde894e2da484df5b8fbc6d386d117a60ad0e3dac5a1ebaaec6a17f` and header `9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67`. Candidate gadget is `1f47ecbd54f931ccd1068b23c4e171864966f652cdf85986f89e151f386cf354`. Earlier frozen leaves are untouched. `suspend-retry.patch` is only the increment over the preceding errno candidate; the precise core/header are required companions.

## Lock and concurrency boundary

The short spin section contains only the flag/status reads and no sleep. It does not recursively call soft-disconnect while holding the lock. The actual run/stop flag and DCTL writers do **not** all hold this spin lock; some run under `connect_mutex` and existing PM assumptions. Consequently this gate is a hardware snapshot, not mutual exclusion through the later `core_exit()`.

A modeled new RUN request between the DSTS and DCTL reads is rejected by the second predicate. A separate explicit test control injects a producer **after** the snapshot and shows that it can still invalidate HALT before core exit. That control is retained as an unresolved lifetime assumption, not a concurrency-safety pass. Closing that existing producer/core-PM ownership gap would require a separate reviewed lifetime change; this candidate adds no new mutex, reset, free or persistent flag to pretend otherwise.

## Actual validation

Fifteen new cases execute the extracted actual run/stop, soft-disconnect, gadget suspend, endpoint stop and frozen core/SUSPHY functions. They cover:

- Previous two-attempt false success, then new DEVICE and OTG-device repeated misses without repeated stop/request/reset work.
- Late HALT success on a later attempt, preserving one original request teardown; first true-intent recovery policy and no blind second reconnect.
- Never-connected halted/unhalted and HALT-with-RUN_STOP-still-set states; already runtime-suspended direct/core entries without new MMIO.
- A RUN request between status reads, the explicit post-snapshot producer limitation, and the ordinary first successful stop path.

GCC PID744 and fixture PID806 both reached terminal zero with ASan/UBSan/Werror. MMIO, DMA/request, IRQ, PM and reconnect boundaries are explicitly fake; no physical HALT, Linux scheduling or real charging latency is emulated. The old 13/24/20/126 suites were not rerun. Their source and nonchanged behaviour are reused, rather than re-labelled as new validation.

One private AArch64 `gadget.o` was built from the exact Image503 saved W=1 command, generated headers/config and fixed header, with this candidate gadget and the frozen SUSPHY core in its private view. Original284 Ubuntu/root guard and the original exec/Popen handle were used after root/sibling coordination. GCC PID847 was waited to terminal zero in 3.112s; Werror/W=1 had no diagnostics. Object SHA is `a199defc16318131c5abe1d7baf434f9943a1f252d4abbb4c7f434ba96c404e2`, 466720 bytes. Original Image503/shared source, config, symvers, Image and object hashes remain equal before/after, and mountinfo after the helper is unchanged. The window was returned with no active build/guard/anchor. No make, link, module, Image, SDK, device or Git operation occurred.

The full core resume error unwind, original request/DMA completion semantics and asynchronous producer/PM ownership remain outside this repair. Neither source tests nor the single object establish real boot, PM recovery, HALT, IRQ delivery or icon-latency acceptance. No desktop/Phosh/UPower change is included.
