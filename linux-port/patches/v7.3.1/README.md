# Linux v7.3.1 patch series notes

## SOFEF03F panel series

`0003-arm64-panel-sofef03f-reapply-backlight.patch`,
`0005-arm64-panel-sofef03f-post-on-after-first-frame.patch` and
`0009-arm64-panel-sofef03f-serialize-brightness.patch` are historical.
They were applied in sequence while the 2026-11-10 HBM root cause was
being isolated.

For new builds use:

`0010-arm64-panel-sofef03f-hbm-first-frame-consolidated.patch`

It applies to the v7.3.1 base panel file and reproduces the deployed
driver byte-for-byte. It includes the stock HBM transition
(`0x53=0xe0/0x20`), first-frame post-on and bounded reapply, mutex
serialization, and the panel power-sequencing corrections that were
already present in the working tree. Do not stack 0003, 0005 and 0009 on
top of it.

The interface remains standard DRM panel, backlight class and MIPI DCS.
No new private ioctl, sysfs node, DT property or board constraint is
introduced.

## USB controller series

The reproducible USB series is defined against kernel head
`604f840ec52b24142aff59b5d1a77b6cecb58397`. `0001` and `0002` are
historical platform/camera snapshots and do not form a linear stack with
each other; do not try to replay `0001` then `0002` as the USB base.

- `0001` contains the SoC DTS conversion to the mainline `qcom,snps-dwc3`
  single-node binding and the `dwc3-qcom` UTMI PIPE clock restore. Both
  are already present in the `604f840` baseline; the early standalone
  extractions in `../superseded/` are not part of this series.
- `0005` removes the unbuilt samurai APSD DWC3 Kconfig/Makefile hooks.
- `0006` adds the generic DWC3 gadget keep-connect system-sleep policy.
- `0007` arms the existing Qcom DP/DM/SS PDC wake IRQs in peripheral mode.
- `0013` adds the cable-event fallback to the keep-connect resume path. It
  is inert while the board does not opt into keep-connect.
- `0014` removes the board keep-connect opt-in. Without a proven
  VBUS/attach source the stale U3 state arms `dp_hs_phy_irq` and aborts
  every suspend, and a cable-event resume previously produced a Windows
  Code 43. The board now uses the standard DWC3 gadget suspend/resume path.
- `0011` removes the now-unused `phy-qcom-snps-femto-v2-window.h` interface
  and restores the generic Qcom SNPS Femto PHY driver to the v7.3.1
  baseline. It has no consumer after `0005`; it is a deletion-only cleanup
  and must not be applied before the APSD owner removal.
- `0012` moves the SM8150 SPMI `periph_irq` from a raw GIC SPI to PDC pin 1
  in `sm8150.dtsi`, matching the SM8250 mainline model. The board
  `usb2-vbus-wake.dtso` overlay and its udev rule were withdrawn on
  2026-11-11 after the GPIO10 assumption was disproved on hardware.

Do not re-enable `0006`/`0007`/`0013` on this board until a standard
PM8150B Type-C/TCPM attach/VBUS source is wired. See
[`USB-REMOTE-WAKE-20261111.md`](../../docs/USB-REMOTE-WAKE-20261111.md).
