# RX60 even-IN reversal — defined before execution

Previous goal turn: PROGRESS. RX59 forced 75 short IN / two short OUT, then
ordinary reopen reproduced CRC-proven TX seq12407 loss. Matching driver log,
ReceivedCount and raw miss six bytes; matched ETW has no failed positive IN.

This reversal preserves the RX59 COM14 driver, phone image and frozen RX55
diagnostic. Same two temporary logging values, exact leaf enable/restore reloads,
same 64 MB ETW providers, same 300-second helper and 60/100-second owners with
total capture <=180 seconds. Continuing human authorization covers this scope.
No flash, phone reboot, driver installation, fuse/PHY/clock or additional reset.

First owner: require first-attempt Ctrl-U receipt. Observe startup frame count.
If even, manually send abc once (expected 20 more IN frames); if odd, send abcd
once (expected 21 more). No newline or command execution. Require actual final
IN count to be even, two short OUT requests only, all input drained. Aim for
similar manual timing to RX59 (data around 22 seconds, close around 40 seconds),
within the 60-second bound. No forced delay loops or repeated test data.

Second owner: ordinary reopen, startup Ctrl-U clears incomplete text. Measure
first-status prefix and initial ReceivedCount. Only sync may retry. Freeze one
3120-byte journal with dd bs=4096 count=1, base64 export, drain, Ctrl-P/Ctrl-].
Both serial owners finally close/dispose/detach; helper finally stops ETW and
restores both original absent values. Stop and preserve the attempt if any
precondition fails. Never retry a data frame to obtain a passing result.

Prediction recorded before execution: even-IN transition restores the first
TX frame while the preceding two-short-OUT transition accepts first Ctrl-U.
Physical DATA0/1 is still unmeasured; this is one reversal, not a failure-rate
estimate or a final repair. Full-packet OUT/ZLPs occur only later during journal
export and are accounted for separately.
