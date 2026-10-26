# Session 54: repeated console RX, console F1 and the next TX observation

2026-10-10 (Asia/Shanghai). Same RX53 candidate; no kernel or installed terminal
change, no flash, one F1/reboot of the same logdump. The overall stability goal
remains active because RX53's precise issued TX-frame loss is unresolved.

The live preflight found three EUD nodes OK, COM14 available, no known owner and
9505 Shared/not Attached. Driver/Image SHA matched session 53. Each USB session
uses one owner, manual steps and once-only data/F1 OUT, with dispose/detach in
finally. No new Windows administrator ETW; WSL root usbmon records target data.

## Repeated RX regression

The separate helper derives from the unchanged RX52 continuous-IN implementation.
It permits at most nine **manual** overlap steps, each with the unchanged 49-byte
`printf '<6>R51LOCK:%0990d:R51END\n' 0 >/dev/kmsg` command and one different
9-byte `R54H01=1\n` through `R54H09=1\n` input. LEN2 never carries tty data.
No automatic loop or retry; a missing probe would stop new data until manual sync.

All nine inputs receive `via=console` receipts and the shell reads back
`R54V=111111111`. Every log contains all 990 zeros. Actual marker-to-OUT intervals
are 152.645..153.104 ms; receipt delays are 716.793..726.297 ms. These are host
observations, not an IRQ latency measurement.

| Counter | Before | After |
|---|---:|---:|
| accepted frames | 25 | 87 |
| bytes / tty | 247 / 247 | 967 / 967 |
| IRQ frames / console frames | 25 / 0 | 78 / 9 |
| empty IRQ / credited console empty IRQ | 0 / 0 | 6 / 6 |
| poll frames, watchdog, bad, drops, fault | 0 | 0 |
| IRQ active / outstanding credit | 1 / 0 | 1 / 0 |

Nine overlaps do not degrade reception. **Only six empty IRQ entries occurred**;
this does not establish behavior under eight consecutive empty entries. Valid
IRQ/console receptions reset the streak. Do not induce an artificial storm or
call the global empty count a consecutive streak.

71 OUT transfers (70 data, one startup Ctrl-U), all complete once and receive
matching receipts. Raw is 33,910 bytes / 5,712 frames. Full target USB IN, read
events and raw match byte-for-byte, including a canceled read's six actual bytes
`90 04 5b 20 31 38`. A CRC-valid 512-frame snapshot, seq 12600..13111, matches
raw directly at frame 3644; CRC 50a225d8. Maximum sink queue is 2; drained, no
workers or errors remain. This is a passing regression window, not a TX fix.

## F1 through the console collector

A new bounded USB owner synchronizes once, submits the same log command, then
one **header-only** `90 02` at marker+152.678 ms, before the log ends. The raw
receipt is `eud: RX46 F1 via=console irqs=90 fault=0`, followed by
`eud: reboot2 bootloader requested`. Independent fastboot reports serial
62bc28a1, product msmnile. All six OUTs complete once; 2,731 IN bytes / 459 frames
match raw, with 990 log digits complete. No tty payload is sent with F1.

The reader sees USB errno 5 after the accepted F1 (usbmon final IN status -62,
zero actual bytes). Its owner closes/drains/disposes; finally detach reports
that old bus 6-5 no longer exists because the device has entered fastboot. This
is an expected removal, independently checked, not a missing data receipt.

The first preflight launch was stopped before attach: its owner-name matcher
saw the parent preparation command containing the helper filename. A separate
read-only check found no actual owner. Launching the reviewed wrapper alone
passed unchanged. No experiment or OUT occurred in that rejected preflight.

Rebooting the same RX53 image restores TOP_CFG=00000011, tty shell and IRQ active.
Passive boot capture sends zero OUT (8,956 frames, no stray/pending). The
unchanged installed native terminal then obtains its first Ctrl-U receipt and
one LEN14 `echo R54READY\n` receipt/output without retry; its finally closes
COM14. Default compatible mode and firmware code remain as verified in RX53.

## Actual Windows receive implementation and useful next measurement

[reference/rx54/source-audit.md](../reference/rx54/source-audit.md) retains
selected disassembly with the exact installed qcusbser 2.1.3.5 PE/PDB identity.
Open invokes input/output resets before starting read workers, consistent with
RX47's ETW. Worker creation is separate from the application's `Read` call;
single/array mode and live scheduling are not measured. Neither ordinary
BytesToRead polling nor a generic WDF example identifies the cause of seq 7287.

New specific observation: `SerialGetStats` (2b81c..2b97f) copies 24 bytes from
`pPerfstats` without clearing them. In `vPutToReadBuffer`, `ReceivedCount` is
incremented at 29795 **after** early refusal branches. This gives a possible
driver-buffer boundary to compare with raw and the software TX journal. It
does not count physical USB acceptance and cannot alone exclude a refused
block. The standard GET_STATS API was researched; **no live query has run yet**.

Next implement one bounded, read-only GET_STATS query on the existing diagnostic
owner's overlapped handle, without CLEAR_STATS, purge, reset, driver change or
another owner. Snapshot before startup/after a drained response and compare
modulo-32-bit received delta with exact wire-byte raw and the issued journal.
Retain queue/errors and timing. A matched byte count locates an observed gap
differently from a deficit; absent reproduction must remain inconclusive.
Do not infer a fix or replace the installed terminal based on this static audit.

## Artifacts, unchanged candidate and final state

Original files: `E:\edk2-samurai-out\rx54`. Reviewable export:
[reference/rx54](../reference/rx54/README.md); run its `verify.py`. Raw/bin and
executed helpers remain byte-exact; traces are lossless gzip, derived text UTF-8
LF. Exact driver binaries/PDB and phone images stay outside Git.

| Artifact | SHA256 |
|---|---|
| kernel driver, unchanged RX53 | 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4 |
| Image, unchanged 30,181,888 bytes | 33efc6bc0c1c2d7b82b80b39dc7cea2331d05cca2005376399dade92b1597952 |
| logdump-rx53-console-rx.img | 50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93 |
| installed terminal, unchanged | 9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57 |
| repeated helper | 48bad103de1b41705d194ad332d88038807f3724753379af3d233d6fc6fa74ce |
| F1 helper | 39d244978fdc6322bb0fbc3a1fdafc142ef31f5e3fe01c9c59b0bf08ed1bc3e5 |

Final state: all three nodes OK, COM14 closed, no known owner, 9505 Shared/not
Attached. Zero flashes; immediate rollback remains unchanged RX48 B. Boot,
DTB, initramfs, F1/console and the compatible/native installed terminal are
preserved. RX53's seq 7287 missing console prefix `[   ` remains the unresolved
TX evidence; this session neither repairs nor invalidates it. Publish only the
reviewed documentation/evidence to fork/master after the required health check.
