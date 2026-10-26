# RX55: reproduced issued TX gap and accepted-buffer receive counts

One bounded, manual Windows owner on the unchanged RX53 candidate captures a
new missing console frame, seq 7376 / `90 04 5b 20 31 36`. The CRC-valid journal's
other 511 records directly match 27 previous-owner and 484 current-owner frames.
First status is 309 raw wire bytes versus 315 issued bytes. GET_STATS's accepted
receive delta is also 309, placing the gap before that counter rather than
solely in application reading/decoding/display. Physical USB/EUD/early driver
refusal are not distinguished. Startup Ctrl-U still requires its second attempt;
nineteen once-only data frames succeed. This session adds observation, not a fix.

`python3 reference/rx55/verify.py` checks raw decoding, saved reads, native
receipts/once-only commands, modulo-32-bit drained deltas, exact 24-byte output,
journal CRC/direct matches and final preservation/closure. The prior matching
tail is read from immutable `../rx54/restored-native.raw`. No hardware action
is performed by verification. Timeout/cancellation retention branches remain
unexercised; no fault is manufactured to test them.

Executed helpers/raw/bin remain byte-identical. `exports.json` retains original
and exported SHA; derived text is UTF-8 LF. No images or third-party driver/PDB
are included. The installed terminal is unchanged; the separate diagnostic
borrows its own existing .NET serial owner with an isolated OVERLAPPED event.
Read [session 55](../../sessions/55-windows-perf-counter-and-reproduced-tx-gap.md)
for primary API sources, source-boundary limits, the corrected read-only path
mistake, original startup failure and next steps.
