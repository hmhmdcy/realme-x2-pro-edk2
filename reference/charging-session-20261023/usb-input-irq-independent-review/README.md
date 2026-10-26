# USB input IRQ independent review

Reviewed frozen author delivery `392ba797…539c5d`. No new blocker was found
within the added IRQ/probe/shutdown/duplicate-suppression scope.

The R7 baseline `b712764f…7098`, decoder `a17caa2c…548fd` and twelve retained
functions match. The actual current native DTB `9271d9cc…914358` was independently
parsed from retained raw bytes: PMIC2 has no interrupt-parent or interrupt cells,
so the actual OF parent walk reaches the four-cell SPMI controller. Its child
address/size cells also match the proposed one-cell reg. Both named IRQ tuples
match the un-commented OEM 19781 source, including trigger types.

Probe requests IRQs while paused and publishes the supply and stop action before
unpausing. Event check and queue share the stop mutex; stop unlocks before joining
the worker. Late handlers therefore cannot queue after stop, suspend or shutdown.
The final stop devres action precedes supply unregister, IRQ free and input free;
probe failures before that action remain paused. The new shutdown calls the same
old stop because normal device shutdown does not unwind devres. The actual
device-core shutdown path holds device/parent locks and drains runtime PM before
dispatch. Existing system PM resume remains unchanged; this is not a new PM
recovery claim. A single enabled exact DT node suppresses register_board's extra
software provider. The 1-second fallback remains unchanged.

All frozen file hashes, the 16-case/four-actual-function test receipt, saved old
runner, relocation addendum and the single-object W1/Werror build receipt bind
to the actual reviewed source. No author generator, test or compiler was run.
The independent receipt is `review-result.json` SHA
`7c217a9d2a974393a74a703bbb24909058dbe9b52e3f31ac19e5efc21202af7c`.

This does not prove real IRQ allocation/delivery or icon latency. The fragment
has not been compiled/applied. Optional platform lookup can map discovery errors
to ENXIO, so polling fallback cannot count as IRQ success. The intended one-node
board tree is the duplicate-suppression scope. Normal IRQ-controller mask/ack/type
programming is distinct from charger, PD or APSD policy writes; the new handler
only schedules the unchanged read/decode path.

Only this review leaf was written. No device, SDK, mount/storage guard, desktop
change, build or test rerun occurred.
