# RX46 source review and next instrument

2026-10-09. This diagnostic investigates receipt loss after the RX41
wait-state/full-payload repair; it does not repeat payload-advancement guesses.

The [matching Realme DT](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/qcom/sm8150.dtsi)
specifies EUD 0x088e0000/0x2000, GIC SPI 492 level high. The actual samurai
node lacks interrupts. The kernel diagnostic synthesizes that resource only
for realme,samurai at the expected base, with a direct GICv3 parent and three
cells. Local irq-gic-v3.c translates SPI 492 to hwirq 524. Boot confirmed
virq=19/hwirq=524 and later real UART frames arrived through that handler.
The firmware DTB is authoritative; neither firmware nor FAT DTB changed.
This is a diagnostic workaround, not the final DT resource representation.

The [vendor eud.c](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/soc/qcom/eud.c)
reads INT1_EN_MASK and STATUS1 in its IRQ handler. Its RX branch tests
STATUS1 only; the TX branch also tests the mask. RX45's audit incorrectly
described RX as software-mask-gated and has been corrected. BIT(0) at the
hardware enable mask remains the basis of the RX-only IRQ setup. RX46 uses
mask 01, excluding stuck TX/VBUS/charger levels from the diagnostic handler,
and saves/restores the original 1c. No STATUS1 write was made.

[Linux IRQ documentation](https://docs.kernel.org/core-api/genericirq.html)
and the actual Linux tree were checked for request_irq/IRQF_NO_AUTOEN,
disable_irq_nosync, synchronization and domain mapping. The hard handler
caches complete payload under the shared UART lock, with no printk, tty
operation or restart. A 32-frame queue, eight consecutive empty-IRQ guard,
bad-header/queue fault and watchdog fallback bound exceptional handling.
F1 is deferred to work context and stops IRQ/restores mask before TOP_CFG,
EUD disable and kernel_restart. Remove stops IRQ, synchronizes/free_irq,
cancels work and disposes only a mapping newly owned by this driver.
Those fallback/remove exceptional paths were not runtime-tested here.

The existing console still holds the UART lock for an entire printk message.
That may delay interrupt handling during TX, so no latency/lossless claim is
made. The failed native C added neither IRQ entry nor empty/header/frame
count while the path was active and subsequent Ctrl-U arrived by IRQ.
This moves the observation boundary to absent notification, without proving
whether the host transmitted, the EUD delivered, or a transient notification
was lost before handler entry. It is not evidence of BusyBox failure or fuse
state. Native outputs remain exact when a frame is collected.

The first candidate used deprecated system_wq in mod_delayed_work and emitted
one runtime warning. Local workqueue.h shows schedule_delayed_work uses
system_percpu_wq; candidate B uses the same queue. Initial of_node_to_fwnode
compile error was corrected to this tree's of_fwnode_handle before flashing.
The final two Image builds completed without compiler warnings.

Same-boot libusb used bulk OUT 02/IN 81, max packet/read-size 16, no COM
setup/reset/ZLP. Three native commands and Ctrl-U succeeded on first OUT,
all by IRQ, and usbmon records full-length status-zero completions.
This small set does not prove long-term reliability or exclude a Windows
qcusbser-specific failure. [libusb I/O documentation](https://libusb.sourceforge.io/api-1.0/group__libusb__syncio.html)
requires checking transferred length; [kernel USB error documentation](https://docs.kernel.org/driver-api/usb/error-codes.html)
distinguishes submission from completion. usbmon is at the virtual WSL
controller, so it does not expose physical USB ACKs.

A first libusb invocation failed before any OUT because usbmon was not
loaded in that WSL instance. Loading the WSL usbmon module/mounting debugfs
restored the read-only instrument; a new capture prefix was used. No Windows
filter or device driver was changed. The later detach call reported the
device already not attached; final enumeration independently confirmed
Windows COM14 and USBIPD Shared/not Attached. No stale owner was assumed.

[Microsoft USB ETW instructions](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/how-to-capture-a-usb-event-trace)
describe PartialDataBusTrace payloads and USBXHCI/UCX completion detail,
without requiring a USB filter installation. Both providers exist locally.
Standard-user logman start was actually denied: -2147024891/E_ACCESSDENIED;
Windows explicitly requested administrator execution. The prepared
eud-etw-step.ps1 requires elevation, records one echo and a counter query,
stops its own session/serial in finally, and keeps all-device ETL local.
The user authorized one administrator capture, now completed. A launch-metadata
prefix collision was corrected before the actual trace. Its manifest confirms
trace_stopped, its operator log records both probe closures, and the exact
session is independently absent.
Reviewed target UCX dispatch/completion pairs have lengths 12/3/3 with successful
USBD/NT status; only echo10 plus one Ctrl-U adds IRQ frames/11 bytes. This narrows
the host boundary beyond application submission without proving EUD delivery.
Both normal and less-restricted tracerpt XML were inspected; original payload
bytes remain unverified. ETL/all-device XML stay local; only reviewed target
events and trace header are exported with their source hashes. Consult actual
provider/schema/driver sources before another capture; do not infer physical
ACKs or turn the short libusb successes into a Windows-only conclusion.
