# RMX1931 cold-boot panel investigation (superseded)

Status: superseded, never flashed. The 2026-11-11 cold-boot test passed with
the verified SOFEF03F HBM fix, so the MDSS-reset/null-insertion candidate is
not needed for the observed symptom.

> **Validity note.** This document records an earlier hypothesis: a display
> controller state left by the bootloader. It was written before the
> 1023/1024 HBM boundary was identified. The HBM fix survived a real
> external-power-removed cold boot and a post-cold-boot power-key wake on
> 2026-11-11. Keep this candidate only as a reference for a future,
> separately reproducible MDSS-reset failure; do not treat it as the
> cold-boot fix. See [PANEL-HBM-20261110](PANEL-HBM-20261110.md).

## Symptom

The UEFI bootloader drives the physical panel correctly. Once Linux probes
DRM/KMS, the panel becomes black even though:

- KWin produces a complete lock-screen frame;
- the DPU scanout buffer contains that frame;
- DSI reports connected;
- DPMS transitions and TE completion return success;
- DPU first-frame and panel-backlight tracepoints fire;
- `backlight` reports `brightness=1024` and `bl_power=0`.

A full standard DPMS off/on reprograms the display path and can make the same
boot display normally. That distinguishes this failure from a compositor or
scanout failure.

## Upstream evidence

SM8250, SM8350, SC8180x and newer Qualcomm display controllers describe the
MDSS core reset:

```dts
resets = <&dispcc DISP_CC_MDSS_CORE_BCR>;
```

SM8150 was missing the same property even though `msm_mdss_reset()` already
supports it. The omission is being fixed upstream:

- Subject: `[PATCH 7/9] arm64: dts: qcom: sm8150: add MDSS reset`
- Author: Dmitry Baryshkov
- Message id:
  `20261015-sm8150-display-card-v1-7-5c14928cef29@oss.qualcomm.com`

The reset is asserted for 20 ms during MDSS probe. It clears display
controller state inherited from the bootloader before Linux reserves and
programs DPU/DSI/DSC blocks.

## Candidate layers

The candidate deliberately separates several unproven changes:

1. Generic SM8150 MDSS reset, from the upstream change above.
2. SOFEF03F power/reset delays interpreted as microseconds, matching the
   stock DTS values and stock driver call sites.
3. DCS initialization in `prepare()`, with display-on sent only after the
   first frame in HS mode.
4. DSI STREAM1 cleanup when programming the controller.
5. Optional command-mode null-packet insertion, controlled by
   `qcom,null-insertion-enabled`.

Layer 5 is not enabled in the first cold-boot test. Null insertion remains a
candidate because command-mode DSC can corrupt output without it, but old
register evidence did not prove it is required on RMX1931.

The register-database entry uses offset `0x2b0`. This is intentional: SM8150
uses DSI6G, whose `io_offset` of 4 is added when `ctrl_base` is initialized,
so the physical register is `0xae942b4`, matching the downstream definition.

## Artifacts

| Artifact | SHA-256 |
| --- | --- |
| `Image-v731-mdss-reset` | `90f15f153ac62f7d489fb684da55b643594a917c3993778fc979fd2bacb572e5` |
| `modules-v731-mdss-reset.tar.gz` | `da911d86e0cb6a63084ca50fc028fcafa2c251debe685f193f5dd3918e4408ad` |
| `sm8150-samurai-mdss-reset-timing-only.dtb` | `f4c18825a42a212f4a90ab56e9b9b6410e4a594efca54e85ad9be82f3f8d513a` |
| `sm8150-samurai-mdss-reset.dtb` | `9d7d6583b622af2156f9ad757cf0ff1de446059b57f3f58dc10753344deb38ca` |
| MDSS reset patch | `5f4e0cfc9a48bd0174a3c15026e1a47d274b4fb29de000e897a805070c3be5b3` |
| `sm8150.dtsi` snapshot | `a3311d23b7781f6a771da63329107b767de6c5eda02884cdcaed39e84424435f` |

Private build directory:

```text
E:\edk2-samurai-out\standard-arm64-v731\panel-mdss-reset-20261110\
```

## Historical acceptance sequence (not executed)

This sequence was never run for the MDSS-reset candidate. The 2026-11-11
cold-boot pass used the HBM-fixed image instead; keep these steps only if a
future failure independently reproduces a pre-HBM MDSS state.

1. Establish SSH over NCM and inhibit idle suspend for the debug session.
2. Install the same-build stripped modules.
3. Write `Image-v731-mdss-reset` to kernel FAT `/Image`.
4. Write `sm8150-samurai-mdss-reset-timing-only.dtb` to `/samurai.dtb`.
5. Read both files back and verify their hashes.
6. Reboot and record the whole transition with the external camera.
7. Separately power the phone down and start it by the physical power key.
8. Verify the screen survives DPMS off/on, short power-key presses, s2idle
   resume, and a second cold boot.
9. Only then evaluate `sm8150-samurai-mdss-reset.dtb` to decide whether null
   insertion is required.

Do not touch boot, NV, persist, calibration, or user-data partitions.

## Debug-only state

The NCM and Wi-Fi watchers under
`panel-delay-fix-20261109` only restore the transport after resume and start a
root `elogind-inhibit`. They are not part of the platform fix and must be
removed from the final system.
