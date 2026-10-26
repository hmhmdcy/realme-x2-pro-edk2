# RX45 source audit

2026-10-09. RX41's TOP_CFG=0x11 and full-frame burst remain verified.
RX44's counters narrowed failed commands to no pending observation.

The [matching Realme driver](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/soc/qcom/eud.c)
defines INT1_EN_MASK at +0x24 and RX at BIT(0). Its common enable mask is
VBUS|CHGR|SAFE_MODE=0x1c. Its IRQ routine reads the mask and STATUS1, but
the RX branch tests STATUS1 only; the TX branch also checks the mask.
This supplied the basis for setting only the hardware RX enable before arrival; it
does not establish that enabling an IRQ bit changes FIFO retention.

Session 33 changed both INT0 and INT1 only after a pending LEN=6 frame was
already observed and used delayed DAT reads before TOP_CFG was fixed.
Session 45 instead changed only INT1 from the saved low byte 0x1c to 0x1d,
before input, with readback verification and F1/remove/failure restoration.
It retained 20 ms polling and made no STATUS1, reset, DAP mux or fuse writes.
The failed native command added no pending/frame/tty count; persistent mask
alone is insufficient. Actual IRQ delivery remains untested by this run.

The vendor DT identifies [GIC SPI 492, level high](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/qcom/sm8150.dtsi).
The actual mainline serial node has no interrupt property. A future IRQ
diagnostic must verify the route and count IRQ entries, safely stop a storm,
keep receipt/tty/reboot work out of hard IRQ context and preserve F1.
The firmware-supplied DTB is authoritative; replacing the FAT DTB alone
does not establish the kernel's IRQ resource. No IRQ was registered here.

Research was refreshed for the user's question about the five peripherals:
[Linaro's firsthand report](https://www.linaro.org/blog/hidden-jtag-qualcomm-snapdragon-usb/)
describes device-dependent fuses and OEM-signed policy, including working
debug on a production OnePlus 6. It is not proof of RMX1931 fuse values.
[SWD-JTAG.md](../../SWD-JTAG.md) records this unit's functioning USB debug
transport, absent tested AP DAP reply, and unvalidated TRACE capability.
An old HANDOVER sentence asserting APPS_DBGEN_DISABLE was corrected to
match those evidence limits. No fuse read or debug-policy change was made.
The [QUIC COM issue](https://github.com/quic/eud/issues/6) still provides no
implementation fix as checked this session.
