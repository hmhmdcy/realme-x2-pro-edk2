---
<!-- from HANDOVER-NEXT.md, section 29 (extracted 2026-10-08; full original:
     archive/HANDOVER-NEXT-full-2026-10-08.md) -->

## 29. EUD COM console, tty and command channel (2026-10-08) - measured

> Historical bring-up record. The current protocol is 0x90/length 1 for real
> tty input and length 2 for F1. Consecutive payload reads remain unverified;
> do not treat the older FIFO-pop interpretation below as the current result.
> See sessions 32/33 and linux-port/docs/EUD-TERMINAL.md for current operation.

### 29.1 What the hardware really does

Host to device framing, verified byte by byte on this unit:

    write  [id][len][payload...]   (one USB transfer, e.g. 81 05 "world")
    read   0x0c -> id     LATCH: the last message's id; re-reading does not pop
           0x10 -> len    LATCH: the last message's len
           0x14 -> payload FIFO: every read pops one payload byte, `len` times

Evidence: with the host writing [90][08]"PAYLOAD!" every 5 s, a probe that dumped
the window 0x0c..0x60 whenever the latches changed printed

    eud: C id=90 len=08 dat=50 window ... 14:50505050 ... 40:02020202 44:07070707
    eud: C id=90 len=08 dat=41 window ... 14:41414141 ...

0x50 is 'P' and 0x41 is 'A': the payload comes out of 0x14, one byte per read.
This also explains the earlier confusion - the header "changing with every
message" was the host's write updating a latch, not the driver draining a FIFO.

Other registers: INT_STATUS_0 (0x40) reads 0x00000000 when idle and 0x02020202
while data is pending; INT_STATUS_1 (0x44) goes 0x06060606 -> 0x07070707 (BIT(0));
neither is a reliable "data pending" flag (a phase that read only the status
registers while the host kept writing saw them constant).  INT1_EN_MASK reads
0x1c1c1c1c, INT0_EN_MASK 0, CSR_EUD_EN 0x01010101, 0x60 0x0b0b0b0b (undocumented).
Every readback replicates the low byte into all four lanes (0x81 -> 0x81818181).

Device to host (TX) is the same idea in reverse and was already known: one
register write is one FIFO entry, so the device writes [ID=0x90][len][data...]
and the host reassembles [0x90][len][data] frames.

### 29.2 Three bugs found on hardware (all fixed)

1. Two writers on one small FIFO.  The firmware boots with
   "earlycon=eud,... keep_bootcon", so the early console stays registered; an
   unconditional register_console() made every printk go out twice and the two
   writers interleaved byte by byte (every character arrived doubled).
   Fix: register the real console only when the command line asks for it, and
   drop keep_bootcon in the firmware command line.
2. No TX pacing.  eud_earlycon.c used INT_STATUS_1 BIT(1) as flow control, but
   that bit reads back stuck-at-set here, so frames went out at MMIO speed and
   whole frames were dropped (four bytes missing in the middle of a log line).
   Fix: fixed timing, 200 us per register write and 2 ms per frame, the numbers
   the EDK2 port had already measured on the same FIFO.
3. Short-lived writers lost their bytes.  "echo x > /dev/ttyEUD0" closes the port
   at once and ops->shutdown() cancelled the paced workqueue before it ran.
   Fix: drain the transmit kfifo synchronously in eud_shutdown().

### 29.3 The driver

Kernel side is drivers/tty/serial/eud.c (a copy lives in
E:\edk2-samurai-out\eud-v3-verified.c):

* a real uart driver, dev_name "ttyEUD", one port, custom type 124, TX through a
  workqueue with the pacing above;
* a 20 ms RX poll that follows the header latch and reads the payload from 0x14;
* struct console "eud" with .device = uart_console_device, registered only when
  the command line asks for it, so /dev/console binds to ttyEUD;
* command channel [0x81][len][payload]: payload[0] is the command code
  (0x01 ping, 0x02 register dump, 0x03 status);
* typing [0x82][len][payload]: the payload is fed to the tty with
  uart_insert_char(), so a shell on /dev/ttyEUD0 can be driven from the PC.

### 29.4 Verification runs (all on this phone)

* tty and console: the initramfs writes "[[TTYBANNER-OK]]" to /dev/ttyEUD0 and
  the host received exactly that string through the driver (not through printk).
  After the firmware change the boot log shows
  "printk: legacy console [eud0] enabled" followed by
  "printk: legacy bootconsole [eud0] disabled", and a typed
  "echo CONSOLEW >/dev/console" came back on EUD.
* command channel: [0x81][0x01] -> "eud: pong", [0x81][0x02] -> full register
  dump, [0x81][0x03] -> "eud: polls=... reports=... last_status=...",
  [0x81][0x07] -> "eud: unknown command 7".
* typing: "echo EUD2-OK", typed as one character per frame, was executed by the
  shell on /dev/ttyEUD0 and its output came back to the host.
* log quality: a 210 s capture reassembles with 0 resyncs (about 15k frames).

### 29.5 Still open

* Reading 0x14 blindly wedges the EUD COM block: the console goes silent while
  the EUD control device (9501) and COM14 stay up, and only a full power cycle
  brings it back.  The payload image did this right after the first host frames
  (see 29.6).  Next iteration: read 0x14 exactly `len` times, only once per
  header change, with `len` validated to 1..16, and never touch 0x14 otherwise.
* While the header-only protocol is in use, input characters can still be lost
  ([0x82][char] carries no payload); the payload protocol should remove that
  once the read is safe.
* The status bits are not trustworthy, so "data pending" is inferred from the
  header latch changing.

### 29.6 Note on the wedged state

After flashing logdump-payload.img the phone booted, the console streamed
normally to about kernel time 20 s, then the host wrote a few frames and the
console went silent.  A full power cycle restored it, so this is an EUD hardware
state rather than a kernel crash.  Do not conclude "the kernel is broken" before
trying a full power cycle.
