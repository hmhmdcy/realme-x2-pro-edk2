# RX44 source audit (2026-10-09)

Purpose: investigate missing native-frame receipts after the RX41 TOP_CFG fix,
without repeating the earlier payload-advancement experiments.

- [Realme X2 Pro vendor eud.c, fixed commit](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/soc/qcom/eud.c):
  COM reception runs from an interrupt and reads ID, LEN, then DAT. Startup
  writes BIT(0) to INT_STATUS_1. Our current driver polls every 20 ms. This
  difference is a candidate to investigate, not proof that polling loses frames.
- [Matching vendor sm8150.dtsi](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/qcom/sm8150.dtsi):
  EUD at 0x088e0000, size 0x2000, GIC SPI 492 level high. The node has no EUD
  clock-vote or secure-eud property. The actual mainline serial node has no
  interrupt property; this session does not alter either DTB.
- The vendor probe tests `if (!ret)` after uart_add_one_port and goes to its
  error path on the normal zero return, before eud_ready and enable_eud.
  Its config/shutdown uses the OR of two complemented single-bit masks,
  producing all ones. These source issues limit claims that this COM path
  constitutes a validated, working implementation on retail hardware.
- Session 32 already combined the vendor startup status write with a relaxed
  DAT burst, before TOP_CFG was fixed. It failed to fix payload advancement.
  It did not isolate receipt stability. Do not repeat that combination as a
  new payload experiment or claim it independently disproved the startup write.
- The older DSP register table in reference/rx40 lists INT_STATUS_1 as read
  access. It is from another SoC and conflicts with these vendor writes; it
  does not justify a blind status clear, FIFO flush or reset on SM8150.
- [QUIC COM-support issue](https://github.com/quic/eud/issues/6): the visible
  discussion has the question and a stale bot response, no receipt-loss fix.
  Existing QUIC COM APIs contain incomplete application-level operations.
- [QUIC COM sample at fixed commit](https://github.com/quic/eud/blob/693741a3b0448690402539ed0e6af067510e386f/src/com_api.cpp)
  sends RX timeout `02 ff ff 00 00`. It does not document the hardware time
  unit, default, expiry effects or a readback. RX38 already submitted this
  exact setup and received no subsequent DEFG receipt. That run predated the
  wait-state fix and lacked pending counters; it is inconclusive for receipt
  loss. This session has not resent the command or reset the port.
- [libusb synchronous API](https://libusb.sourceforge.io/api-1.0/group__libusb__syncio.html)
  requires checking transferred bytes as well as the return code, including
  partial transfer on timeout. [Linux USB error codes](https://docs.kernel.org/driver-api/usb/error-codes.html)
  distinguish URB submission from completed transfer and report endpoint halt,
  CRC/protocol faults and timeout separately. RX43's libusb missing-receipt
  sample already has full-length, status-zero OUT completions. It is an
  inference, not a bus trace, that investigation must continue beyond that
  completion boundary toward EUD FIFO/status presentation to the CPU.
- [OpenOCD EUD addition](https://repo.or.cz/openocd.git/commit/d06edabdcdad9c4ed5d66102311c89c5c44e4e87),
  August 2026: the new driver implements SWD, not a COM console. Its
  [COM descriptor snapshot](https://github.com/openocd-org/openocd/blob/d06edabdcdad9c4ed5d66102311c89c5c44e4e87/doc/usb_adapters/eud/05c6_9005_eud_com.txt)
  agrees with RX36's 9505 bulk IN 0x81, OUT 0x02, 16-byte maximum packet and
  32-byte configuration. It supplies no new COM RX MMIO handshake.

The next diagnostic records polls, pending observations, rejected headers,
accepted frames/bytes and tty delivery using the existing MMIO reads. A sysfs
snapshot adds no hardware access. Ctrl-U includes these counts in its existing
receipt so a long shell command is not required. This lengthens that one
diagnostic receipt; normal multi-byte receipts, poll timing and FIFO access
order remain as in RX41.

## Production debug access question

The [QUIC README](https://github.com/quic/eud) lists the five peripherals as
chip capabilities, not an access guarantee for a particular production device.
[Linaro's firsthand experiments](https://www.linaro.org/blog/hidden-jtag-qualcomm-snapdragon-usb/)
report device-dependent fuses/policy and debug working on a production OnePlus
6. Our earlier tests established CTRL/COM use and SWD/JTAG transport with no
valid internal AP DAP response, including the firmware stage. They did not
read this unit's fuse values. TRACE remains unvalidated. See the qualified
[device evidence](../../SWD-JTAG.md); no new DAP mux, fuse, secure-policy or
TRACE operation was performed in RX44. A signed policy or a debug-enabled
device could supply an additional instrument, not a demonstrated COM fix.
