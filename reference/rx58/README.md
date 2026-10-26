# RX58: first-frame association and exact failed-read gates

2026-10-10. See [session 58](../../sessions/58-reopen-first-frame-and-driver-completion-gates.md).
Read-only replay establishes that the three CRC-proven TX gaps are the first
console timestamp frame of the first Ctrl-U status in reopened Windows owners.
RX53 accepted its first sync, so startup RX loss is not required for a TX gap.
All other 511 records match directly; RX57 remains a passing contrast.

Exact installed PE/PDB checks identify the error logger's missing payload/length
and the later status gate that skips vPut insertion. L2 still forwards status
and length; the newly bound indirect callback reaches ReadIrpCompletion. No
fault-time failed partial read is measured, so this is a candidate, not a fix.

The new ETW/logger plan is prepared and mocked only, awaiting a separate single
UAC authorization. No COM open, registry/PnP change, attach, build, flash or
phone reboot occurred in this session. Both old RX57 UAC attempts were used.
Helpers retain external paths and one-use guards. Do not run this evidence copy
or treat stored plans as authorization. Full PE/PDB, mocks and all-device traces
remain outside Git. Existing terminal/driver/image and two absent settings stay
unchanged; see readonly-state.json.

Run `python3 verify.py` here. It validates checksums, replays the original
cross-sample comparisons and checks exact excerpt machine bytes, callback
binding, mocked failure results and unexecuted read-only baseline. Replay needs
the existing rx51/rx53/rx54/rx55/rx57 evidence alongside this directory.
