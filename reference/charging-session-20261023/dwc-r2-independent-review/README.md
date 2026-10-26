# Independent review of the frozen DWC R2 candidate

No new confirmed defect was found in the reviewed scope. The two `stopping && is_on` changes close the preserved R1 default teardown counterexample. The examined actual IRQ/work/configfs-NCM call paths do not establish a reverse `connect_mutex` wait that would turn the reviewed `synchronize_irq` sites into a new deadlock. This is a scoped source review, not kernel lockdep or hardware acceptance.

The reviewed directory is `charging-oem-audit-20261023/apsd-dwc-window-candidate-r2`. Its patch SHA is `1c8df68911b05ae565abb4cfa347ad59eb9bafedeba4874d0b3cf6d697f1f031`. `review.py` only reads/hashes the frozen files; it does not import their generators. All delivery hashes match. Core/header/window helper bytes and 19 extracted functions match R1; the only changed function is pullup, with exactly the two stopping conditions. No frozen author file was edited.

## The actual no-window teardown chain

The cached source354 UDC `gadget_unbind_driver` calls `usb_gadget_disconnect_locked` before `usb_gadget_udc_stop_locked`. The former invokes gadget pullup(0); the latter eventually invokes `dwc3_gadget_stop`. R2 exit first marks stopping/SHUTDOWN, then invokes `usb_del_gadget`, preserving `connect_mutex` until after unbind/stop and joining recovery work.

R1 rejected off at the first stopping check, so the preserved actual-function reproduction reports ESHUTDOWN, no soft disconnect/HALT, then IRQ free with no active window. R2 permits off at that check. SHUTDOWN is deliberately not a busy window, so off follows the original runtime-PM barrier, suspended shortcut, and active soft disconnect path. Its on request is still rejected before reconnect.

The second condition is independently necessary: off may have passed the first check and acquired PM before a simultaneous shutdown sets stopping. When it reaches `connect_mutex`, stopping must continue to reject on but permit off. Otherwise it silently skips the active disconnect after the PM preparation. The retained fifth R2 actual-function case exercises that exact boundary. An owned live window continues to defer off as intent until shutdown parks with its retained reference; that is distinct from ordinary no-window exit.

The exact five-case receipt `12397ef8921c9ed4ca24c8cf79146f6207094d2815d796c776849274f77cca60` was reused: active no-window exit, already-suspended no-resume exit, owned-window off/shutdown, stopping on versus off, and shutdown after off PM acquisition. Neither those five nor the old 13 groups were rerun. The R1 failure JSON was read as historical failure evidence, not rewritten as a pass.

The original `dwc3_gadget_soft_disconnect` can still fail or time out. UDC unbind's failure handling and the underlying PM-zero shortcut predate this candidate; R2 does not make such a failure proof of HALT. The new tests' successful fake disconnect is not a hardware guarantee. Core resume's historical ignored gadget-resume error is also unchanged; the explicit new window end reports its own restoration errors separately.

## synchronize_irq under connect_mutex

The actual threaded IRQ takes `dwc->lock`, processes its event buffer and calls device/endpoint dispatch. None of the examined DWC IRQ entry/dispatch functions directly takes `connect_mutex`. A fatal event schedules recovery work; it does not wait for that work. Thus the worker waiting for the mutex is not itself a reverse wait from the IRQ being synchronized. Exit joins recovery work only after USB gadget deletion/IRQ stop and after releasing the connection mutex.

The new begin claims CLAIMED before its mutex/IRQ wait, and end marks RESTORING before its reconnect/IRQ wait. Both are busy states. Reentrant pullup from an allowed gadget callback therefore updates intent and returns before PM, `synchronize_irq` or `connect_mutex`; the intended reentry cannot wait on that mutex. The stopping on path returns even earlier. This is the specific reason the new busy-window paths differ from an unrestricted callback assumption.

The default recovery helper still holds `connect_mutex` around soft disconnect, sleepable gadget disconnect, IRQ synchronization and reconnect. That same lock/synchronize order already exists in the original Image-associated gadget source. The scoped review does not infer safety merely from its age: the current configfs/NCM callbacks were checked separately.

Five small callback sources were read from the authorized original mounted source and compared byte-for-byte to Image source commit `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`. Their hashes are in `callback-source-manifest.json`. In that current chain, IRQ disconnect reaches configfs's spin-locked composite callback, composite `reset_config`, NCM disable, and gether endpoint teardown. NCM/gether contain no gadget connect/disconnect/activate/deactivate call and no DWC connection-mutex access. The gether `flush_work` is in sleepable final cleanup, not in its IRQ-context disconnect. Composite suspend/resume reaches function methods and vbus-draw; configfs's optional driver suspend/resume hooks are null. EP0 setup/completion and NCM notification/network completion likewise do not supply a connection-mutex reverse wait. Endpoint completion has its own ordinary spinlock/queue behavior, not a synchronous wait for DWC error work.

This does not certify arbitrary future function drivers. A future consumer must not call the process-context begin/end API from an IRQ/gadget callback or while holding the UDC connect lock, DWC spinlock or connection mutex. It must not synchronously join its own work from such a callback. Those are caller/lifecycle constraints, not a newly proven fault in the present NCM path.

## Default behavior and owner integration

With no consumer the window remains IDLE, takes no retained PM reference and adds no PHY/PMIC/EUD operation. The PM gate is cleared through the common exit paths; prepare/complete exclude new claims across system sleep. Default error recovery retains its recovery-count cap and state transitions. Start resets the per-bind window/stopping state while retaining cookie generation. Removal's ordering now keeps the mutex valid through UDC callbacks and joins work before destroying it. No further default regression was demonstrated by the reviewed source/receipts.

The EUD, DWC and PHY foundations are compatible only through a same-kernel session owner that supplies their missing common lifetime and power constraint:

1. Take one owner/session mutex in process context; separately establish current-boot route/PD/source authorization and serialize with UDC/platform teardown. A device reference alone is insufficient. No component's internal mutex may remain held across another component call.
2. EUD begin establishes software COM quiet only. DWC begin must return a valid owned token and verified HALT. A failed DWC begin may still return a nonzero cookie/retained reference, requiring explicit cleanup; EUD begin failures do not grant ownership.
3. Only then may an authorized PHY owner borrow its already-initialized, powered state. No component may obtain its prerequisite by resuming/resetting the PHY. PHY write/restore failure retains its token: successful PHY end is required before DWC end, and DWC restoration failure must not be followed by unconditional EUD end.
4. Restore PHY, then DWC, then EUD, with independent primary/restore/cancel results. The owner must retain its own active-power/PM cancellation constraint through EUD end because DWC end releases its own reference. Cancellation or SHUTDOWN/REMOVED is not restoration. EUD's removed-token acknowledgement may release its reprobe interlock only after the other work is cancelled/joined.
5. The owner must be part of actual DWC/EUD/PHY lifecycle cancellation before UDC stop/core exit or COM unbind; a cookie does not prevent teardown from resetting/powering off the hardware. The bounded session must define an explicit terminal failure policy. No automatic owner, timeout reconnect or hardware trial is added by this review.

`review-result.json` records the checked bytes and source functions. No new C counterexample was needed because no additional issue was confirmed. No phone, SSH, USB, SDK, shared-source write, kernel build or author-suite execution occurred.
