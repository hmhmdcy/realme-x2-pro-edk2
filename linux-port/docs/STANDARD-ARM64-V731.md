# Standard ARM64 Linux v7.3.1 adaptation

Updated: 2026-11-06

This checkpoint turns the Realme X2 Pro (`RMX1931` / `samurai` / SM8150)
from a bring-up tree into a reproducible Linux v7.3.1 platform image. The
deployed hardware uses mainline models and APIs for the exposed platform;
only SoC wiring, regulator sequencing and a small amount of board glue remain
private.

Machine-readable identities and hashes are in
[`../dts/v731/source-lock.json`](../dts/v731/source-lock.json). The frozen
hardware view is in
[`../dts/samurai-dt-v1-abi.json`](../dts/samurai-dt-v1-abi.json).

## Runtime result

The source-controlled boot image is now flashed and booted:

- release: `7.3.1-rmx1931-samurai-v731`;
- boot partition SHA-256:
  `c8a6c616f60c8ee8f314bfc9e1329c61af3eb070b0cee3724b99080ad3444eaf`;
- first boot ID: `a38fc278-644b-4387-97cf-f5c0c06aa541`;
- ordinary-reboot ID: `3df82213-3f55-4ab6-b6af-a8a54e73645d`;
- `taint=0`;
- three remoteprocs `running`;
- `sensor-power` reports `vdd=1 vddio=1`;
- UDC `configured`;
- `bq28z610-0` and `mp2650-input` bind through `power_supply`;
- DSI `connected/enabled/On`;
- `tinydm`, `sshd`, `samurai-usb`, `samurai-sleep-inhibitor`, KWin and
  plasmashell start after both boots.

The boot partition and logdump were read back on the device and match the
candidate hashes. The runtime evidence endpoint is the local Wi-Fi SSH link;
the test image is not a distributable generic image.

## Kernel source identity

The v7.3.1 source was imported from the official tarball, then split into two
commits:

| Item | Value |
| --- | --- |
| tarball SHA-256 | `fa595aad93734f829c963c2a90ef7c3673224fd7fdae7b49406e397cde2de231` |
| baseline commit | `09455be5a5c3421019315de48a32c9ded91d0030` |
| platform commit | `824dc0a56143d8bf1cc1d20adb877abced48b336` |
| platform tree | `fbbf939a98426cd45e08b4d7a42bcadfbf900d39` |

The platform commit is stored as
[`../patches/v7.3.1/0001-arm64-add-standard-samurai-platform-glue.patch`](../patches/v7.3.1/0001-arm64-add-standard-samurai-platform-glue.patch)
(SHA-256
`11e97a17342ac13989686683bd8bc1e4269b41b050a7914c57c055b186390063`).
The exact build configuration is
[`../configs/v7.3.1/samurai.config`](../configs/v7.3.1/samurai.config)
(SHA-256
`5c7ea3eec1bb0efca473f3032390fff0368fc8dbc4f826c4b614863300004ffc`).

The production wrapper is
[`../dts/v731/sm8150-samurai.dts`](../dts/v731/sm8150-samurai.dts). It deletes
the source-tree debug `bootargs`, disables EUD, switches the primary USB
controller to the standard DWC3 model and disables the unused SuperSpeed PHY.

## Firmware source identity

The production command line is now present in the EDK2 source, not only
byte-patched into an image:

```text
console=tty0 loglevel=4 panic=15 clk_ignore_unused
```

The EDK2 change is
[`../patches/edk2/0001-samurai-production-bds.patch`](../patches/edk2/0001-samurai-production-bds.patch),
SHA-256
`e05a5e9c154794c76cfd554b3b43aa367754ee3d61193da1b60af53177b7eee1`.
`PlatformBm.c` hashes to
`2a3a90fbb4ba42e9a2dad38f4b9282940db7236d7ee07373a29fde0a5471bba5`.

The EDK2 GCC LTO layout depends on the command-line allocation size. The
source therefore keeps the historical 108-`CHAR16` allocation and pads the
shorter production string with 57 spaces. The kernel parser ignores those
spaces. Rebuilding the old and final command lines with one fixed staging
tree produced only printable metadata differences:

```text
metadata-review: passed=true
classification: printable_metadata_only
BdsDxe: 80 changed bytes / 80 changed ranges
PlatformSmbiosDxe: identical
UiApp: identical
```

The BdsDxe image is 110592 bytes, SHA-256
`f3b946b1660cd444048aba7e5fe434e08a6f41d8dd11cc83f944455fea6855ac`.
The final boot changes only the BdsDxe FFS among the 101 main-FV files; the
other 100 files, the compatibility DTB, shim and ramdisk are preserved.

## Command-line pruning

Each item was removed in a separate boot/rollback window:

| Change | Result |
| --- | --- |
| remove `ignore_loglevel`, set `loglevel=4` | pass |
| remove `clk_ignore_unused` | **fail, stopped in fastboot; rolled back** |
| remove `pd_ignore_unused` only | pass |
| remove `regulator_ignore_unused` only | pass |
| remove both PD/regulator flags | pass |

`clk_ignore_unused` remains only because it is a measured necessary board
constraint. It is not treated as a general platform default or as a substitute
for fixing the missing clock consumer.

## Standard interfaces

The v7.3.1 image uses:

- standard `mps,mp2650` and `ti,bq28z610` `power_supply` devices;
- the generic `qcom,sm8150-dwc3` / `qcom,snps-dwc3` USB model, UDC class and
  configfs gadget;
- the generic remoteproc prepare/unprepare subdevice lifecycle for the SLPI
  sensor rails;
- DRM/KMS and backlight class for the panel;
- ASoC/ALSA PCM and UCM for audio;
- evdev, input force feedback and standard udev/feedbackd discovery;
- IIO and SensorProxy for sensor consumption.

The retained board-specific code is intentionally narrow:

- SM8150 and samurai DTS wiring;
- the sensor-power regulator sequencer;
- the sofef03f panel description;
- the AW8697 haptics board driver;
- MAX98937 and samurai ASoC board glue.

The image does not include the camera ICP/CAMSS experiment, APSD/private
USB-input charging, private managed-charging kernel modules, production EUD
serial ownership, vendor root compatibility properties or private
`samurai_diag` trace dependencies.

The old `samurai-charging` package is now a legacy explicit-opt-in experiment.
`samurai-platform` 5-r14 no longer depends on it; the standard image relies on
the kernel charger/gauge bindings and the standard `power_supply` class.

## DTB contract check

The v7.3.1 DTB is 114371 bytes, SHA-256
`3261908efb6730f43f41e9ab752b03a107ab583d451f433c7eb648760ed79ebb`.
The updated contract declares 12 resources, including the standard MP2650
charger and the DWC3 wrapper at `/soc@0/usb@a600000`:

```text
passed=true
resources_declared=12
resources_checked=12
failures=0
warnings=0
```

The contract remains deliberately not frozen for multi-SKU, cold-boot and
suspend/resume coverage.

## Reproduce the image

On the Linux build host:

```sh
git clone --branch codex/v7.3.1-samurai <kernel-worktree>
git -C <kernel-worktree> checkout 824dc0a56143d8bf1cc1d20adb877abced48b336
cp linux-port/configs/v7.3.1/samurai.config <build-dir>/.config
make -C <kernel-worktree> O=<build-dir> ARCH=arm64 \
  CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make -C <kernel-worktree> O=<build-dir> ARCH=arm64 \
  CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image dtbs modules
```

Build and package the firmware metadata with the fixed staging path:

```sh
python3 linux-port/scripts/build-eud-off-bds.py \
  --output <new-bds-output> --execute
python3 linux-port/scripts/build-boot-larger.py \
  --boot <trusted-boot> --bds <new-bds-output>/BdsDxe.efi \
  --dtb <build-dir>/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb \
  --output <new-boot-output> --execute
python3 linux-port/scripts/review-boot-metadata.py \
  --source-boot <old-source-built-boot> \
  --candidate-boot <new-boot-output>/boot-eud-production-off.img \
  --compat-dtb <compat.dtb> --output <review.json>
```

The v7.3.1 binaries produced by this checkpoint are:

| Artifact | SHA-256 |
| --- | --- |
| `Image-v731` | `dc4c5623551824d170397cd93a01256dfc0eadb0d13b949c54e64f6e0ea61eda` |
| `sm8150-samurai-v731.dtb` | `3261908efb6730f43f41e9ab752b03a107ab583d451f433c7eb648760ed79ebb` |
| `modules-v731.tar.gz` | `fc1607efc672b047318936fdada05f33a286815fac46ee6efac05291c6376bbb` |
| final boot | `c8a6c616f60c8ee8f314bfc9e1329c61af3eb070b0cee3724b99080ad3444eaf` |
| final BdsDxe | `f3b946b1660cd444048aba7e5fe434e08a6f41d8dd11cc83f944455fea6855ac` |

## Rollback and remaining work

The previous tested boot is
`E:/edk2-samurai-out/standard-arm64-v731/cmdline-final/boot/boot-eud-production-off.img`
(`236360a31ce397ddceec2eca91b0a4c606d93f754ced0c19325b4c288568ec5e`).
The older production envelope is
`E:/edk2-samurai-out/runtime-20261106-eud-default-off/boot/boot-eud-production-off.img`
(`8d1d6de2a3c63599080a16ded6ced1e410c9434e4e411a969e19b25ff03e690b`).

Still open:

- the embedded test initramfs contains local test credentials and must not be
  published as a generic image;
- cold power-loss boot, actual suspend/resume and 90 Hz switching were not
  re-verified on the source-controlled image;
- RAM/UFS SKU coverage is not proven;
- RPMh read diagnostics still emit `ret=-95` noise;
- the standard ESP/BDS fallback path and persistent UEFI variables are not
  implemented;
- camera and managed high-voltage charging remain separate profiles.
