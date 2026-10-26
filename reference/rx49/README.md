# RX49: complete USB IN comparison and a real partial cancellation

See [session 49](../../sessions/49-usb-in-and-partial-timeout-audit.md) and
[source audit](source-audit.md). RX48's kernel/Image, TOP_CFG=0x11, whole-frame
RX, console/F1 and installed terminal are unchanged. No phone flash/reboot
or new Windows administrator trace was performed.

Seven historical traces were compared offline with their unchanged raw
files. A new manual continuous libusb owner printed 60 complete numbered
lines, recovered a CRC-valid 512-record TX journal and returned 11,066
bytes, identical to complete target usbmon IN data. One canceled IN had
six real bytes and the installed PyUSB backend preserved them.
These are virtual HCD/software boundaries, not physical packet/ACK proof.
No old TX loss or IRQ grace wait branch was reproduced; stability remains open.

Raw/bin/usbmon and executed Python sources are byte-identical exports;
other text has normalized UTF-8/LF/trailing whitespace. `exports.json`
retains original/exported hashes, and `SHA256SUMS` protects all exports.
The first helper's source is reconstructed from the display-only fix;
its SHA matches the source hash measured before that run. Both its raw
and its display error are retained. No bytes are repaired.

`python3 verify.py` independently checks input totals, receipts, output,
whole IN streams (including nonzero-status data), journal CRC/frame
window, resource closure, historical file hashes and final enumeration.
`eud-usb-session.py` is a bounded diagnostic helper, not a replacement for
the installed Windows terminal. It requires an already attached 9505 and
readable usbmon; it never binds, resets or reconfigures a device.
