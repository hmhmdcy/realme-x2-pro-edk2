# Offline DTB experiment profiles

This directory separates the hardware contract from the deployed experiment
policy. None of these fragments is activated by the production OS wrapper.

| Fragment | Layer | Rule |
| --- | --- | --- |
| `samurai-camera-icp.dtsi` | camera experiment | optional overlay; not part of `samurai-dt-v1` |
| `samurai-charging-usb-input.dtsi` | charging experiment | optional overlay/firmware input |
| `samurai-5v1500-policy.dtsi` | supply policy | requires the charging fragment; policy only |
| `samurai-eud-off-route.dtsi` | debug | debug-only; exclude from production DTB |
| `samurai-debug-bootargs.dtsi` | startup policy | move to debug entry/LoadOptions |
| `usb2-typec-sink.dtso` | USB Type-C | DTB-only, current gadget-only kernel, TCPM sink/device |
| `usb2-typec-dual.dtso` | USB Type-C | requires a new Image with DWC3 dual-role and xHCI |
| `sm8150-samurai-usb-typec-sink.dts` | USB Type-C | full source-level sink wrapper for kexec/offline validation |
| `sm8150-samurai-usb-typec-sink-compact.dts` | USB Type-C | boot-FFS-fit sink wrapper; drops only the disabled, absent Ethernet node |

The independent build profiles are:

| Profile | Includes |
| --- | --- |
| `profile-charging-500ma.dts` | common + charging |
| `profile-charging-5v1500.dts` | common + charging + 5V1500 policy |
| `profile-camera-icp.dts` | common + camera ICP |
| `profile-eud-debug.dts` | common + EUD route + debug bootargs |

All four built successfully; their ledgers classify every semantic item:

| Profile | DTB SHA-256 | Semantic items |
| --- | --- | ---: |
| charging 500 mA | `3afcaceb...a564e` | 15 |
| charging 5 V / 1.5 A | `70f5e0f0...f9953` | 15 |
| camera ICP | `83f4e286...e6ca` | 10 |
| EUD debug | `0d8e701b...d55148` | 8 |

The USB2 Type-C overlays are built separately and then merged into a
symbolized production base DTB:

| USB profile | DTB SHA-256 | Kernel requirement |
| --- | --- | --- |
| sink | `b18da562...657bd792` | current gadget-only config |
| dual | `ef8e40ba...7e87e58d` | `DWC3_DUAL_ROLE=y`, `XHCI_HCD=y`, `XHCI_PLATFORM=y` |

See [`USB-TYPEC-20261110.md`](../../docs/USB-TYPEC-20261110.md) and
[`build-usb-typec-candidates.py`](../../scripts/build-usb-typec-candidates.py).
The sink profile does not change `dr_mode` or add a role-switch graph; the
dual profile is not deployable with the current Image.

The deployed 2026-11-12 boot DTB is built from
`sm8150-samurai-usb-typec-sink-compact.dts`.  It keeps the production
`model`/`chassis-type` and all USB nodes, removes only the disabled SM8150
Ethernet controller (not populated on RMX1931), and fits the existing
114716-byte embedded DTB section at 114595 bytes.  See
[`USB-TYPEC-WAKE-20261112.md`](../../docs/USB-TYPEC-WAKE-20261112.md).

The former `usb2-vbus-wake` profile was withdrawn on 2026-11-11.  The vendor
DTS comments out the PM8150 GPIO10 `vbus-gpio` and its `&usb1` consumer, and
live sampling showed GPIO10 does not follow VBUS.  See
[`USB-REMOTE-WAKE-20261111.md`](../../docs/USB-REMOTE-WAKE-20261111.md).

`sm8150-samurai-experiment-os.dts` is an offline reconstruction profile for
the deployed `9736b861...` experiment. It is intentionally separate from
`../split-ba61/sm8150-samurai-os.dts`.

## Offline reconstruction result

The profile was built with the locked k363 kernel tree and compared with the
deployed experiment DTB:

- built DTB: `c582dd7c...a64f`, 116843 bytes;
- deployed DTB: `9736b861...f9352`;
- semantic changed properties: 0;
- added/removed nodes: 0;
- added/removed properties: 0;
- one linkage-only difference: the deployed carrier has an unused
  `/soc@0/eud-off-route` phandle.

Receipts are in
`E:\edk2-samurai-out\layer-adaptation-20261105\experiment-dtb-build\`.

The build script is
[`build-dtb-experiment.py`](../../scripts/build-dtb-experiment.py):

```sh
python3 linux-port/scripts/build-dtb-experiment.py \
  --kernel-root /home/cy122/x2pro-linux/l2-source-ba61 \
  --dtc /path/to/kernel/scripts/dtc/dtc \
  --output-dir /path/to/experiment-dtb-build \
  --compare /path/to/deployed-9736b861.dtb
```

This proves source-level semantic identity, not byte identity and not runtime
activation. The production OS DTB remains sourced from
`../split-ba61/sm8150-samurai-os.dts`.
