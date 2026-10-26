# RX47: continuous native terminal, reopen comparison and remaining faults

See [session 47](../../sessions/47-native-terminal-session-boundary.md) and
[source audit](source-audit.md). TOP_CFG=0x11 and RX46 IRQ B are unchanged.
No flash or new administrator trace was performed. Only the host terminal
script was changed: optional `-Native`, startup Ctrl-U synchronization, one
open port, payload lengths 1 or 3..14 and no data-frame retries.
The default one-byte compatible terminal remains available.

Raw files are byte-identical copies from `E:\edk2-samurai-out\rx47`.
Derived text/events and helper scripts have normalized UTF-8/LF/trailing
whitespace for Git; their unchanged external source hashes are recorded in
`exports.json`. No raw data are repaired. `SHA256SUMS` protects the exported
evidence and source snapshots. Full all-device ETL/XML stay local.

`python3 verify.py` checks exact native payload receipts and command results,
startup-only retries, reserved length-2 avoidance, counter deltas for failed
reopened inputs, compatibility, reboot, F1 and the actual TX text loss and
watchdog fallback. Passing means the described observations are consistent;
it does not mean terminal stability is solved. Especially, zero resync bytes
does not rule out dropped complete TX frames.

`export-etw-controls.py` exports only the reviewed target endpoint controls
from the existing RX46 trace. XML retains complete Event elements; JSON
provides a convenient field projection. DATA0/DATA1 remains unmeasured.
