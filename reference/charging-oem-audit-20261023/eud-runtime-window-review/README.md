# Independent EUD software-window review

Review outcome: **changes required** for the borrowed-remove work lifetime. The candidate and its receipts were not changed. This review binds `eud.c` SHA `8cdd661b7834a7ccba46bd7577be84bd3bb81f6a00fb512d2b70e9d7c4c1231c` and patch SHA `838cb462b1ff1535185b82fee980ef7f368585ba975aaf3f394e07f5e93f4929`.

## Confirmed issue

`eud_remove_locked` cancels RX at candidate line 1666, then unregisters the console at 1669. A console callback can already have passed its `!rx_stopping && !window_quiet` test (502–504 or 572–574) and pause before the actual `mod_delayed_work` queue operation. `begin` can mark quiet/cancel existing RX and return while that callback remains paused. During borrowed remove, the early RX cancellation also sees nothing queued; console unregistration then waits for the old callback. If it performs its already-approved queue operation before returning, remove continues through UART removal and only a final TX cancellation, clears `eud`/drvdata, and returns with RX still pending.

`late-remove-counterexample/result.json` records an actual-function reproduction of this order. The frozen candidate function extraction is copied byte-for-byte. Only OS boundaries model the console pause and console-unregister joining that callback. The single case passes ASan/UBSan/Werror and proves `rx_work.pending==1` after endpoint removal. It **does not** execute work after memory release and is not a measured use-after-free. Since the port was allocated with `devm_kzalloc`, a queued callback retaining that endpoint is a lifetime risk that must be closed before integration. The original driver's early-cancel order also permits this risk; this is not presented as a regression solely caused by the new gates.

Required correction: withdraw all producers (IRQ stop/free, console unregister and UART removal), then perform a final RX and TX join before clearing/releasing the endpoint. The author acknowledged the reproduction and is preparing an independent R2. This review does not edit the author's frozen R1.

## Additional targeted checks

`result.json` is the separate **five-case test receipt**, not overall candidate acceptance. It copies the author's bound extraction without running the old nine groups, additionally extracts the actual nbcon device-lock/unlock, thread and atomic callbacks, and exercises:

1. Default TTY shutdown drain and nbcon threaded output.
2. Begin while a real TTY work thread has dequeued one frame: join completes, undequeued bytes pause, no FIFO access occurs after quiet.
3. Begin while a real nbcon thread owns the TX mutex: begin waits, remaining thread/atomic output obeys the UART gate.
4. A console kick queued after begin cancellation: RX entry remains inert while the endpoint is alive and quiet. This property alone does not solve removal lifetime; the counterexample above demonstrates why.
5. End/remove serialization and old-token rejection after a new endpoint generation.

All five pass ASan/UBSan/Werror with deterministic pthread boundaries. Source review found no additional blocking issue in the scoped default path, token checks, IRQ-enable-intent restoration, PM fences or F1 commit gate. These tests are not full kernel lockdep or hardware validation. The API's explicit requirement to call outside EUD callbacks and with no UART/TX/console lock held remains a consumer integration precondition.

## PD observation receipt

The current `reference/charging-management-20261023/pd-controls-r8-result.json` SHA is `b31b31b10caa02477fb7be79b9c825e9aefc01b584a9424ec710e612ca13a65d`, exactly matching `apsd-lifecycle/pd-controls-r8-correlation/result.json`. The executed-host-script field is already included in those bound bytes. No observation was regenerated or acquired again.

Reproduce only this review with `python3 review.py`; reproduce only the remove counterexample with `python3 reproduce-late-remove.py`. Both write solely inside this review directory. No phone, SSH, USB, SDK, shared source or author-file mutation occurred.
