# RX54: console RX/F1 regressions and exact host-counter audit

The unchanged RX53 candidate accepts nine manually triggered console-overlap
inputs, reads back all nine assignments, keeps IRQ active/fault=0, and handles
six credited empty IRQ observations. Eight consecutive empties were not induced.
All 71 OUTs complete once and receive matching receipts; full IN/events/raw and
a CRC-valid 512-frame TX snapshot match directly.

One console-source header-only F1 during the same log enters independently
verified fastboot. Its six OUTs and all received IN/raw match. Expected removal
follows the console F1 receipt; owners drain/dispose/detach in finally. One
same-image reboot restores Linux and an unchanged native terminal's fresh
receipt and echo. No flash or new Windows administrator ETW.

Selected exact-installed-driver disassembly adds the read-worker entry path and
the read-only `SerialGetStats` buffer-count boundary. GET_STATS has not run on
hardware. It is a concrete next observation, not a root-cause claim. RX53's
missing issued TX seq 7287 remains open; a passing regression is not a TX fix.

Run `python3 reference/rx54/verify.py`. The two analyzers check raw framing,
once-only commands/receipts, counts, exact IN/OUT, cancellation actual bytes,
F1 provenance/fastboot and direct journal matching. Verification checks the
unchanged source/Image/terminal identity and restored boot evidence.

`exports.json` retains original/exported SHA. Raw/bin and executed helpers are
byte-identical. Derived text is UTF-8 LF; gzip traces decompress to the exact
original. Images/driver/PDB stay external. See
[session 54](../../sessions/54-console-rx-regression-and-host-counter-audit.md)
and [source audit](source-audit.md).
