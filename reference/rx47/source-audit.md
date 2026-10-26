# RX47 host session boundary and remaining TX/IRQ evidence

2026-10-09. This audit reuses the one completed RX46 administrator trace.
No new elevated capture, driver replacement, pipe reset experiment, flash,
PHY reset, DAP mux change or fuse/APDP operation was performed in RX47.

## Endpoint controls in the actual trace

`export-etw-controls.py` selects the unique VID 05c6 / PID 9505 rundown,
eight UCX control events and sixteen associated USBHUB3 client/reset events.
The source ETL SHA256 is
`b2911052876e89712276081e5ad0e6491f525bad8aed2f64076261dc3b37f595`.
The full ETL, full XML and provider manifests stay local in
`E:\edk2-samurai-out\rx46`; only reviewed target events are exported.

Two pairs of successful endpoint controls occur in the retained timestamp
strings at 19:41:57.427879/427983 and 19:42:02.558986/559167. Each pair clears
ENDPOINT_HALT on IN 0x81 and OUT 0x02: bmRequestType=02, bRequest=01,
wValue=0, wLength=0. Matched completion USBD and NT status values are zero.
USBHUB3 records four client URBs with function 0x1e, the RESET_PIPE /
SYNC_RESET_PIPE_AND_CLEAR_STALL function. They match the two session
boundaries in the serial helpers by timing; this association is inferred.
No target CDC line-coding or DTR/RTS request appears in these controls.

[Microsoft's URB_HEADER documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usb/ns-usb-_urb_header)
explains that RESET_PIPE_AND_CLEAR_STALL clears endpoint halt and resets the
host data toggle. A device which fails to reset its own toggle can treat
the next packet as a duplicate and drop it. This supplies a specific reason
to compare continuous ownership with reopening. **The trace has no physical
DATA0/DATA1 observation; it does not prove this device has that defect.**
Do not patch a driver or actively reset the endpoint based on this hypothesis.

## Actual host implementation and capture limits

The installed oem102.inf service is qcusbser, binary version 2.1.3.5,
252,288 bytes, SHA256
`ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151`.
UCX01000.sys is 10.0.26100.9549, 310,592 bytes, SHA256
`092fa18ea4dd1792f8a190270f8c33cc5ee6a0d05d2e34df64f75b95a4d73dcd`.
The RX36 legacy source contains QCUSB_RetryDevice IN/OUT resets and similar
QCPNP reset calls, but its version differs from this installed binary. These
source call sites cannot prove which installed function sent a given URB.

The existing ETL contains UCX 27/v1 and 26/v0 transfer headers and no 28/29
partial/full data events. Searching its unchanged bytes for the R46G frame,
ASCII payload and ASCII hex found no occurrence. Provider templates expose
data variants, but captured events do not supply the original OUT bytes.
`inspect-etl-payload.py` reproduces these limited checks against local files.
Missing byte patterns alone are not proof that every possible encoding was
searched. Raising verbosity without a demonstrated template path would be
another guess. The one authorized capture is complete, not continuing consent
for further elevated runs.

## Newly exercised device paths

The final host source's interactive post-reboot session accepted 14 native
data frames, all on their first submission. Twenty numbered printf output
lines and a shell variable readback were complete. The first long rx_stats
output nevertheless contains `irq_frames=11 poempty=0`, where the unchanged
source emits `irq_frames=11 poll_frames=0 empty=0`: twelve characters are
absent from the decoded original raw stream. This is an actual remaining
TX/output observation, unlike RX41's corrected stdout-filter reports.
It does not identify whether the loss was in EUD TX, USB IN or the host path.
Zero stray and zero buffered bytes cannot detect dropped complete frames.

Repeating that status query in the same open session accepted all input but
triggered fault=4/watchdog=1. The last native frame was collected through
polling, and complete second status output reported frames=15, bytes=tty=182,
irqs=irq_frames=14, poll_frames=1, active=0, queued=0, with no bad header,
overrun or queue drop. F1 subsequently ran through polling and independently
reached fastboot; its new serial session needed five OUT attempts.

Source review shows the watchdog stops IRQ on its first observation of RX
pending. That observation alone does not distinguish a broken IRQ from an
IRQ which has not yet acquired the UART lock. The console holds that lock
with local IRQs disabled for an entire paced printk message, while tty TX
holds it for each frame. A race/latency explanation is plausible, unproved.
The current IRQ B diagnostic was retained unchanged. A future repair must
allow measured IRQ progress before declaring failure and keep bounded F1
fallback; it should not count a polling frame as an IRQ success.

The host native mode is a tested operational mitigation, not certification
of the physical cause, reliable arbitrary-length TX or exactly-once input.
