# Superseded patch extractions

These files are kept for provenance only. They are not part of the
current USB series and must not be applied on top of
`linux-port/patches/v7.3.1/0001-arm64-add-standard-samurai-platform-glue.patch`.

- `0024-arm64-dts-qcom-sm8150-use-snps-dwc3.patch` was an early
  standalone extraction of the SM8150 `qcom,snps-dwc3` single-node
  conversion. Its board-DTS context predates the current board wrapper;
  the live conversion is part of `0001`.
- `0025-usb-dwc3-qcom-restore-utmi-pipe-clock.patch` was an early
  standalone extraction of the `dwc3-qcom` UTMI PIPE clock restore.
  The same change is already in `0001`; keeping both causes a duplicate
  hunk and an ambiguous build base.

The reproducible USB series is defined against kernel head
`604f840ec52b24142aff59b5d1a77b6cecb58397`:

```text
0005-usb-dwc3-qcom-remove-unused-samurai-apsd-kconfig.patch
0006-usb-dwc3-gadget-keep-connect-sys-sleep.patch
0007-usb-dwc3-qcom-peripheral-wake.patch
0008-arm64-dts-samurai-usb-host-resume.patch
0011-usb-phy-remove-dead-hsphy-window.patch
0012-arm64-dts-qcom-sm8150-spmi-pdc-wake.patch
```

`0001` and `0002` are historical platform/camera snapshots, not a
linear quilt stack with each other; verify the USB series against
`604f840` rather than replaying `0001` then `0002`.
