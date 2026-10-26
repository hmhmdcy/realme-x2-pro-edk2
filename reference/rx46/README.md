# RX46: real IRQ reception works, but a missing command adds no IRQ

2026-10-09. See [session 46](../../sessions/46-rx-irq-and-host-trace-boundary.md)
and source-audit.md. Native terminal stability remains unresolved.

The diagnostic maps the vendor's GIC SPI 492 to hardware ID 524, requests
an initially disabled IRQ, and enables only INT1 RX after the existing boot
delay. Whole frames are cached under the TX lock in hard IRQ context;
receipts, tty delivery and F1 run in work context. A 20 ms watchdog can stop
IRQ and fall back to polling. None of the measured successful frames used
fallback; its exceptional paths were reviewed, not exercised on hardware.

Raw and usbmon captures, libusb metadata/events and the exact candidate
sources are byte-identical exports from E:\edk2-samurai-out\rx46. SHA256SUMS
protects those files. Derived Windows text/events and build logs have LF
line endings and trimmed trailing whitespace; originals remain external.
usbmon records virtual WSL host-controller URBs, not physical bus packets.

`python3 verify.py` checks real IRQ-frame counts, the missing Windows C
command's absent IRQ/pending/frame/tty observation, exact native outputs,
full-length status-zero libusb completions, F1, reboot and final diagnostics.
It cannot prove why a frame lacked an IRQ or certify reliable native input
or lossless TX. Zero stray is only a framing result; some receipt timestamp
prefixes are incomplete.

First Image's initial native A receipt includes a deprecated system_wq
warning. The current B Image uses system_percpu_wq, matching the existing
schedule_delayed_work wrapper; its measured receipts do not have that new
warning. Both final builds have no compiler warnings. The earlier API-name
compile failure was fixed before flashing and is retained as build history.
Existing earlycon/ioremap boot warnings are not described as resolved here.

Current diagnostic source is linux-port/eud.c, matching
eud-irq-candidate-b.c. Rollback remains the unchanged RX44 Image/source.
The new eud-etw-step.ps1 was syntax-checked and used for one user-authorized
administrator capture after the standard-user ETW start was denied. Echo
succeeded on its first OUT; the counter query sent two OUTs with one receipt.
Three target UCX OUT completions have lengths 12/3/3 and status zero, while
only echo plus one Ctrl-U adds IRQ frames. Original OUT payload bytes remain
unverified by ETW. Serial and owned trace were closed/stopped and independently
checked. A failed launcher prefix collision preceded the actual capture.

All-device ETL/XML stay external. export-etw.py selects only the reviewed
target rundown/endpoints/OUTs plus trace header; etw-eud-summary.json stores
source hashes and completion evidence. No non-target USB payload is exported.
There are 25 raw capture sets including pre-trace and ETW serial probes.
The exported ETW manifest has normalized UTF-8/LF text for Git; its unchanged
external original's SHA256 is also recorded in the ETW summary.
