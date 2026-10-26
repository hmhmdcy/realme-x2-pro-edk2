# Recovery work must retire before gadget teardown

This is a source-only, exit-only candidate based on the frozen DEVICE outcome
gadget `1080c78f…7859` and header `6f6ec74e…cc05`. Core `5331ae94…a17f`
is unchanged. It adds one per-gadget-lifetime `recovery_stopping` field and
changes exactly four functions: IRQ recovery scheduling, recovery publication,
gadget init and gadget exit. No PM error consumer, core/PHY teardown, endpoint
policy, new retry, reset or desktop change is supplied.

The old exit cancels recovery work, destroys `connect_mutex`, then calls
`usb_del_gadget()`. Its gadget IRQ is still registered during this interval.
A new IRQ can enqueue recovery after cancellation, and normal UDC unbind can
call the actual pullup function while the mutex has already been destroyed.
The eight-case native fixture preserves that original counterexample; it is
not a measured phone UAF or a claim that fake recovery I/O is real MMIO after
free. In particular, the real soft-disconnect can skip hardware on an already
false pullup flag. The counterexample's unequivocal observation is the actual
worker/pullup reaching the retired fixture mutex and recovery boundary.

The candidate closes the recovery enqueue gate under `dwc->lock`, then calls
`cancel_work_sync()` with neither that spinlock nor `connect_mutex` held.
Both the IRQ enqueue and the helper's pending-publication enqueue check the
gate and queue under the same spinlock. A queued old worker exits the helper
with an initialized `-ESHUTDOWN` receipt. A worker already past that check may
complete its existing attempt, but the synchronous work join precedes any
UDC unbind or endpoint/resource release. Real IRQ generations and the original
pending state are retained; gate closure does not invent recovery success.

`connect_mutex` now survives the entire `usb_del_gadget()` call and is destroyed
after it returns. The pinned UDC source is an essential part of this argument:

* `usb_del_gadget()` explicitly documents unbinding a bound gadget and calls
  `device_del(&gadget->dev)` synchronously.
* The gadget bus `.remove` is `gadget_unbind_driver()`. It disables connection,
  joins VBUS work, calls pullup-off under its own `connect_lock`, disables async
  callbacks and joins the gadget IRQ. After the function-driver unbind it calls
  `usb_gadget_udc_stop_locked()` under that same UDC lock.
* That calls the actual DWC `udc_stop`: it clears `gadget_driver` under the DWC
  spinlock and calls `free_irq(irq_gadget, ev_buf)`. The new mutex destruction
  therefore follows the bound UDC's synchronous IRQ release.

The exact functions, hashes and line numbers are in `caller-source-evidence.json`.
The UDC source is the existing 56,279-byte snapshot `17d0d78f…1041`, already
bound by `usb-resume-errors/source-manifest.json`; it is not a fake test body.
The supplementary cached device core shows `device_del → bus_remove_device`.
The generic bus/dd implementation is not newly imported here: synchronous
driver removal is the existing device-core API contract. The fixture's fake
`usb_del_gadget` tests only the DWC boundary order and does not replace that
source/API argument.

The gate reopens only before `INIT_WORK`, mutex initialization and
`usb_add_gadget()` in a new gadget lifetime, while that lifetime has no registered
UDC/IRQ producers. It is neither a permanent broken state nor a PM-abort token.
Existing role/caller ownership must prevent parallel gadget init/exit or a new
mode from reusing the object before the old exit returns. Init-failure repair,
parallel double exit and new role/PM serialization are outside this change.

The eight new cases cover the old late-enqueue/retired-mutex control, IRQ arrival
between cancellation and UDC stop, queued work removal, closed helper receipt,
an actually running pthread worker joined before unbind (including pending
publication), open-gate pending delivery, unchanged old unrecoverable policy,
and the original null-gadget no-op. GCC PID788 and fixture PID797 both returned
zero with ASan/UBSan and `-Werror`. IRQ/workqueue primitives, UDC callbacks,
MMIO/DMA, PM and allocation boundaries remain fake. The pthread mutex/condition
join is real; Linux IRQ/workqueue concurrency is not exhaustively proved.
Old 7/15/13/24/20/126 and outcome suites were not rerun.

## The DEVICE abort boundary remains open

This patch is a prerequisite lifetime repair, not a safe `core_exit()` license.
`connect_mutex` still does not serialize UDC request/free IRQ, endpoint disable
or dequeue, EP0 paths, frame reads, all RUN_STOP writers, pending IRQ disable
depth or core/device removal. The DEVICE failed-resume consumer is absent.

For a future confirmed-HALT abort, a separate transient owner must exclude new
reconnect and endpoint MMIO producers, serialize IRQ registration/free and the
event buffer, join recovery outside its mutex, then revalidate HALT and RUN_STOP
under that retained ownership before core/PHY exit. `dwc->mutex` cannot simply
be taken by the PM callback: the actual DRD owner already holds it across
`pm_runtime_get_sync()`. A device reference alone does not stop unbind/devres.
The existing `pending_events` bool also does not own arbitrary IRQ-disable
depth: its actual get/disable is paired only by the successful runtime-resume
tail. Those entries need one explicit serialized owner before a negative
DEVICE resume return can be added.

If HALT remains unknown, this board's optional child reset handle is not a
proved hardware quiescence authority. A negative runtime callback marks the
device suspended even if initialized core/PHY remain powered, while a blanket
zero would conceal failure. A real reset authority or a deliberately specified
PM-consistent ACTIVE-error design is still required. The earlier suspend retry
snapshot only blocks a false successful power-off; returning `-EAGAIN` alone
does not prove the completely usable ACTIVE state required by the runtime-PM
contract. Full resume unwind and full suspend ACTIVE recovery remain unproved.

A subsequent private single `gadget.o` compile may check this target's syntax
and layout use only. The new `struct dwc3` field changes layout: every header
consumer must be consistently rebuilt for any future integration. No mixing
with old-layout objects, Image/link, handset deployment, SDK, Git operation or
shared source/build write is authorized or performed by this leaf.
