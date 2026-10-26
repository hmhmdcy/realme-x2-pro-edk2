# RX52: same-owner busy-console RX loss and continuous USB IN comparison

Current image stays RX48 B. No phone flash/reboot, driver edit, installed-terminal
replacement or new Windows administrator ETW capture. Linux usbmon uses the
existing WSL root route; only target bus/address records are archived.

Two manual USB sessions use the same 1009-byte kmsg write and one 7-byte input,
152 ms after a timestamped kernel marker. A is the RX49-style read/save/display
loop; B puts read completions in a queue and saves/decodes/displays in a separate
sink. Both submit data once and, after this probe's four-second timeout, keep
capturing until a manual Ctrl-U receipt restores synchronization in the same
owner. No control transfers occur in either recorded interval.

| Evidence | A: serial read/sink | B: continuous read, separate sink |
|---|---:|---:|
| Complete IN bytes = raw | 13220 | 13245 |
| Positive IN completions | 2220 | 2225 |
| Probe OUT submission/full successful completion | 1 / 1 | 1 / 1 |
| Probe receipt / accepted RX or tty bytes | absent / 0 | absent / 0 |
| Additional empty IRQ before same-owner recovery | 1 | 1 |
| Long log zero digits, expected 990 | 982 | 990 |
| Snapshot frames present, out of 512 | 510 | 512 |
| Largest body IN completion-to-next-submission gap | 8423 us | 854 us |

This reproduces missing RX without reopening or using qcusbser. The observer
change improves the IN gap and TX result in one comparison, while RX still fails.
It does not establish a physical USB ACK, measured IRQ delay, a universal TX cause
or a stability fix. A's two missing console frames contain identical `0000`;
their exact sequence positions are ambiguous. The analyzer compares collapsed
run counts with unique prefix/tail anchors, without filling or guessing gaps.

`summary.json` and the two journal binaries are derived from the immutable raw
and trace. `analyze.py` independently audits complete OUT/IN/raw accounting,
counter/receipt boundaries, the exact commands, CRC and journal match. Run:

```text
python3 reference/rx52/verify.py
```

Raw, binary snapshots and executed Python helpers retain original bytes. Derived
text is UTF-8 LF. Target traces are gzip with mtime=0; decompression must reproduce
the original trace SHA. `exports.json` records original/exported SHA; `SHA256SUMS`
covers every archived file except itself. No full third-party source or binary is
published. See [session 52](../../sessions/52-same-owner-usb-overlap-and-continuous-in.md).
