# RX57: built-in driver raw logger, measured before serial-buffer acceptance

2026-10-10. See [session 57](../../sessions/57-driver-raw-logging-boundary.md).
One initial setup failed before COM open because the local PnpDevice PassThru
returned a device object. Its original scripts/status are preserved; independent
state proves the two temporary values were removed. A separately approved retry
corrected the output interpretation and captured one bounded owner successfully.

The new observation works: driver successful-read bytes, received counter and
app raw agree at 9550 bytes; all 512 issued journal frames directly match across
55 previous / 457 current frames. The old startup/TX loss did not recur. This
is a measurement method, not a stability repair or physical USB/PID/ACK proof.
Logging can affect timing; complete file parsing alone is not a losslessness proof.

Temporary settings were removed and the exact COM14 instance reloaded, serial
and diagnostic probes closed, helpers exited, three nodes OK, no owner or USBIP
attachment. Phone image/driver source/Image/installed terminal are unchanged.
Original binary driver logs, raw capture, journal and executable helpers retain
their bytes; exports.json records provenance. Derived disassembly is UTF-8 LF.
Full PE/PDB, phone image and synthetic/mock fixtures stay outside Git.
Original capture text/JSONL are marked binary for Git to preserve their CR/LF
and terminal whitespace; they remain readable files. Source/code whitespace
checks still run normally.

Run `python3 verify.py` here for offline hash/dependency/code/capture/state checks.
The unchanged three diagnostic dependencies live in ../rx55. Administrative
launch/capture helpers retain original external paths and one-use attempt guards;
do not launch them from this evidence copy. Both approved UAC attempts were used.
No further admin capture or device reload is authorized by the stored scripts.
