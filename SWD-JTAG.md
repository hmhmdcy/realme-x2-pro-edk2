# EUD SWD / JTAG on the realme X2 Pro

> Split out of EUD.md on 2026-10-08; verbatim from there.  EUD COM (the console) is in
> EUD.md and RX-CONSOLE.md.

> **2026-10-09 evidence qualification:** CTRL and COM are usable on this unit.
> SWD/JTAG USB transport is usable, but the tested internal AP DAP does not
> respond. We have not read this unit's debug-fuse values, so this is not proof
> of which fuse was programmed or that every retail unit has identical policy.
> TRACE has not been validated. The current COM receipt-loss investigation is
> in sessions/46-rx-irq-and-host-trace-boundary.md; enabling another peripheral does not
> itself repair the COM receive path.

---

## SWD / JTAG on this retail unit: transport works, target DAP does not (2026-10-08)

### Transport verified on hardware

The EUD SWD and JTAG peripherals do come up on this unit; the older note
("CTLOUT_SET 0x645 + VBUS attach did not make 9504 appear") failed on the
payload, not on the hardware.

| Peripheral | CTLOUT_CLR | CTLOUT_SET | Result |
|---|---|---|---|
| SWD, DAP route (use this) | 0x000E0090 | 0x00100445 | USB\VID_05C6&PID_9504 appears |
| SWD, GPIO route          | 0x000E0090 | 0x00000545 | 9504 appears, but SWD goes to the external pads |
| JTAG                     | 0x001E0104 | 0x00000090 | USB\VID_05C6&PID_9503 appears (needs the VBUS pulse) |

* Do **not** pulse VBUS_ATTACH/VBUS_INT for the SWD DAP route. A port that is
  stuck as "unknown USB device (descriptor request failed)" is recovered by
  clearing the peripheral bit, waiting for the port to disappear, setting it
  again and giving it about 3 s.
* Both devices bind to oem58.inf (QdssPort / qdbusb.sys) and expose user-mode
  DOS paths (no "(0004)/(0003)" suffix on this unit):
  `\\.\Qualcomm EUD SWD Device 9504\DEBUG` and
  `\\.\Qualcomm EUD JTAG Device 9503\DEBUG`.
* Every command needs an explicit FLUSH byte (0x01) before its response is
  returned: SWD STATUS `07 01` -> 4 B; JTAG FREQ_RD `0F 01` -> 4 B.
  SWD status word: bits[2:0] = ack (1 = OK, 2 = WAIT), bit3 = wait_timeout,
  bit4 = parity_err, bit5 = freezio_latch, bits[31:16] = cmd_cntr.
* SWD and JTAG share one debug port and are mutually exclusive.

### The target DAP never answers

With the DAP route up, the full OpenOCD-equivalent connect sequence was run:

    FREQ 0x4 -> line reset -> JTAG-to-SWD (0xE79E) -> line reset
    -> ABORT 0x4 -> DP CTRL/STAT = 0x50000000 (power-up request) -> ABORT 0x1F
    -> read DPIDR (0xA5)

Result on this unit, in every state tried (Android awake, Android suspended, and
with SRST/TRST asserted through SWD bitbang):

    data = 0x00000000   status = 0x00010020   ack = 0   freezio_latch = 1

`ack = 0` means no valid DAP acknowledgement was returned. The EUD status also
reports `freezio_latch`; that flag alone does not identify a particular fuse
or distinguish all policy, mux, power and clock causes. Switching the internal DAP mux on while Android
is running also **hangs the AP** (black screen, full power cycle needed).

Research (Linaro "The hidden JTAG in your Qualcomm/Snapdragon device's USB port",
linux-msm/openocd README + src/jtag/drivers/eud.c, Qualcomm QFPROM and security
documentation, qualcomm-linux/qcom-ptool):

* debug access can be controlled by **fuses** plus an **OEM-signed debug
  policy**. Qualcomm driver families distinguish invasive debug enable,
  non-invasive trace enable, DAP device enable and global disable. Names such
  as `APPS_DBGEN_DISABLE` describe those controls, not a measured fuse value
  for this phone; fuse layouts vary by SoC/version;
* the policy lives in the **apdp** partition ("Apps Processor Debug Policy").
  The F.14 package for this phone ships it as `dpAP.mbn`, a signed ELF carrying
  the OPPO Root CA / Attestation CA chain, so it cannot be replaced without the
  OEM signing keys;
* the official quickstart enables EUD **in U-Boot/fastboot**
  (`mw.l 0x88e1014 1`, keeping the fastboot gadget registered), then attaches
  OpenOCD (`swd newdap ... -expected-id 0x5ba02477`), and suggests booting Linux
  with `maxcpus=1`.

Conclusion for this retail unit: the EUD *transport* is usable from the host,
but the AP CoreSight DAP is not exposed to it. This was finally confirmed at the
officially recommended stage as well (the OpenOCD quickstart way: enable EUD from
the firmware, not from Android): `boot-samurai-eudlogfull.img` was flashed,
BDS enabled EUD (9501 appeared at +6 s), the DAP route was set and the same
sequence returned `data = 0x00000000, status = 0x00010020, ack = 0` - identical
to the Android-stage result. Moving to UEFI therefore did not make the DAP
accessible in the tested configuration. Boot-time security policy is a
plausible explanation, not a direct measurement of an XBL decision or fuse
value. There is no demonstrated unlock method for this unit in this project.

[Linaro's firsthand EUD report](https://www.linaro.org/blog/hidden-jtag-qualcomm-snapdragon-usb/)
describes both debug fuses and OEM-signed policy, and a production OnePlus 6
where debug works. It does not prove the same permissions on RMX1931. Such a
policy must be accepted by the OEM trust chain and match the device/security
configuration; unlocking the Android bootloader does not establish that
permission. Programmed OTP fuses are not software-erasable, while some debug
restrictions may have authorized policy overrides. Neither an arbitrary APDP
image nor another model's firmware is a demonstrated solution here.

The [Qualcomm JTAG fuse driver family](https://android.googlesource.com/kernel/msm/+/e60e904d4e7457386748f5e80fe8b56da7a79bd1/drivers/soc/qcom/jtag-fuse.c)
and [CoreSight fuse checks](https://android.googlesource.com/kernel/msm/+/android-6.0.1_r0.73/drivers/coresight/coresight-fuse.c)
illustrate separate DAP/debug/trace gates; their addresses and bit positions
must not be copied blindly to SM8150.

If authorized AP debug were available, it could help inspect MMIO and IRQ
state, but halting the CPU also changes FIFO timing. TRACE could assist only
after a permitted trace source, route and sink are configured; enumeration
alone does not establish useful capture. For today's COM fault, retain
software RX counters and host USB captures as the working instruments.

The TRACE USB peripheral transports SoC trace data; it is not a USB bus
analyser. A blocked CPU trace source does not by itself establish that every
software trace source is blocked, or that the USB trace peripheral is fused
off. Those are separate capabilities requiring separate evidence.

### Practical guidance for this port

* Treat **EUD COM** as the primary debug channel: verified end to end, and it is
  what the firmware DEBUG() and the Linux `earlycon=eud`/`console=eud` use.
* Keep the SWD/JTAG tooling (`E:\eud-host\eudtool.exe`, `devraw.exe`,
  `swd-idcode.ps1`) for a debug-enabled/engineering device, where the same
  sequence should read DPIDR `0x5ba02477`; do not plan normal bring-up work
  around halting this phone.
* `maxcpus=1` is worth trying when debugging the Linux SMP bring-up.
* Safety: never switch the internal DAP mux while Android is running; EUD keeps
  the USB port until a full power cycle (hold Power ~15 s).
