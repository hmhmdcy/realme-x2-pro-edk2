# RX53: service whole RX frames during console output

One logdump-only candidate adds a bounded RX check before/after complete console
TX frames, using the existing shared-lock whole-frame collector. RX waits in the
software queue; receipt, tty and F1 execute later in work context. It records
`via=console` and separate console counters, and credits at most one empty IRQ
after console consumption. Startup, TOP_CFG=0x11, header-only F1 and TX pacing
are preserved. The source and exact build/flash hashes are archived here.

| Evidence | Continuous USB | Windows diagnostic |
|---|---:|---:|
| Same 1009-byte kmsg and one 7-byte overlap input | accepted | accepted |
| Probe receipt delay | 713.159 ms | 607 ms |
| Probe RX/tty, source | 7 bytes, console | 7 bytes, console |
| Readback after clearing/fresh boot | R51H=1 | R51H=1 |
| Log zero digits | 990 | 990 |
| CRC-valid snapshot, direct TX/raw matches | 512/512 | 512/512 |
| IRQ enabled, faults/drops | 1, 0/0 | 1, 0/0 |

USB IN/raw match byte-for-byte, including six bytes in a canceled IN completion.
The installed native and compatible terminals work, F1's first candidate OUT
enters fastboot, and the same candidate reboots successfully.

**Stability is still unresolved.** The final installed native terminal loses the
first four-byte status prefix `[   ` at journal seq 7287. An immutable snapshot
matches 151 last-boot frames, then 87 affected-owner frames and 273 later USB
frames directly; only that one issued console frame is absent. Command, receipt
and output complete. This is a TX fault, separate from the successful overlap
RX improvement. EUD/physical USB/Windows receive localization remains open.
Repeated overlaps past the eight-empty-IRQ fault threshold and console-source
F1 still need focused regression checks; do not mark the overall goal complete.

Run `python3 reference/rx53/verify.py`. The three analyzers independently audit
counter boundaries, once-only writes, exact commands, complete raw and journal
CRC/direct comparisons. The Windows reader audit retains RX51's strict checks,
adding repeated CR-before-LF normalization for derived text; original raw is
unchanged. No interpolation/edit-distance fills missing frames.

`exports.json` gives original/exported SHA. Raw/bin/executed helpers/source retain
original bytes. Derived text is UTF-8 LF; target traces are gzip (mtime=0), with
byte-identical decompression. Images and third-party binaries remain external.
Rollback is unchanged `logdump-rx48-tx-journal.img`. See
[session 53](../../sessions/53-console-boundary-rx-service.md).
