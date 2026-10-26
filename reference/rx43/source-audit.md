# RX43 source and actual userspace audit (2026-10-09)

Purpose: separate USB submission, device RX, tty delivery and visible output.
Hardware results and the corrected RX41 conclusions live in
[session 43](../../sessions/43-native-terminal-evidence-audit.md).

The actual build is `/home/cy122/x2pro-linux/linux`; its current local commit
is e42788eaf, with the previously recorded working-tree modifications retained.
The active EUD source and built Image still match RX41:

| File | SHA256 |
|---|---|
| drivers/tty/serial/eud.c | 425a22c6b08da820f946aa269d9d5cd141ae181d5d73dde71ec3cdb2d8e7628b |
| arch/arm64/boot/Image | def8528ac0522c30cee6f5008ea6bb4b171514f6cf5d5c6cefbf185686c752c4 |
| drivers/tty/serial/serial_core.c | 2053931aef71c605f85bb9c8406dd3f8f2c29ce353b76297425f8c013f2ffe0c |
| drivers/tty/tty_buffer.c | 6a4177ae3040469cb56960b6cdcd76464f8121a01dd16c78478addc05ebf9c0d |
| drivers/tty/n_tty.c | 5f33bf3bca249d246c2bbf85f7852e77dd65dc14e57a135a83fa03adb9dda0a9 |
| actual initramfs/init | e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab |
| actual initramfs/bin/busybox | 999cb969d09093a71716cfc747bb53cdada3f332c05eb5046c56e0f66a4d6d22 |

## RX and tty

eud_rx_work polls every 20 ms after startup. The shared uart lock covers
STATUS1, ID, LEN and all DAT reads. Only STATUS1 bit 0 opens the RX path;
invalid IDs/lengths produce no receipt. The complete payload is cached before
printk and tty insertion. This round does not weaken that gate, split native
input, change the wait state, or add an unverified acknowledge register write.

tty_insert_flip_string supplies normal flags and returns the inserted count;
tty_flip_buffer_push schedules line-discipline work asynchronously. The
kernel's tty_buffer flush_to_ldisc and n_tty receive/read paths separate this
insertion from userspace reads. A successful insertion alone is not command
execution. New echo/dmesg/console responses do prove execution in their samples.

The failed Windows echo A has no receipt in the later complete dmesg tail,
although its preceding and following Ctrl-U receipts are present. It did not
reach this driver's accepted-frame log in the audited interval. This excludes
a mere host display omission for that sample, but does not distinguish USB/EUD
reception from STATUS1 gating or invalid-header rejection. There is no physical
USB bus capture, IRQ trace or idle-header telemetry in this round.

## Actual shell and BusyBox

CONFIG_INITRAMFS_SOURCE points at the actual WSL initramfs. Init mounts proc,
sysfs and devtmpfs, redirects boot diagnostics to /dev/kmsg, then launches
`sh -i` with stdin/stdout/stderr on /dev/ttyEUD0. It prints an independent
console banner. The shell reports that job control is unavailable; ordinary
echo and pipelines were demonstrated on hardware.

The actual binary reports BusyBox 1.37.0, built 2026-01-10. For source comparison
we retrieved the [official 1.37.0 release archive](https://busybox.net/downloads/busybox-1.37.0.tar.bz2),
not proof of this binary's original build configuration or absence of vendor
patches. Exact release files examined: libbb/read_key.c, libbb/lineedit.c and
shell/ash.c. Archive SHA256:
3311dff32e746499f4df0d5df04d7eb396382d7e108bb9250e7b519b837043a4.
read_key.c SHA256:
346fd6c6f197348a673a3db2bfbe177f51b35f81ba80c0ed68b40223d3c43cad.
lineedit.c SHA256:
db9c0969787af3995f96bdde53527d5aca5c5f8b0397c3be8045b46a2631ff93.

The release read_key reads ordinary input one byte at a time to avoid reading
past a pasted newline. Cursor-position replies require an ESC sequence;
lineedit does not discard ordinary ASCII merely while its cursor query is
outstanding. It uses TCSANOW for entry/restoration, rather than flushing input.

[qemu-pty-check.py](qemu-pty-check.py) runs the actual initramfs binary, with
the same unavailable job control and no reply to ESC[6n. A single 15-byte PTY
write executes echo OFFLINE43 and returns the output and prompt. Its active
line-editing ICANON/ECHO/ISIG flags are false. This is an offline shell check,
not an EUD transport measurement. The hardware stty -a command sees the
restored canonical/echo settings while the command executes; these two
observations are consistent with temporary raw mode during line editing.

## TX and host capture

serial_core uart_write queues bytes in xmit_fifo and invokes start_tx.
eud_start_tx schedules tx_work; each worker frame carries at most four bytes.
The worker, console_write, shutdown drain and RX DAT burst share the port lock.
The existing 200 us/write and 2 ms/frame pacing is unchanged. A concurrent
console printk can interleave with tty text at frame boundaries; initial
banners and shell messages visibly do this. Zero stray bytes only validates
framing, not complete TX delivery.

The host terminal saves unfiltered raw/text/events, filters diagnostics and
ESC[6n only for display, and sends ASCII via its compatible one-byte protocol.
It is unchanged. In contrast, decode-eud-capture.py had printed only eud:
lines to stdout while writing all text to its .txt file. That filter concealed
real command responses in RX41's review. It now prints the complete decoded
capture. eud-step now saves text/events directly, refuses existing captures,
validates complete native frames and reserved F1, and offers a bounded tail.

## USB comparison boundary

The local QUIC source is commit 693741a3b0448690402539ed0e6af067510e386f.
Its [COM definitions](https://github.com/quic/eud/blob/693741a3b0448690402539ed0e6af067510e386f/inc/com_eud.h)
and framing were rechecked. RX43 libusb uses the existing eud-usb-step helper:
bulk OUT 0x02 / IN 0x81, max packet 16, read-size 16, no setup command, reset,
ZLP or filter change. usbmon captures the virtual WSL controller's URBs.
All three echo B OUTs completed with status 0 and length 12; one fresh device
receipt followed the third. Another three completed stty OUTs had no receipt.
Thus qcusbser is not necessary for missing receipts on the repaired RX41
configuration. The trace does not identify which physical transfer the device
accepted or prove USB-level ACKs. Retry delivery remains unsequenced.
