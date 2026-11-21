# L2 source split for the locked k363 DTB

The common/OS/vendor wrappers were generated from the canonical k363 board
source by [`split-canonical-dts.py`](../../scripts/split-canonical-dts.py);
the three board-local camera fragments were then vendored here so a
rebuild does not depend on an out-of-tree kernel-tree copy. This is an
offline source split, not a deployed firmware image.

## Source identity

- Kernel build commit:
  `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`
- Kernel DTS:
  `arch/arm64/boot/dts/qcom/sm8150-samurai.dts`
- SHA-256:
  `428e20b3fe06a8b4ea85617cd2db3da9528e4edb0276647e7c7ed15c3737338b`
- Config:
  `Image363-extracted.config`, SHA-256
  `23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed`

The exact source is also archived as
[`reference/kernel276/sm8150-samurai.dts`](../../../reference/kernel276/sm8150-samurai.dts);
the file is byte-identical at the k363 build commit.

## Files

| File | Purpose |
| --- | --- |
| `sm8150-samurai-common.dtsi` | Shared board hardware description and debug boot command line |
| `sm8150-samurai-os.dts` | OS-facing wrapper without vendor match properties |
| `sm8150-samurai-vendor.dts` | Semantic control wrapper with vendor match properties |
| `imx319.dtsi` | Board-local rear main-camera wiring, rails, GPIO and CSI endpoint |
| `s5k3m5-samurai.dtsi` | Board-local telephoto wiring, rails, GPIO and CSI endpoint |
| `s5kgw1-samurai.dtsi` | Board-local primary-camera wiring, actuator and CSI endpoint |

The vendor wrapper is **not** the 450,826-byte stock ABL compat DTB. The
stock compat blob remains a separate firmware input.

The three camera fragments are copied into this directory so the board
source does not depend on out-of-tree fragments being present in whichever
kernel tree performs the build. A rebuild with these local fragments still
produces `f7959f8a...a3f0`, byte-for-byte identical to the earlier split
output.

## Verified build

The locked k363 DTB rebuild produced 114,556 bytes with SHA-256:

```text
dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d
```

This matches `reference/kernel363/boot-candidate-build-validation.json`.

The split also produced:

- `sm8150-samurai-vendor.dtb`: byte-identical to the canonical k363 build;
- `sm8150-samurai-os.dtb`: semantically identical except for removal of
  `qcom,msm-id`, `qcom,board-id`, and `oppo,dtsi_no`.

## L3-02 OS-only sensor data

The L3-02 candidate uses the standalone OS wrapper
[`../l3/sm8150-samurai-os-sensor-data.dts`](../l3/sm8150-samurai-os-sensor-data.dts),
which includes the locked OS wrapper and the overlay
[`../l3/sensor-power-data.dtsi`](../l3/sensor-power-data.dtsi). The
overlay adds six optional `realme,*` properties to `/sensor-power`; the
vendor wrapper does not include it. Keeping this as a separate wrapper
leaves the locked OS wrapper and `source-lock.json` unchanged. Rebuilding
the locked OS wrapper in the current host tree is semantically identical
to `f7959f8a...`, with zero changed/added/removed nodes or properties;
byte identity remains defined by the exact worktree recorded in the source
lock.

The exact-k363 OS DTB candidate build is
`89604b9ce7ea1502dc3a73f1523fc48d46044166792dbbd2d5c2aa4f9d66d570`
(114,709 B). Its semantic diff against the pre-L3 OS DTB
`f7959f8a...a3f0` is exactly six added properties, with zero changed,
removed, or relocated nodes/properties. The vendor wrapper source was not
changed; rebuilding it on the current host tree remained semantically
identical to canonical `dcdd74ec...2c8d`, though the byte hash can vary
with the host DTSI/dtc tree and is not used as the identity test.

This overlay is still offline data. It is not installed in a kernel tree,
not activated in firmware, and does not replace the canonical v1 source
lock.

The k270 actual boot DTB `429db1fa...` was also compared with the OS DTB:
zero changed property values, 12 added camera nodes, 3 added CCI
properties, and the same 3 removed vendor root properties. See
[`L2-DUAL-KERNEL-MATRIX.md`](../../docs/L2-DUAL-KERNEL-MATRIX.md). This is
offline compatibility evidence only.

The current boot image does not yet contain this source-built OS DTB. Its
pre-probe OS DTB is the charging-integration variant
`9736b861ae73a045dcc032963b81b680f3f2662623b4e1175c2bcea1d29f9352`.
That identity must be resolved separately before claiming the firmware ABI
is frozen.

## Deployed difference ledger

The pre-probe deployed DTB has been compared with the canonical k363 DTB
and classified by [`dtb-diff-ledger.py`](../../scripts/dtb-diff-ledger.py).
After normalizing phandle renumbering, all 24 semantic differences are
classified:

- camera ICP experiment: 7;
- charging / USB-input experiment: 12;
- USB controller linkage: 1;
- EUD debug route: 3;
- debug/test bootargs: 1;
- new public ABI items: 0.

The current post-probe OS DTB adds only the three vendor root-property
removals, so its 27 differences are also fully classified. The receipts
are under
`E:\edk2-samurai-out\layer-adaptation-20261105\source-lock-ba61\`.

The classified experiment is now also reconstructed in
[`../experiments/`](../experiments/). Its offline build
`c582dd7c...a64f` differs from the deployed `9736b861...` by zero semantic
properties and zero nodes; only the deployed carrier has one unused
`eud-off-route` phandle. Build and comparison receipts are in
`E:\edk2-samurai-out\layer-adaptation-20261105\experiment-dtb-build\`.

## Limitations

- The debug `bootargs` is still in the shared source.
- No runtime activation of the source-built split has been performed.
- The k270/k363 DTB semantic matrix is additive-only offline, but neither
  kernel has booted with the candidate DTB.
- No multi-SKU startup matrix has been run.
- The classified charging, camera ICP, EUD, and debug differences still
  need to be moved to separately versioned overlays or firmware inputs.
