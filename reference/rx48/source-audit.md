# RX48 source and observation boundaries

The actual kernel is `/home/cy122/x2pro-linux/linux`; the kernel source
revision and previous tty/console audit are recorded in sessions 43/47.
Only the EUD driver was changed for the two RX48 builds.

The [official generic IRQ API documentation](https://docs.kernel.org/core-api/genericirq.html)
describes `irq_get_irqchip_state()` as an internal controller state query
and requires disabled preemption when per-CPU registers are involved.
The actual local `kernel/irq/manage.c`, `kernel/irq/chip.c`,
`kernel/irq/handle.c` and `drivers/irqchip/irq-gic-v3.c` were reviewed:
the direct SPI uses read-only pending/active/enable register queries,
has no sleeping IRQ bus lock, and releases the descriptor lock before
calling the registered handler. The UART lock serializes FIFO accesses.
The three state queries are sequential, not an atomic combined snapshot.

The old first-pending watchdog could win the UART lock before an IRQ
waiting to collect data. Console holds the lock with IRQs disabled for an
entire printk message; tty TX holds it for each frame. This motivates
retaining 20 ms observations and allowing 100 ms of unlocked IRQ progress
before fallback. The hardware samples had waits=0: they do not validate
that race explanation or the new grace branches. Idle `gic=80 err=0`
does validate the new read-only query on this device's direct mapping.

The actual `include/linux/sysfs.h` supplies the binary attribute callback
signature/group definition; the implementation uses a whole-buffer,
offset-zero snapshot under the UART lock, with version/size/sequence/CRC.
It only copies software records and computes CRC, with no FIFO register
reads during journal retrieval. Save to tmpfs before base64 transport.

The [matching model's vendor EUD source at a fixed revision](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/soc/qcom/eud.c)
does not supply a complete transferable framed TX algorithm: its TX path
uses a full-width UART ID check and writes data without this driver's LEN
sequence. Historical measurements on this unit show the purported TX
status bit remains set. No new specification was found that justifies
copying its flow control or guessing status/interrupt writes.

The journal is appended after this driver's issued ID/LEN/DAT writes and
fixed delay. Its sequence and CRC describe CPU-side software evidence.
They do not confirm device FIFO acceptance, physical USB ACK, or host
driver delivery. The journal adds small execution/memory overhead, so
passing candidate B cannot establish that observational changes are
timing-neutral. The tested 512-record window matches host raw completely;
RX47's archived missing 12 characters remain a separate real observation.

Prior [Microsoft URB header documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usb/ns-usb-_urb_header)
supports the session-boundary data-toggle hypothesis in RX47. This round
did not measure physical DATA0/1 or collect another administrator trace.
Compatible startup's one retry is not enough to place that first OUT at
a specific device/USB/driver layer. No new claim about blown production
fuses, AP DAP permissions or TRACE availability follows from these tests.
