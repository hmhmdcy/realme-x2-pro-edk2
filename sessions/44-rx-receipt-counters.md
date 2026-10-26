# Session 44: missing-receipt boundary measured with RX counters

2026-10-09, Asia/Shanghai. Continues sessions 41-43. The RX41 whole-frame
payload method remains intact. Receipt stability is **not fixed** by this
session's diagnostic changes.

## Findings

The current diagnostic kernel counts every existing STATUS1 poll, pending
observation, rejected header, fully collected frame and tty byte insertion.
No extra hardware reads or writes were added. It exposes a read-only
`rx_stats` platform-device attribute, reachable through
`/sys/class/tty/ttyEUD0/device/rx_stats`. Ctrl-U also prints the counters in its
existing receipt, before delivery of that current byte; `tty_before` therefore
excludes it. This lengthens the Ctrl-U receipt and can affect TX timing around
that diagnostic. Normal multi-byte receipts and the 20 ms delayed-work interval
are unchanged.

| Capture | OUT / receipt | Device evidence |
|---|---|---|
| metrics-before | 3 / none | No visible response |
| native-a (`echo R44A\n`, LEN=10) | 1 / none | No response; next snapshot shows this was never collected |
| metrics-recovery | 2 / receipt | polls=7658, pending=1, bad=0, frames=1, bytes=1, tty_before=0 |
| native-b (`echo R44B\n`, LEN=10) | 1 / none | No response; next snapshot shows no extra pending observation or frame |
| metrics-after-b | 3 / receipt | polls=11415, pending=2, bad=0, frames=2, bytes=2, tty_before=1 |
| native-c-positive-control (`echo R44C\n`, LEN=10) | 2 / receipt | Exact payload, RX STATUS1 after=06060606, `R44C` output and shell prompt |
| metrics-after-c | 4 / receipt | polls=20574, pending=4, bad=0, frames=4, bytes=13, tty_before=12 |

All three snapshots have no_tty=0, overrun=0 and bad_id/bad_len=0. The second
snapshot adds only its own Ctrl-U: the failed B input and earlier failed
Ctrl-U attempts did not increment pending or accepted-frame counts. The third
adds exactly one successful native 10-byte frame plus its own Ctrl-U, with the
expected tty byte total. This is stronger than an absent console receipt alone:
these failed inputs did not reach a pending observation, header rejection or
tty delivery in this driver.

It does **not** distinguish an EUD/USB delivery failure from a pending state
that appeared and disappeared between polls. The counters do not sample the
bus continuously, and Windows Write/Flush is not a USB completion trace. RX43
separately established full-length status-zero libusb completions without a
device receipt. No BusyBox failure was demonstrated here.

## Source review and excluded repeats

See [source audit](../reference/rx44/source-audit.md) for fixed primary sources,
the vendor RX IRQ path and SPI 492, the limitations of that vendor COM code,
QUIC timeout semantics, USB completion/error documentation and OpenOCD's new
SWD-only implementation. Our nominal 20 ms polling versus the vendor interrupt
path is a concrete difference to investigate; it is not a proved cause.

RX timeout units/default/expiry behaviour remain undocumented. RX38 already
sent `02 ff ff 00 00` without a receipt on its subsequent probe. RX32 already
tried the vendor startup status write with a relaxed DAT burst before the
wait-state fix. Neither old run isolates today's missing-pending boundary.
This session does not repeat those register writes, PORT_RESET, PHY reset,
USB filter changes or force bind.

## Diagnostic setup and preserved state

Fresh PnP: 9501/9500/9505 OK, COM14, USBIPD 6-5 Shared, not Attached. A bounded
pre-change Ctrl-U missed once; a subsequent bounded recovery accepted its
second OUT. Every serial owner closed/disposed in finally.

Only eud.c changed. TOP_CFG=0x11/readback/restore, full DAT burst under the TX
lock, len=2 header-only F1, console, TX pacing and the compatible terminal are
retained. Actual DTS, rpmh, earlycon and existing backups were preserved.
Image was built incrementally. Packaging copied the RX41 FAT and replaced
only Image with mtools; extracted Image and DTB were byte-compared. Only
logdump was flashed; boot was not changed.

The first sysfs-only diagnostic accepted a native LEN=14 setup fragment, but
the next fragment's three OUTs produced no receipt. A compatible long query
stopped after five missing receipts for one byte; Ctrl-U then cleared the
partial line. Another bounded LEN=14 setup could not complete. These were
attempts to retrieve counters, not evidence that sysfs or BusyBox failed.
The Ctrl-U receipt was extended to make observation require only one byte.

| Artifact in E:\edk2-samurai-out | SHA256 |
|---|---|
| logdump-rx41-native-ordered-tty.img (unchanged base/rollback) | cdf0c1eb633c906f424dfd33c4d7757e1cc1bfe6edd88002127da4ebbdca477f |
| logdump-rx44-rx-stats.img (sysfs-only intermediate) | e41c2382b4f3e83cddbf1f1bcd08f17decb23d32741c2e9f1c8e55948c29a10f |
| logdump-rx44-rx-stats-ctrl-u.img (current diagnostic) | cefc82252e203e3bbb5a27b9b302c807d6d1ee82c49318ed2d6a54661660db9d |
| current Image | 937960d0754b92c8797404b7cdd9159a710b9897c6f2be576bd980d0bca0a87e |
| current eud.c | e17acbd5d6139c94c3e22f6d6bcd442186d3bd24e9292a10e29f3d5781970dd2 |
| unchanged actual init | e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab |
| unchanged actual BusyBox | 999cb969d09093a71716cfc747bb53cdada3f332c05eb5046c56e0f66a4d6d22 |

External `rx44/eud-before-rx44.c` and `Image-before-rx44` retain the RX41
source/Image. `eud-sysfs-only.c` and `Image-sysfs-only` retain the intermediate.
Logs and packaged copies are non-overwriting. The published driver matches the
actual current source; reference/rx44 contains raw fixtures and a verifier.

## Next investigation

Final F1 accepted its fourth bounded OUT; fastboot independently returned
`product: msmnile`. Rebooted the same diagnostic without flashing again.
Final boot again verified TOP_CFG=0x11/original zero and the tty shell.
A fresh Ctrl-U accepted its second OUT with pending=frames=bytes=1, bad=0,
tty_before=0, no_tty=overrun=0. COM14 closed/disposed; 9501/9500/9505 OK;
USBIPD 6-5 Shared, not Attached. This is a live diagnostic candidate, not a
stability fix. The persistent investigation goal remains active.

Continue from the missing-pending boundary, retaining the same successful
native payload method and the raw/counter comparison. Review the RX IRQ route,
mask semantics and bounded interrupt handling before changing reception.
The authoritative DTB is supplied by firmware, so editing only the FAT DTB
does not establish an IRQ resource. Prefer a justified logdump-only diagnostic
when feasible; only boot/logdump are authorized. Compare one variable with
the existing counters and require command output, console and F1 checks.
Do not claim reliability from a small set of successful retries.
