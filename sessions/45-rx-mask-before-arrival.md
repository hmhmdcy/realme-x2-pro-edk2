# Session 45: RX enable mask before arrival does not fix missing receipts

2026-10-09, Asia/Shanghai. Continues RX44's missing-pending investigation.
The verified TOP_CFG=0x11 and whole-frame payload fix is retained.
**Native terminal stability remains unresolved.** The mask candidate was
reverted; the final device and actual source/Image are RX44 again.

## Measured result

The diagnostic changed only INT1_EN_MASK (+0x24) before receiving input:
save the low-byte original 0x1c, write original|BIT(0)=0x1d, verify masked
readback, and restore on F1/remove/probe failure. It did not register an IRQ,
change the 20 ms polling interval, write STATUS1, change FIFO ordering or
alter TX pacing. Boot confirmed TOP_CFG=0x11/original zero and mask=1d/original
1c. The tty shell started normally.

| Capture | Host OUT attempts / receipt | Device evidence |
|---|---|---|
| mask-metrics-before | 3 / yes | polls=2847, pending=frames=1, bytes=1, tty_before=0 |
| mask-native-a, `echo R45A\n`, LEN=10 | 1 / none | Empty response capture |
| mask-metrics-after-a | 5 / yes | polls=4784, pending=frames=2, bytes=2, tty_before=1 |
| mask-native-positive, `echo R45B1234\n`, LEN=14 | 1 / yes | Exact 14-byte payload, s1_after=06060606, R45B1234 output and prompt |
| mask-metrics-after-positive | 1 / yes | polls=6327, pending=frames=4, bytes=17, tty_before=16 |
| mask-f1 | 2 / yes | Reboot receipt and independently verified fastboot product msmnile |

All metric snapshots have bad=no_tty=overrun=bad_id=bad_len=0. The snapshot
after failed A adds exactly its own Ctrl-U, no pending/frame/tty observation
for A or the missed Ctrl-U attempts. The next snapshot adds exactly the
successful 14-byte command plus its own byte. The software boundary is the
same as RX44 despite the persistent enable bit. **Enabling INT1 RX alone is
insufficient.** This run does not rule out IRQ reception or establish how
long pending remains visible. Windows Write/Flush is not a physical USB trace.

The mask boot has 13906 decoded frames and 8 stray bytes; record that
resynchronization explicitly, without attributing it to a proved cause or
calling the capture lossless. Native/control probes have zero stray and no
incomplete bytes, but that alone does not prove lossless TX.

## Why this was a distinct experiment

Read [source audit](../reference/rx45/source-audit.md), the RX44 source review,
and session 33 before further hardware work. Session 33 changed both INT0
and INT1 after seeing an incoming pending frame and used delayed DAT reads
before the wait-state fix. It tested payload advancement, not persistent
mask-before-arrival delivery with counters. Here only INT1 changed before
arrival; the repaired full-frame method and software counts stayed intact.
No startup STATUS1 write, timeout command, PORT_RESET, PHY reset, USB filter
change, force bind, DAP mux switch or fuse access was repeated.

The matching vendor DT routes EUD to GIC SPI 492 level high. The actual
mainline node has no IRQ property, so this mask-only run cannot test IRQ
delivery. The next useful comparison is a bounded actual IRQ receiver with
IRQ-entry counters, safe fault fallback and process-context receipt/tty/F1
handling. Verify that route before interpreting an absent IRQ. The firmware
configuration-table DTB is authoritative; merely changing the FAT DTB is
insufficient. Prefer a justified logdump-only diagnostic.

## Build, scope and restoration

Live state was checked first: 9501/9500/9505 OK, COM14, bus 6-5 Shared and
not Attached. A fresh baseline Ctrl-U accepted one OUT; baseline F1 accepted
its fourth OUT and fastboot independently returned product msmnile.
Every serial owner closed/disposed in finally. All probes were manual,
bounded and used unique capture paths. No automatic multi-experiment loop.

Only logdump was flashed for the candidate and return to RX44. Both flashes
were successful. Boot was unchanged. Incremental Image build preserved actual
initramfs and all existing Linux changes. Packaging copied the RX41 FAT and
replaced only Image; extracted Image and DTB were byte-compared. The build
succeeded with one boot-log format warning, documented alongside the exact
tested candidate in reference/rx45/README.md. The candidate is not the current
driver; its tested source and warning are retained honestly for audit.

After mask F1/product verification, RX44 was flashed back. Its original
source and Image were also restored byte-for-byte from backups. Final boot:
13904 frames, zero stray/incomplete bytes, TOP_CFG=0x11/original zero and
shell started. Final Ctrl-U accepted one OUT: polls=4430, pending=frames=bytes=1,
tty_before=0, all bad/no_tty/overrun fields zero. COM14 closed/disposed;
9501/9500/9505 remained OK. F1, console and the compatible host terminal
remain available. No native reliability certification is claimed.

| Artifact in E:\edk2-samurai-out | SHA256 |
|---|---|
| logdump-rx45-rx-mask.img, excluded candidate | 015204912e6bde13a5406d66840aa50493b90f442b57895b53e42dfaf9be36b3 |
| rx45/Image-mask-candidate | d142d0daa8474778ca0ec8aad9f48b1268789371de776fd9347eb40adcdc4dff |
| rx45/eud-mask-candidate.c | a4a51107234b38140e2e64dfd79f665af97e9f5aa5689748207c5a769fae9b2c |
| logdump-rx44-rx-stats-ctrl-u.img, restored live diagnostic | cefc82252e203e3bbb5a27b9b302c807d6d1ee82c49318ed2d6a54661660db9d |
| restored actual Image and rx45/Image-before-rx45 | 937960d0754b92c8797404b7cdd9159a710b9897c6f2be576bd980d0bca0a87e |
| restored actual eud.c and rx45/eud-before-rx45.c | e17acbd5d6139c94c3e22f6d6bcd442186d3bd24e9292a10e29f3d5781970dd2 |
| unchanged actual init | e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab |
| unchanged actual BusyBox | 999cb969d09093a71716cfc747bb53cdada3f332c05eb5046c56e0f66a4d6d22 |

The evidence verifier checks raw hashes, exact counter deltas, native output,
F1/product, logdump-only flashes, baseline return and source identity. The
persistent investigation goal remains active. Do not retry the same mask-only
candidate as a proposed stability fix.

## User question: which EUD features are fused off?

CTRL and COM are usable on this unit. SWD/JTAG USB transport works but the
tested AP DAP does not answer; TRACE remains unvalidated. No fuse values were
read, so neither this failure nor FREEZIO proves a specific programmed fuse.
The old HANDOVER sentence asserting APPS_DBGEN_DISABLE was corrected.
The researched policy/access limits and practical implications are maintained
in [SWD-JTAG.md](../SWD-JTAG.md). No demonstrated unlock method for this unit
was found. Another EUD peripheral could provide an instrument if permitted;
it does not itself repair COM or make a SoC TRACE sink a USB bus analyser.
