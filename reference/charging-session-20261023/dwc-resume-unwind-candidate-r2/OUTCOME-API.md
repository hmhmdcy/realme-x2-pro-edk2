# Minimal next DEVICE outcome interface — proposal, not a supplied API

The current `dwc3_recovery_result` already owns the real recovery stage, IRQ sequence snapshot and pending-at-publication fact. Reuse it; do not infer success from `pullups_connected`, do not turn it into a resource-lifetime token, and do not add a permanent broken flag.

The smallest implementable first change is an **internal same-Image** function, with the exact recovery-result definition moved from gadget.c to internal core.h and a stack-only output beside it:

```c
struct dwc3_device_resume_result {
        int primary;
        int recovery;
        bool requested;
        bool recovery_attempted;
        bool operation_completed;
        struct dwc3_recovery_result detail;
};

void dwc3_gadget_resume_result(struct dwc3 *dwc,
                             struct dwc3_device_resume_result *result);
```

These are proposed identifiers and semantics, **not implemented/linkable symbols** in this leaf. `detail.pending` keeps its precise existing meaning: pending at the locked publication point, not an assertion that future IRQs cannot arrive. The result must be initialized on the no-driver/no-intent path as `requested=false`, and on every original first-connect or recovery branch. A primary-success/no-recovery branch must initialize its detail explicitly (including a real lock-protected sequence snapshot if exposed), rather than return uninitialized stage/sequence data. `recovery_attempted` prevents an uninitialized/default recovery zero from being mistaken for success.

`operation_completed` can only be true for an actual successful requested initial connect, or for a requested recovery whose reconnect returned zero and whose existing locked publication has no later error generation. A pending-at-publication result is not terminal success. No-driver/no-intent is a separate normal skipped operation; it is not labeled connected. Old unrecoverable state and original first-attempt policy must not be silently cleared.

Keep **`int dwc3_gadget_resume(struct dwc3 *)` unchanged** as the legacy wrapper: use the shared DEVICE implementation and continue returning the original primary result; keep its existing non-DEVICE/OTG branch verbatim. The current header declaration/stub is under `!IS_ENABLED(CONFIG_USB_DWC3_HOST)`; the new declaration/stub must follow that existing build guard. There is no new EXPORT_SYMBOL/UAPI, no changed public symbol signature and no new persistent `struct dwc3` member in this first cut. DEVICE `dwc3_resume_common` is the sole new consumer, and gadget/core/header must be built together in a later consistent kernel; no hot mix of old/new objects is permitted.

For a genuinely completed reconnect, the new consumer may report PM resume success while preserving primary/recovery in diagnostics: hardware operation actually completed. That is different from returning zero for a failed recovery merely to keep PM ACTIVE. When outcome is failed or pending, the new consumer cannot yet return the errno or call core_exit safely; it needs the second boundary below.

## Required failed-attempt ownership, with exact call sites

There must be a returning DEVICE abort operation under the same controller lifetime. Its receipt needs **observations and ownership separately**:

- The attempted stop's primary/cleanup errno and actual DSTS HALT observation. The current soft-disconnect early return when pullups are false does not prove HALT, so a successful return from it cannot populate a HALT-confirmed receipt.
- Device event-source masking, actual IRQ join, and an outside-`connect_mutex` `cancel_work_sync`/join after future recovery producers have been excluded. The actual worker can otherwise reconnect after an earlier HALT observation.
- Who owns any temporary IRQ disable and the exact `pending_events` get/disable being paired. Do not clear/put/enable based on a Boolean without the corresponding serialized producer ownership; do not invent a release after `free_irq`.
- Whether that controller is still bound and its core/MMIO/PHY resources remain retained. A device or PM reference alone is not a replacement for this bind/remove ownership.

The exact functions needing the next lifecycle proof/change are:

1. `dwc3_gadget_resume` / new result implementation and `dwc3_gadget_recover_locked`: preserve first/recovery result and generation publication, no additional retry loop.
2. `dwc3_schedule_err_recovery`, `dwc3_err_recovery_work`, and gadget pullup/start/stop/exit: define a **transient abort** gate and join/cancel boundary that cannot race a queued worker or IRQ request/free. Do not wait for work while holding the mutex it needs.
3. `dwc3_gadget_soft_disconnect` / `dwc3_gadget_run_stop`: supply actual stop/HALT evidence even on a false software-pullup path, without assuming a timed-out RUN_STOP halted hardware.
4. `dwc3_check_event_buf` and `dwc3_runtime_resume`: pair only the real pending-event reference/IRQ ownership, including the error terminal. If core goes off, a registered IRQ must not access it in the callback-return/PM-status window. Re-enabling it blindly is not an unwind.
5. DEVICE `dwc3_resume_common`: only after verified HALT, producer exclusion, IRQ/work join and preserved bind lifetime may it run existing event-buffer cleanup/core exit. Keep the original primary and independent cleanup errors visible.
6. `dwc3_pm_resume`: only a fully unwound failure can take its existing `pm_runtime_set_suspended`. A failed HALT with retained powered resources cannot take that branch. Generic runtime PM likewise sets SUSPENDED after any negative callback; merely retaining resources while returning the error is inconsistent.

The required successful teardown order is therefore **exclude new entry/reconnect producer → stop with actual HALT proof → release internal mutex before work join while the exclusion remains owned → join IRQ and recovery work → revalidate unchanged HALT/bind ownership → event-buffer/core/PHY exit → publish PM-consistent failure and pair only the owned pending reference/IRQ state**. Excluding new recovery/reconnect producers must not blindly disable the whole gadget IRQ before the stop poll: the actual soft-disconnect comment requires event acknowledgments while waiting for HALT. The already-disabled runtime pending-event case needs its own demonstrated event-drain/ownership handling. The ordering of these exclusions and joins must be validated against the real IRQ/UDC/PM locks before implementing it; the existing source does not supply an already valid owner for those steps.

If stop cannot prove HALT, do **not** go on to PHY-off or event-buffer free. A controlled hardware reset/quiescence authority or an explicitly PM-consistent active-error ownership state is still required. This board has no child reset handle that can simply be assumed to do that. A negative callback alone makes generic runtime PM mark suspended, and a blanket zero would hide the failure. That is the concrete remaining blocker, rather than a missing errno check or a need for more old test repetitions.
