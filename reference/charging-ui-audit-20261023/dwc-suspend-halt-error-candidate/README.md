# DWC suspend HALT-error return candidate

This offline candidate repairs one swallowed error in `dwc3_gadget_suspend()`. It requires the frozen SUSPHY core candidate (`core.c` SHA `5331ae94…6a17f`) and exact Image503 gadget/header inputs. It is not an Image, has not been deployed, and does not close the complete suspend/resume or retry lifecycle.

## Actual call and resource state

The exact Image503 `dwc3_gadget_soft_disconnect()` takes/releases `dwc->lock`, sets `connected=false`, and calls the existing active-transfer/request removal path. It may complete/reset EP0's setup state, then calls `dwc3_gadget_run_stop(false)`. That function clears RUN_STOP and sets `pullups_connected=false` **before** polling DEVCTRLHLT. It restores its temporary USB2 SUSPHY/ENBLSLPM bits before returning, including on its 2000-poll `-ETIMEDOUT` exit. Neither the software pullup flag nor that timeout proves physical HALT.

After a run/stop error the original soft-disconnect still calls `__dwc3_gadget_stop()` under `dwc->lock`: DEVTEN is masked and both EP0 enable bits are cleared through the existing endpoint disable/request paths. It sets the gadget NOTATTACHED and returns the original run/stop error. The gadget is therefore not operationally restored: endpoint requests may already have been stopped/given back. The unchanged request/DMA handling is not re-certified by this candidate.

Crucially, these functions do not unregister the gadget IRQ, free the event buffer/cache, free endpoint structures/EP0 TRBs, call core exit, or power off PHY/clocks. The registered IRQ's event-buffer pointer and controller resources remain allocated. An already-running IRQ/thread can still finish against those retained structures; this patch does not add an IRQ join, free, worker cancellation or new lock. Existing error-recovery concurrency is not redesigned.

Before this patch, a negative soft-disconnect return with `softconnect=false` falls through the disconnect callback and returns zero. `dwc3_suspend_common()` then joins the IRQ and calls core exit without a HALT proof; the already-frozen SUSPHY rollback is never reached. The new code returns that original error before the callback, so this **current failed attempt** takes the core's restore-SUSPHY/error return and `dwc3_pm_suspend()` skips pinctrl sleep. Core/PHY/event-buffer resources stay active. There is no reason to invent a HALT or release those resources in order to abort this attempt.

## Minimal delta

Only `dwc3_gadget_suspend()` changes. After its original `ret && softconnect` block, a nonzero `ret` is returned. The actual callee returns zero or negative errno; the new false-intent HALT failure therefore remains `-ETIMEDOUT`.

The original true-intent policy is unchanged: attempt `dwc3_gadget_soft_connect()` and return `-EAGAIN`, including when that reconnect fails. A successful stop still takes the original disconnect callback and zero return. No threshold, poll count, error-recovery state, header, PM/core function, callback signature or ABI changes. There is no automatic reconnect when the intent is false, permanent broken flag, free, PHY-off, fake HALT or new retry.

Exact public inputs: gadget `ca4bf1c5a1afa42267d2f7f8b636dfe7ca5a1b9581307093f93a892e2f004314`, core `5331ae946cde894e2da484df5b8fbc6d386d117a60ad0e3dac5a1ebaaec6a17f`, header `9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67`. The candidate gadget is `aabfc928ca916d5b40492996153a03c08b837dcbb1d0c07091f23a35c2debfe2`. `source-result.json` records exact function hashes and source line references; `prepare.py` derives the only-function patch and extracted functions without changing those inputs.

## Actual validation

Thirteen new cases run the extracted actual run/stop, soft-disconnect, endpoint-disable/stop, gadget-suspend and frozen SUSPHY/core PM functions together. The old gadget plus the same SUSPHY core reproduces the unsafe successful core-exit path after a modeled HALT timeout. New DEVICE/OTG-device cases cover both softconnect intents and stop success/error; additional cases cover direct error with delayed EP0 handling, the unchanged successful reconnect policy, original no-pullup early success and runtime error propagation. The timeout cases verify original errno/policy, zero core exit/IRQ join/PHY put/pinctrl sleep, retained structures, masked endpoint state and restored SUSPHY bits.

Compiler PID734 and fixture PID791 both reached terminal zero with GCC ASan/UBSan/Werror. The test's MMIO, PHY/PM, IRQ, request/DMA and reconnect boundaries are explicitly fake; no physical HALT or real IRQ scheduling is emulated. The original 24/20/126 suites were not rerun. The first offline extraction attempt omitted `irqreturn_t`; that source-tool failure is retained under `history/`, corrected without changing kernel policy.

One private AArch64 `gadget.o` was then built from the actual Image503 saved W=1 command, generated headers/config and unchanged Image503 header, with the frozen SUSPHY core present in its private source view. Original284 Ubuntu/root storage guard was used after notifying root/siblings. GCC PID793 was waited to terminal zero on the original exec handle; Werror/W=1 had no diagnostics. The object is 466856 bytes, SHA `3ce30b25a3c19b0cfa0412eb743e189e1c0c06d3648e72726adbb29a7069f639`. Original Image503/shared source/config/symvers/Image/object hashes and helper-after mountinfo remain unchanged. No make, link, module, Image, SDK or device action was performed; the window was returned with no active build/guard/anchor.

## Explicit remaining limits

The old soft-disconnect early return when `pullups_connected=false` has no independent physical HALT check. A later attempt after the failed stop can therefore skip run/stop and appear successful. This patch fixes only the currently swallowed error and does not claim a safe subsequent retry, restored endpoint service or a full DMA drain. The source's existing in-flight recovery-worker policy also remains unchanged.

The separate core resume path still ignores gadget resume errors. Directly returning those errors without a proven core/PHY/event-buffer/IRQ unwind remains rejected; this candidate does not enable that old draft. A future Image must deliberately integrate both this gadget delta and the precise SUSPHY core candidate, and receive a separate lifecycle/integration review. No desktop/Phosh/UPower or charging-state change and no new physical latency acceptance is included.
