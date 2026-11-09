# Standard ARM64 Linux v7.3.1 adaptation

Updated: 2026-11-09

This checkpoint turns the Realme X2 Pro (`RMX1931` / `samurai` / SM8150)
from a bring-up tree into a reproducible Linux v7.3.1 platform image. The
deployed hardware uses mainline models and APIs for the exposed platform;
only SoC wiring, regulator sequencing and a small amount of board glue remain
private.

The 2026-11-09 checkpoint closes the persisted Wi-Fi/CDC NCM/SSH work and
the camera driver Selection API gap before moving to the remaining hardware
blocks; the mainline-API, thin-board-layer and safe-flash boundaries are
unchanged.

Settings provenance is now explicit: production keeps postmarketOS/KDE
defaults plus the irreducible board layer. The installed 5-r22 / 4-r10
packages still contain the historical board `samurai-sleep-inhibitor` and
tinydm overrides; the 5-r23 / 4-r11 candidates remove them and restore the
official `sleep-inhibitor` policy. Historical runtime sections below that
name `samurai-sleep-inhibitor` describe the older deployment, not the
production target. See [SETTINGS-PROVENANCE](SETTINGS-PROVENANCE.md).

The PM8150L rear flash is deployed through the standard LED-flash and
V4L2-flash APIs. The current pair keeps boot `5b4dd487…` and DTB
`b244b3f1…` byte-identical while replacing the kernel FAT with
`1f4bbb30…`; it carries Image `f8d89621…`, which removes all three
custom MAX98937/AW8697 `status` attributes. The pair was written from the
running Linux system, read back in full, and passed two ordinary reboots
with the complete 777-module camera, flash/V4L2, Bluetooth, NFC, thermal
and Wi-Fi/NCM/SSH gate. A 200 mA torch increased the S5KGW1 wide RAW mean
from 177.04 to 407.147 with faults 0. A later `loginctl` suspend test using
a direct sysfs RTC alarm left the handset unreachable and is not a suspend
pass; physical wake and an `rtcwake`-based retest remain required.

The NFC block uses the existing mainline `nxp,nxp-nci-i2c` node and Alpine's
standard `neard` userspace. `samurai-platform 5-r22`, `neard-openrc` and the
`neard` daemon are installed. After an ordinary reboot the default OpenRC
runlevel started `neard`, `nfc0` was present, and the
`org.freedesktop.DBus.Properties` plus `org.neard.Adapter` power/poll
methods passed. No physical tag was available, so TagFound/read/write and
eSE remain unclaimed.

The Bluetooth host block now has a separate, reproducible signed module
package: `samurai-bluetooth-host 0.1.0-r0` contains only the mainline
`bnep`, `uhid` and `uinput` modules for the exact `v7.3.1` release. The
configuration delta is exactly `BT_BNEP`, `UHID` and `INPUT_UINPUT`
`n -> m`; all modules are `intree=Y`, have no dependencies. The signed
package is installed; after an ordinary reboot the official `bluez.conf`
and boot-time `depmod -A` path auto-loaded all three modules. `/dev/uhid`,
`/dev/uinput`, the BNEP socket family, BlueZ `hci0` and the full 777-module
runtime gate passed. External PAN/HID peers and cold boot remain open. See
[BLUETOOTH-HOST-MODULES](BLUETOOTH-HOST-MODULES.md).

## 2026-11-09 network checkpoint

The previously flashed camera-final boot is the network baseline:

- boot `9b9be136bd3ee2328f0c4273a829471ad0cd73a7fe7d718825ac024f7af3ae54`;
- Image `aa6c4b6b43ec45f4c41d3d420b980e35876860537cb6f2cb96ec5063aab8432a`;
- DTB `3799ec6c7d3e0c67a657859a37b2fe147fa21a9dedc84d49c8eb83fd8debc805`;
- ordinary-reboot ID `d5cfa04f-5f4e-430a-8bc3-472567bd45f7`, `taint=0`;
- `samurai-platform` 5-r21 installed; UDC `configured`, `usb0` carrier 1,
  configfs `qmult=20` restored by the normal startup path;
- NCM 24/24 bidirectional, 0 failures, 1798.828-second heartbeat;
- Wi-Fi 1810 samples over 1820.51 seconds, max sample gap 1.01 seconds;
- runtime verifier passed with four cameras, two complete RAW frames each,
  100% nonzero, 0% saturated, CAMSS `suspended`, and no kernel fault.

The failure was split cleanly: the old Genesys hub port caused the
`VID_0000&PID_0001` Code 43 enumeration failure, while the direct
motherboard port exposed a separate NCM bulk-IN queue-depth stall. The
latter is fixed with the standard `f_ncm`/`u_ether` configfs `qmult=20`;
no private transport layer was added. Runtime evidence is
`E:/edk2-samurai-out/standard-arm64-v731/camera-r21-final-20261109/runtime-r21.json`
(SHA-256 `d0e8d6059620ae07500ff2e751326fadc8e200f84cf5f0895414e88d45b360a0`).
External-power-removed cold boot, repeated cold boots, a Linux host and
longer transfers remain open.

## 2026-11-09 camera Selection API checkpoint

The camera patch now implements the V4L2 sensor-driver Selection API instead
of relying on libcamera fallback warnings:

- IMX471 `CROP` reports the analogue register window for the selected mode,
  `(8,408)/4640x2644`; default and bounds remain `(8,8)/4656x3496`;
- S5K3M5 supports active and try `CROP`, `CROP_DEFAULT` and `CROP_BOUNDS`,
  all `(0,0)/2104x1560` for its current mode;
- `cam -l` exits 0 with no `Unable to get rectangle` or kernel `EINVAL`.

The two in-tree sensor modules were rebuilt against the unchanged kernel
release, installed atomically, and tested after an ordinary reboot. The new
boot ID is `668b8d20-d22f-44d9-908c-68070eea0147`; Wi-Fi SSH returned in
42 seconds, `taint=0`, and the full runtime verifier passed. The four RAW
paths each produced two complete frames with 100% nonzero and 0% saturated
pixels; frame-to-frame change was 27.058-50.355%. CAMSS returned to
`suspended`, MMCX settled at 128, and libcamera captured one 640x480 RGB888
frame from each of the four cameras.

The patch is now 25 files / 6839 insertions / 285 deletions, tree
`de256d3a46ecb80a80015fc996360127154bfe65`. The superseding module archive
contains 773 stripped modules; a byte comparison confirms that only
`imx471.ko` and `s5k3m5.ko` changed from the previously accepted 773-module
tree. Evidence is in
`E:/edk2-samurai-out/standard-arm64-v731/camera-selection-fix-20261109/`.
The ordinary reboot is not a cold-boot proof.

Machine-readable identities and hashes are in
[`../dts/v731/source-lock.json`](../dts/v731/source-lock.json). The frozen
hardware view is in
[`../dts/samurai-dt-v1-abi.json`](../dts/samurai-dt-v1-abi.json).
The startup timing audit is in
[`STARTUP-LATENCY-AUDIT.md`](STARTUP-LATENCY-AUDIT.md).

## 2026-11-08 runtime result (historical)

The deployed standard-rootfs pair now carries the promoted DWC3 FIFO-resize
DTB and passed a new ordinary-reboot runtime gate:

- release: `7.3.1-rmx1931-samurai-v731`;
- boot partition SHA-256:
  `7f8d7a65a3c450fd6abd2a41c5d4e1f359ffe4f7b66a36e53e4ec7aea2782777`;
- kernel FAT SHA-256:
  `1f3a40f4e02ae67e2e7ada9029592a539e74be65905a1e54562f68c9e65550c4`;
- `/samurai.dtb` SHA-256:
  `c9f948cdac6e58b23ba5bd9bb29137d6266154ce22540fb4d585e24826649fc5`;
- last verified ordinary-reboot ID after the SSC fix:
  `f6113e67-cee2-4708-b2cd-c004344e0eb0` (the later no-flag clock kexec
  preflight left the handset awaiting a physical power cycle); camera
  acceptance boot: `1b9dacbc-7ac1-4600-8738-8dfee46f5206`;
- `taint=0`; F2FS `userdata` is `/`, PID 1 is `/sbin/init`;
- UDC `configured`; both `10.42.0.1/24` and `169.254.42.1/16` are present;
- CAMSS, CCI, four sensors, lens and both PM8008 instances probe;
- `tinydm`, `sshd`, `samurai-usb`, `samurai-sleep-inhibitor`, KWin and
  plasmashell are running;
- the live FDT contains `tx-fifo-resize`;
- the full runtime JSON, including two complete RAW frames from every camera,
  is
  `E:/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/runtime-camera-r17.json`
  (SHA-256
  `41842ca39a1eb24b5753bdecc49701ea88874515df549bc726fa36dab88df291`).
  The front, rear, telephoto and wide frames are 100% nonzero, 0% saturated,
  and 28.0-48.5% changed between the two frames.

`samurai-platform 5-r17` replaces the fixed 45-second Wi-Fi soak with a
bounded poll of the standard MPSS state. Measured from the reboot request to
first SSH on the same ordinary reboot: Wi-Fi about 57 seconds (about 26
seconds after kernel start), NCM about 37 seconds (about 7 seconds after
kernel start), versus about 101 seconds for Wi-Fi before the change.
The device-side dmesg for the r17 regression shows `wlan0` association at
24.68 seconds and first Wi-Fi SSH at about 26 seconds of uptime. The later
86.6-117 second host-side results are therefore an AP/DHCP/host-link
variation, not the removed board sleep.

The same latency pass removed an independent fixed 20-second wait in
`samurai-ssc`. It now waits for the standard QRTR SSC service 400 and retries
the real accelerometer/light readiness probes. On boot `f6113e67...` the
FastRPC device appeared at `03:49:13.408`, the first real sensor probe
completed at `03:49:19.084`, and the OpenRC `default` runlevel completed in
26 seconds versus 42 seconds before. The boundary and skip-camera runtime
gates passed with `taint=0`, CAMSS `suspended`, MMCX 128 and all four camera
media entities present. Device-side `WIFI_READY` remained about
18.5-18.8 seconds; later host-side Wi-Fi first-SSH timings varied from about
87 to 117 seconds while NCM stayed near 33.8 seconds, so AP/DHCP/host-link
variation remains open and is not attributed to the removed sleeps.

The earlier camera-enabled envelope passed three complete boot cycles and
remains the camera acceptance baseline:

- release: `7.3.1-rmx1931-samurai-v731`;
- boot partition SHA-256:
  `9b9be136bd3ee2328f0c4273a829471ad0cd73a7fe7d718825ac024f7af3ae54`;
- first boot ID: `c97a0a52-60e7-41fc-bf49-59c7ff0d3fc5`;
- ordinary-reboot ID: `9b93d2c2-7bd9-45aa-90a2-1af71c32d6b3`;
- `poweroff`-initiated re-power ID:
  `35915162-7912-4cb2-a766-88691cbd44bc`; USB stayed attached, so this is
  not yet a manually keyed, external-power-removed cold boot;
- `taint=0`;
- three remoteprocs `running`;
- `sensor-power` reports `vdd=1 vddio=1`;
- UDC `configured`;
- `bq28z610-0` and `mp2650-input` bind through `power_supply`;
- DSI `connected`; normal compositor timeout-off is accepted, and
  `kscreen-doctor --dpms on` restores `enabled/On`;
- `tinydm`, `sshd`, `samurai-usb`, `samurai-sleep-inhibitor`, KWin and
  plasmashell start after all three boots;
- KWin/KMS switched `1080x2400` between 60 and 90 Hz with zero fault-pattern
  matches;
- a clean 15-second RTC `s2idle` cycle resumed with the same boot ID,
  `success=3 fail=0`; tinydm, KWin and Plasma survived, and all four cameras
  passed another RAW capture after resume.

The boot and logdump partitions and FAT `Image`/`samurai.dtb` were read back
on the device and match their source-locked hashes. The runtime evidence
endpoint is the local Wi-Fi SSH link; the test image is not a distributable
generic image. All three boot cycles produced the full camera and platform
acceptance JSON, with `taint=0`.

A later reboot (`6df4a965-4ca2-4a1b-97c5-35b60dac14c3`) restored the
production runtime after a boot-order failure in the previous cycle. The
skip-camera verifier passed with the same production boot/Image/DTB hashes,
773 modules, `camss=suspended`, `taint=0`, Wi-Fi SSH and re-enumerated USB
NCM. This is a recovery/recheck, not a replacement for the three complete
camera cycles above.

The same boot's post-install runtime recheck is
`current-runtime-after-service-fix-20261108.json` (SHA-256
`6fcf5b0da5ec96a93f75ac271e6a58ba8684a91a43574e31dea3f85b09d67746`).
It passed every skip-camera check with `mmcx=128` while the display was on,
and both Wi-Fi and NCM were reachable. The USB NCM baseline also completed:
24/24 bidirectional `64K/256K/1M/4M` transfers passed, followed by 1800
seconds of heartbeat; the independent verdict SHA-256 is
`7fd449305cdc084f8735f44d75948ac1ac40f09fdc9ff0bbbb3af6a4ac63c31a`.
This is a current-boot baseline, not a multi-boot or long-idle proof.

The WiFi power model was checked against the decompiled same-handset DTB.
The stock `wifi@18800000` node binds four standard regulator consumers:
`vdd-0.8-cx-mx`, `vdd-1.8-xo`, `vdd-1.3-rfa` and `vdd-3.3-ch0`; the
deployed DTB already carries the same four PMIC phandles. The explicit
wrapper reconstruction in
`E:/edk2-samurai-out/standard-arm64-v731/wifi-supply-dtb-candidate-r2/`
builds to the identical DTB SHA-256 `3799ec6c…`, so this is a source
consistency fix, not a runtime change. `ath10k_snoc` still requests an
optional fifth `vdd-3.3-ch1`; that rail is absent from the stock DTB and
falls back to a dummy regulator. It is not evidence of the earlier SSH
disconnects.

The prior OpenRC failure was addressed at the board-package boundary rather
than by another reboot: `samurai-usb` now loads the standard `socinfo`
driver and waits up to 60 seconds for the numeric SoC serial;
`samurai-wifi` has bounded 120-second source/WLAN waits; NetworkManager,
sshd and SensorProxy use ordered soft dependencies; SSC waits up to 30
seconds for SLPI and 90 seconds for FastRPC. The resulting
`samurai-platform 5-r16` (`a8be7466…`) and `samurai-desktop 4-r8`
(`48730e82…`) are installed. The platform package adds the standard
`dnsmasq` USB NCM DHCP path while retaining the legacy
`169.254.42.1/16` debug address. A controlled ordinary reboot after installation
produced boot ID `3f9f8649-931e-40f2-b0da-60a1f889ae29`; the
service-boundary gate and skip-camera runtime verifier both passed, all eight
core services started, and the production boot/Image/DTB/module hashes
remained unchanged. Wi-Fi SSH recovered in about 80 seconds. NCM SSH needed
roughly four minutes for Windows link-local/NCM enumeration to converge, then
passed the complete four-size bidirectional single-iteration matrix (8/8) and
a 60-second heartbeat. Evidence is in
`E:/edk2-samurai-out/standard-arm64-v731/post-service-fix-reboot-20261108/`
and `E:/edk2-samurai-out/standard-arm64-v731/ncm-post-reboot-20261108/`.
This validates the service ordering on a new boot, but not an
external-power-removed cold boot or multiple boot cycles.
The same boot also passed a four-camera RAW regression: two complete frames
per camera, every frame 100% nonzero, 0% saturated, and 38-60% changed pixels
between frames. The RAW evidence remains private outside the public tree.

## Standard rootfs (flashed and booted)

The paired standard-rootfs boot and kernel FAT are flashed on the handset.
This removes the diagnostic initramfs and host-specific ftrace bootconfig,
then mounts the existing postmarketOS F2FS `userdata` directly:

```text
console=tty0 loglevel=4 panic=15 root=PARTLABEL=userdata rootfstype=f2fs rootwait rw clk_ignore_unused
```

| Artifact | SHA-256 |
| --- | --- |
| `Image-v731-standard` | `5069b1b47d453b11f11ce4a831de6821971b064184452303d4373ae7c8fbd2bd` |
| production DTB | `c9f948cdac6e58b23ba5bd9bb29137d6266154ce22540fb4d585e24826649fc5` |
| deployed FIFO boot | `7f8d7a65a3c450fd6abd2a41c5d4e1f359ffe4f7b66a36e53e4ec7aea2782777` |
| deployed kernel FAT | `1f3a40f4e02ae67e2e7ada9029592a539e74be65905a1e54562f68c9e65550c4` |
| initial standard-rootfs boot (rollback) | `e1cccd9d3d1119c2b40bda4d15834ea857ca8ec897e611f9af28b1e66050bd19` |
| initial kernel FAT (rollback) | `8a684871daa9b32d38c0c514e21b7d6b5076a280b35f9ae236821d040ffa46cf` |
| candidate BdsDxe | `54a56caa564a90f573e3bf7bbf5e12c9261c85c754bfeaff274ad8c05a1224d9` |
| `samurai-standard.config` | `036776433109197b01f249b130e838aa655cd76357962d0624ed376cb6aa6cb2` |
| candidate manifest | `5964daeb5fe8fb642a731a4f0dafcc02c6a7f484fa4906e430e48fc11b332a94` |

The generated kernel still includes the 512-byte mainline default initramfs
archive, whose only entries are `/dev/console` and `/root`. It contains no
test files, credentials, diagnostic script, or bootconfig. The FAT passed
`fsck.vfat -n`; `/Image` and `/samurai.dtb` read back match the hashes above.
The BDS metadata review is `printable_metadata_only`; `PlatformSmbiosDxe` and
`UiApp` are byte-identical to the tested source boot.

The deployment is pair-scoped. The boot image supplies the firmware DTB and
command line, while the `logdump` FAT supplies the matching Image and DTB.
Partial deployment is rejected by the current helper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\linux-port\scripts\flash-v731-usb-fifo-pair.ps1 `
  -FlashBoot -FlashKernelFat -Reboot
```

After boot, run the on-device verifier with the standard-rootfs profile. It
requires the exact command line above, `PARTLABEL=userdata` mounted as F2FS
on `/`, and `/sbin/init` as PID1, in addition to the normal hashes, cameras,
power, display, USB and service checks:

```sh
python3 linux-port/scripts/verify-v731-final-runtime.py \
  --usb-fifo --output /tmp/v731-usb-fifo-runtime.json
```

The FIFO pair has been flashed and booted on the handset. Boot `f26c6cdc…`
passed the `--usb-fifo` runtime verifier with exact
boot/FAT/Image/DTB hashes, F2FS `userdata` root, `/sbin/init` PID1,
`taint=0`, CAMSS/media, all four RAW cameras, power, display, USB, Wi-Fi and
desktop checks.
Evidence is
`E:/edk2-samurai-out/standard-arm64-v731/usb-fifo-production-source-20261108/runtime-camera-after-pair-20261108.json`
(SHA-256
`671f28b85dbf163e77762b4d3e068ed536db63bd55ff2001af17cff076b6aceb`).
The camera-final and initial standard-rootfs pairs remain rollback images.

## Standard UEFI boot candidate (not flashed)

A second offline candidate moves the normal OS boot decision to the standard
UEFI removable-media path:

```text
ABL -> BootShim/EDK2 -> BdsDxe
    -> \EFI\BOOT\BOOTAA64.EFI on the FAT containing /Image
    -> GRUB standalone
    -> Linux EFI stub + /samurai.dtb
    -> root=PARTLABEL=userdata rootfstype=f2fs
```

BdsDxe now checks `\EFI\BOOT\BOOTAA64.EFI` first and passes no LoadOptions;
the embedded GRUB configuration owns the command line and the device tree.
GRUB discovers the volume with `search_fs_file` against `/Image`; the FAT
label is not a boot prerequisite.  The source configuration is tracked at
[`../uefi-standard/grub.cfg`](../uefi-standard/grub.cfg).
If the standard boot manager is absent or returns, BdsDxe falls back to the
existing direct `/Image` path with the board command line. The fallback is
deliberate: it keeps the current recovery entry while the standard path is
being validated.

| Artifact | SHA-256 |
| --- | --- |
| UEFI candidate boot | `c5e856d5ac06a42fb55df909dae26fe26293517aa65fd67570730f6de068690c` |
| UEFI candidate FAT | `7c326ad4dd6f3c3682bd047554534bb4cb94eddec818b7cbbe69a0ada7ed3131` |
| UEFI BdsDxe | `f5cf8a7efcce6208ef48250928880214ae25807ea92c17e0d896547f87f57206` |
| GRUB `BOOTAA64.EFI` | `97ef936d2b44c3ed69504d9a5ec1e15c525ba3ba3a1053fa457788f191886170` |
| `grub.cfg` | `f0f9911b10bfd5884157c50350bd4ac36fd82cf12a9573d25658c4bc5fe4d4f9` |
| UEFI candidate manifest | `603f90ce630e47ca1e83f700072b4100312b9964b3f896adfbcaf6b8124ce7c4` |

GRUB is a standalone ARM64 EFI image built from Ubuntu
`grub-efi-arm64-bin 2.14-2ubuntu1` modules. `grub-script-check` and the ARM64
PE check passed; the FAT passed `fsck.vfat -n`; `/Image`, `/samurai.dtb` and
`/EFI/BOOT/BOOTAA64.EFI` read back match. Only the BdsDxe FFS changed among
the 101 main FFS files; `PlatformSmbiosDxe` and `UiApp` remain identical, and
the PE32 inserted into the boot image matches the newly built BdsDxe.  The
volume is still labelled `KERNEL` for compatibility with existing tooling,
but neither BDS nor GRUB requires that label.

The pair is deployed with
[`../scripts/flash-v731-uefi-standard.ps1`](../scripts/flash-v731-uefi-standard.ps1).
It rejects either partition alone. This candidate is **offline built only**;
handset GRUB execution, root mount and rollback are still unverified.

## Kernel source identity

The v7.3.1 source was imported from the official tarball, then split into two
commits:

| Item | Value |
| --- | --- |
| tarball SHA-256 | `fa595aad93734f829c963c2a90ef7c3673224fd7fdae7b49406e397cde2de231` |
| baseline commit | `09455be5a5c3421019315de48a32c9ded91d0030` |
| platform commit | `824dc0a56143d8bf1cc1d20adb877abced48b336` |
| platform tree | `fbbf939a98426cd45e08b4d7a42bcadfbf900d39` |
| camera patch tree | `de256d3a46ecb80a80015fc996360127154bfe65` |

The platform commit is stored as
[`../patches/v7.3.1/0001-arm64-add-standard-samurai-platform-glue.patch`](../patches/v7.3.1/0001-arm64-add-standard-samurai-platform-glue.patch)
(SHA-256
`dcdb7c70f74bfa75888733aa20a836530635ff788e137d9a073364d847d2dbcf`).
The camera/CCI/PM8008 work is stored as
[`../patches/v7.3.1/0002-arm64-standardize-samurai-camera-stack.patch`](../patches/v7.3.1/0002-arm64-standardize-samurai-camera-stack.patch)
(SHA-256
`964cd13b3bb52d0b4977b94cbcd1aeea454fbb368dd4b34818ab821be913b38f`,
26 files, 6860 insertions and 285 deletions).
The thin-private-layer audit also removes the two custom read-only `status`
sysfs files from the MAX98937 and AW8697 board drivers. They were not part of
ASoC or input-force-feedback UAPI, and current diagnostics use ALSA controls,
input/ff and kernel logs. The deletion is
[`../patches/v7.3.1/0004-samurai-remove-private-status-sysfs.patch`](../patches/v7.3.1/0004-samurai-remove-private-status-sysfs.patch)
(SHA-256
`f69ffecd482d11c19f25f074ed5d2ccc48ac765acbf22c54956701bdd0497a5c`).
The final deployed Image is `f8d89621…`; the paired FAT is
`1f4bbb30…`, based on the accepted flash/V4L2 FAT and with only
`/Image` replaced. Boot `5b4dd487…` and DTB `b244b3f1…` remain unchanged.
Two ordinary reboots passed the full 777-module runtime gate, all three
custom status nodes are absent, standard ALSA playback/capture and AW8697
input/FF remain present, and `taint=0`. The verifier report is
`E:/edk2-samurai-out/standard-arm64-v731/thin-private-final-20261109/verification.json`.
The attempted suspend/resume is **not** accepted; see the recovery note in
`NEXT-SESSION.md`.

## NFC userspace boundary

The NFC controller is exposed through the in-tree `nxp-nci_i2c` driver and
the standard `nfc0` device. The board package does not add a private NFC
driver or ioctl. It only selects the Alpine `neard` 0.20 package and its
upstream OpenRC service, which talks to the controller through the kernel
NCI interface and exposes the standard `org.neard` D-Bus API.

The deployed userspace set is:

- package `samurai-platform 5-r22`, SHA-256
  `bc3f6d59d1aaf5ae800bc512205b1cbd5da71a3412a64ac651396a4d8ba82f51`;
- package index SHA-256
  `273e3992322030d9e006a235778d4831bd8262044d7110ad8d68680410c05a8b`;
- official `neard 0.20-r0` APK, SHA-256
  `027df5f8637a1fd50f34abba456b9c96ec838af53d4f09cb8d7bf16168487069`;
- signer public key and package manifest in
  `E:/edk2-samurai-out/standard-arm64-v731/nfc-neard-20261109/`.

`test-nfc-neard.py` checks `nfc0`, the OpenRC service and the standard
`org.freedesktop.DBus.Properties` and `org.neard.Adapter` methods through
`dbus-send`/`dbus-monitor`. After an ordinary reboot with boot ID
`3331ca80-078d-4dda-935a-902d271cbea1`, `neard` auto-started and power,
polling and cleanup passed. A physical tag is required for `--expect-tag`;
without one the probe reports no tag rather than treating controller binding
as read-card acceptance.
The exact build configuration is
[`../configs/v7.3.1/samurai.config`](../configs/v7.3.1/samurai.config)
(SHA-256
`9c99cfc3a14c075586c39692ae92fd6975f49a5afa1ee8a510cead4206cb39d1`).
The direct-rootfs candidate uses
[`../configs/v7.3.1/samurai-standard.config`](../configs/v7.3.1/samurai-standard.config)
(SHA-256
`3782156ba0359c41367b2a9797a8f4bf25d2574c1ab433db869e607ac783b708`;
generated `.config` SHA-256
`d3dc6f072055a7d9da50de7c1e5416da837c680c00126f9a8f25b379f9984097`).

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

The production BdsDxe image is 110592 bytes, SHA-256
`f3b946b1660cd444048aba7e5fe434e08a6f41d8dd11cc83f944455fea6855ac`.
The direct-rootfs candidate BdsDxe is also 110592 bytes, SHA-256
`54a56caa564a90f573e3bf7bbf5e12c9261c85c754bfeaff274ad8c05a1224d9`;
its review changed only printable command-line metadata.
The UEFI standard-boot candidate BdsDxe is 110592 bytes, SHA-256
`f5cf8a7efcce6208ef48250928880214ae25807ea92c17e0d896547f87f57206`.
Its metadata review is `requires_manual_review` because the BDS code itself
changed; only the BdsDxe FFS differs, while `PlatformSmbiosDxe` and `UiApp`
remain byte-identical.
The source platform rebuild changed only the BdsDxe FFS among the 101 main-FV
files. On top of that tested BDS, the camera candidate changes only the
mainline DTB FFS `25462cda-221f-47df-ac1d-259cfaa4e326`; the other 100 main
FFS files, including BdsDxe, the compatibility DTB, shim and ramdisk are
preserved. The metadata review classification is
`printable_metadata_only`.

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

For the audit, the primary diagnostic is the one-line
`CLOCK_ALLOW_WRITE_DEBUGFS` patch plus a per-clock debugfs sweep. A no-kexec
fallback is
`linux-port/diagnostics/gcc-clk-gate-sweep.py`: it toggles the extracted GCC
branch gates through `/dev/mem` while the production kernel stays up, skips
`gcc_cpuss_rbcpr_clk` unless `--include-critical` is passed, and uses a
20-second watchdog. It is diagnostic only and must not ship as a fix.

The clock candidate is
[`0003-clk-qcom-gcc-sm8150-keep-cpuss-rbcpr-critical.patch`](../patches/v7.3.1/0003-clk-qcom-gcc-sm8150-keep-cpuss-rbcpr-critical.patch)
(SHA-256 `3955ff1e889a0ae8c42e8356615bcbc6bcbafe900a615fb958080bf4982ff203`).
It marks only `gcc_cpuss_rbcpr_clk` as `CLK_IS_CRITICAL`; the clock has
0 enable / 0 prepare counts, hardware enable asserted, no Linux consumer,
and the adjacent CPUSS gates are already critical.

The complete candidate is staged at
`E:/edk2-samurai-out/standard-arm64-v731/clock-rbcpr-candidate`:

| Artifact | SHA-256 |
| --- | --- |
| `Image-v731-clock-rbcpr` | `9d50f46424a64c9ce7ff5277ea2abab18480df1b23a78c7d2199a9bc261d925e` |
| clock GRUB `BOOTAA64.EFI` | `81fba9922e74259001495ae1ae7368744f940d6b9e2d4c3feeaf173fd0459887` |
| clock `grub.cfg` | `2cce9fa843c64956a72f124c22e77284e550395ef496195e4c5cce8bc99a9b6b` |
| clock kernel FAT | `3e788ccbf9fa598f43c25be7747a0571742e21df18b4bb8f5917def2ed65117a` |
| paired boot carrier | `c5e856d5ac06a42fb55df909dae26fe26293517aa65fd67570730f6de068690c` |

The candidate command line is exactly:

```text
console=tty0 loglevel=4 panic=15 root=PARTLABEL=userdata rootfstype=f2fs rootwait rw
```

It intentionally contains no `clk_ignore_unused`. A clean-source object
rebuild proves that only the patched object changes the locked clock flags:
the baseline object has `0000000000000000` at the recorded layout offset and
the patched object has `0008000000000000` (`BIT(11)`, `CLK_IS_CRITICAL`).
The offline verifier also checks the ARM64 GRUB image, file-based `/Image`
discovery, absent safety flag, FAT `fsck.vfat -n`, all three FAT member hashes,
the BDS PE32 hash in the boot carrier, and the paired-write flash helper.

This is **offline built and object-proof verified, not flashed**. A
no-`clk_ignore_unused` kexec preflight using a rewritten live FDT loaded the
image and armed the watchdog, but the handset did not return over Wi-Fi, NCM
or fastboot for more than 255 seconds. The persistent boot/FAT were
unchanged, but a physical power cycle was required. Therefore this is not a
claim that the constraint can be removed, and kexec is not a safe unattended
rollback. The independent offline check is
`linux-port/scripts/verify-clock-rbcpr-candidate.py`; after flashing, run:

```sh
python3 linux-port/scripts/verify-v731-final-runtime.py \
  --clock-rbcpr --output /tmp/v731-clock-rbcpr-runtime.json
```

The runtime profile requires the exact command line without
`clk_ignore_unused`, F2FS `userdata` root, `/sbin/init` as PID1, and
`gcc_cpuss_rbcpr_clk` to expose `CLK_IS_CRITICAL` with prepare/enable counts
1 and hardware enable `Y` before accepting the change.

Resume checklist after the diagnostic detour:

1. Physically power-cycle the phone after the failed preflight and confirm
   the production boot ID, `taint=0`, Wi-Fi SSH, and boot/FAT hashes before
   changing anything.
2. Run `gcc-clk-gate-sweep.py --list`, then the sweep without
   `--include-critical`; keep Wi-Fi SSH as the control channel. A reset is
   expected to return to the production boot because FAT `/Image` was not
   modified.
3. Do not rerun kexec without physical access to a power button. If physical
   access is available, use the guarded
   `linux-port/diagnostics/run-kexec-standard-smoke.sh` with an explicitly
   rewritten live FDT; run the debugfs per-clock sweep for the
   CAMCC/DISPCC/DSI/RPMh remainder only under that condition.
4. Fix the first hanging clock with a real consumer, or with the narrowest
   `CLK_IS_CRITICAL`/`CLK_IGNORE_UNUSED` annotation justified by the provider;
   rebuild and test without `clk_ignore_unused`.
5. Separately compare `restart-bootloader-clean.py` against the old
   `RESTART2("bootloader")` path for the warm-reboot fastboot enumeration
   issue.

## Standard interfaces

The v7.3.1 image uses:

- standard `mps,mp2650` and `ti,bq28z610` `power_supply` devices;
- the generic `qcom,sm8150-dwc3` / `qcom,snps-dwc3` USB model, UDC class and
  configfs gadget;
- the generic remoteproc prepare/unprepare subdevice lifecycle for the SLPI
  sensor rails;
- the standard CAMSS/CCI/media-controller/subdev/V4L2 RAW capture path for
  IMX471, IMX319, S5K3M5 and S5KGW1;
- the standard PM8008 MFD/regulator API with a thin board address sequencer;
- DRM/KMS and backlight class for the panel;
- ASoC/ALSA PCM and UCM for audio;
- evdev, input force feedback and standard udev/feedbackd discovery;
- IIO and SensorProxy for sensor consumption.

The retained board-specific code is intentionally narrow:

- SM8150 and samurai DTS wiring;
- the sensor-power regulator sequencer;
- the SM8150 CAMSS resource table and MMCX performance vote;
- the PM8008 dual-address board sequencer and four sensor profiles;
- the sofef03f panel description;
- the AW8697 haptics board driver;
- MAX98937 and samurai ASoC board glue.

Fingerprint is deliberately not represented as a standard peripheral in
this image. The Android 19781 source describes a Goodix `goodix_fp` node
with power, reset and interrupt GPIOs plus `ldo7-supply`, but no Linux
data bus; the vendor HAL performs capture and matching through a signed
TrustZone applet/QSEECom. Mainline has no equivalent secure applet loader
or fingerprint class, so adding a private `goodix_fp`, `spidev`, or fake
input node would misrepresent the hardware and would not authenticate
anything. The functional fingerprint chain remains intentionally outside
the standard OS image until a mainline-compatible secure path exists.

The image includes the standard V4L2 CAMSS camera path, but not the camera
ICP userspace experiment, APSD/private USB-input charging, private
managed-charging kernel modules, production EUD serial ownership, vendor root
compatibility properties or private `samurai_diag` trace dependencies.

The old `samurai-charging` package is now a legacy explicit-opt-in experiment.
`samurai-platform` 5-r14 no longer depends on it; the standard image relies on
the kernel charger/gauge bindings and the standard `power_supply` class.

## Camera acceptance

The four cameras use the upstream CAMSS/CCI/media-controller/V4L2 model. On
the final boot, all sensors auto-probed and two complete private RAW frames
were captured from each path in all three acceptance boot cycles:

| Camera | Sensor | Media path | Format | Two-frame bytes |
| --- | --- | --- | --- | ---: |
| front | IMX471 | `csiphy2 -> csid0 -> vfe0_rdi0` | `SRGGB10_1X10/1928x1088`, `pRAA` | 5257216 |
| rear | IMX319 | `csiphy1 -> csid0 -> vfe0_rdi0` | `SRGGB10_1X10/1632x1224`, `pRAA` | 5013504 |
| tele | S5K3M5 | `csiphy3 -> csid0 -> vfe0_rdi0` | `SGRBG10_1X10/2104x1560`, `pgAA` | 8236800 |
| wide | S5KGW1 | `csiphy0(C-PHY) -> csid0 -> vfe0_rdi0` | `SGBRG10_1X10/4608x3456`, `pGAA` | 39813120 |

All 24 decoded frames were complete, 100% non-zero, unsaturated, and differed
within each pair. While streaming, CAMSS was active with MMCX at 384; after
stream-off CAMSS returned to `suspended`. MMCX returned to 128 with the
display on or 64 with the display powered off, both normal idle states. Each
run ended with `taint=0` and no new warning. The scene RAW files and hashes
remain private; the repository records only dimensions, structure and
validation results.

The reproducible harness is
[`../scripts/test-camera-four-raw.sh`](../scripts/test-camera-four-raw.sh) plus
[`../scripts/verify-camera-raw.py`](../scripts/verify-camera-raw.py). It
discovers sensor entities by model because CCI bus numbers can change between
boots; hard-coded `i2c-N` names are not ABI. The verifier has an optional
numpy path and a standard-library fallback that matched it exactly on the
host.

The final Selection API pass adds an explicit driver contract:

- `VIDIOC_SUBDEV_G_SELECTION` succeeds for IMX471 and S5K3M5 on `CROP`,
  `CROP_DEFAULT` and `CROP_BOUNDS`;
- libcamera 0.7.2 enumeration emits no rectangle/EINVAL errors;
- `runtime-selection.json` and the final runtime verifier require the two
  sensor module hashes as well as the camera topology and RAW checks.

This removes a real userspace fallback, but does not claim AF/AWB/LSC,
recording, concurrent streams, thermal behavior or image quality.

## PM8150L flash-LED/V4L2 final

The stock camera DTS wires the rear dual-LED flash to PM8150L channels 0
and 1 (`flash0`/`flash1`, `torch0`/`torch1`, switch 3). The final deployment
uses only the existing `qcom,pm8150l-flash-led` binding,
`drivers/leds/flash/leds-qcom-flash.c` and
`drivers/media/v4l2-core/v4l2-flash-led-class.c`. S5KGW1 links the emitter
with the standard `flash-leds` property so the flash subdevice enters the
CAMSS media graph:

- DTB `b244b3f10a14811dca2e808efa8c840f432cac69020e66b60eba97d02794a18e`;
- boot `5b4dd4871f6856710ff58e722ffd8b2c30d04baf0104b262adcb02e46a7651bf`;
- kernel FAT `c99c690ee923238b0954975682c0e40ce99ae63afd048d40b5059fea70e5862e`;
- stripped baseline modules archive `c12a0513caf664200e1df47da5061b227090ffe8cf8d3586030cdbb9241a8b30`, 774 modules; after installing the signed Bluetooth host package the runtime tree has 777.

The boot image changes only the DTB FFS GUID
`25462cda-221f-47df-ac1d-259cfaa4e326`; BDS remains
`f3b946b1660cd444048aba7e5fe434e08a6f41d8dd11cc83f944455fea6855ac` and the
other 100 main FFS are byte-identical. The FAT keeps the deployed
`Image` `aa6c4b6b…` and replaces `/samurai.dtb`.

The final pair was written from the running Linux system, not fastboot.
`flash-pair-linux.sh` resolves `boot`/`logdump` by GPT label, verifies exact
image size and SHA-256, refuses mounted or read-only targets, writes
`logdump` first, reads back the whole partition, then writes and reads back
`boot`:

```powershell
pwsh -File .\linux-port\scripts\flash-v731-pair-linux.ps1
pwsh -File .\linux-port\scripts\flash-v731-pair-linux.ps1 `
  -FlashBoot -FlashKernelFat -Reboot
```

The actual write is recorded in
`E:/edk2-samurai-out/standard-arm64-v731/flash-led-v4l2-20261109/flash.log`;
both partition readbacks equal the expected values. Run the post-boot gate
with:

```sh
python3 linux-port/scripts/verify-v731-final-runtime.py \
  --flash-led-v4l2 \
  --scripts-dir /tmp/v731-verify \
  --output /tmp/v731-flash-led-v4l2.json
```

The first ordinary reboot changed the boot ID to
`364abb2c-8521-49a5-957e-77bdc37e426a`; NCM SSH returned in 36.761 seconds
and Wi-Fi SSH in 59.327 seconds. The post-reboot gate required 774 modules,
exact partition/Image/DTB/module hashes, four cameras with two complete
unsaturated frames each, thermal trips/cooling devices, the `white:flash`
entity and V4L2 controls, CAMSS `suspended`, MMCX 128 and `taint=0`.

After installing the signed `samurai-bluetooth-host 0.1.0-r0` package the
next ordinary reboot reached boot ID
`071abbb5-88bd-4c8a-879a-ab9906387617`. The official `bluez.conf` loader
and boot-time `depmod -A` path brought up `bnep`, `uhid` and `uinput`
without manual intervention; `/dev/uhid`, `/dev/uinput`, the BNEP socket
family and BlueZ `hci0` were present. The `--bluetooth-host` full gate
passed with 777 modules, four RAW camera pairs, flash/V4L2, thermal,
network and services; NCM SSH returned in 39.764 seconds and Wi-Fi SSH in
64.487 seconds. No external PAN or HID peer was available, so those
business paths remain unclaimed.

The standard LED class and V4L2 flash controls both work. At
`intensity_torch_mode=200000` the S5KGW1 wide RAW mean rose from 177.04 to
407.147 (`+130%`), with 0% saturated pixels and 93.851% of pixels changed;
`faults=0`, `led_mode` returned to 0 and `strobe_status` returned to 0.
The RAW files and hashes stay in the private evidence directory and are not
published. External-power-removed cold boot, repeated cold boots and long
flash thermal endurance remain open.

## DTB contract check

The previous camera-final DTB was 114395 bytes, SHA-256
`3799ec6c7d3e0c67a657859a37b2fe147fa21a9dedc84d49c8eb83fd8debc805`.
The deployed flash/V4L2 DTB is 114656 bytes, SHA-256
`b244b3f10a14811dca2e808efa8c840f432cac69020e66b60eba97d02794a18e`.
The updated contract declares 24 resources, including the standard MP2650
charger, DWC3 wrapper, CAMSS, both CCI controllers, four RAW sensors, the
wide-camera lens, both PM8008 instances and the PM8150L flash controller:

```text
passed=true
resources_declared=24
resources_checked=24
failures=0
warnings=1  # explicit additive-only change
```

The contract remains deliberately not frozen for multi-SKU, cold-boot and
suspend/resume coverage. Flash probe, LED/V4L2 control, optical output,
runtime PM, private-status removal and two ordinary-reboot cycles are now
device-proven. The current suspend attempt is explicitly not accepted:
direct sysfs RTC arming plus `loginctl suspend` did not recover. Cold boot,
long-thermal and an `rtcwake` retest remain open.

## Reproduce the image

On the Linux build host:

```sh
git clone --branch codex/v7.3.1-samurai <kernel-worktree>
git -C <kernel-worktree> checkout 824dc0a56143d8bf1cc1d20adb877abced48b336
git -C <kernel-worktree> apply \
  <repo-root>/linux-port/patches/v7.3.1/0002-arm64-standardize-samurai-camera-stack.patch
cp linux-port/configs/v7.3.1/samurai.config <build-dir>/.config
export LOCALVERSION=
export KBUILD_BUILD_VERSION=4
export KBUILD_BUILD_TIMESTAMP='Fri Nov  6 17:14:18 CST 2026'
# Run this from the same login environment used to build the deployable tree.
# In this environment rustc is in ~/.cargo/bin; a non-login shell discovers 0.
make -C <kernel-worktree> O=<build-dir> ARCH=arm64 \
  CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make -C <kernel-worktree> O=<build-dir> ARCH=arm64 \
  CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image dtbs modules
grep -E '^CONFIG_(I2C_QCOM_CCI|V4L2_CCI|VIDEO_(IMX319|IMX471|S5K3M5|S5KGW1|LC898219XI))=' \
  <build-dir>/.config
grep -E '^#define CONFIG_(I2C_QCOM_CCI|V4L2_CCI|VIDEO_(IMX319|IMX471|S5K3M5|S5KGW1|LC898219XI))_MODULE' \
  <build-dir>/include/generated/autoconf.h
```

`LOCALVERSION=` is deliberate: without it the uncommitted camera worktree
gets a trailing `+`. Use a fixed absolute `O=<build-dir>` path: the Image
contains a GNU build-id note whose hash is sensitive to the output path.
The build identity above reproduces the recorded release banner, but not
yet the deployed `aa6c4b6b…` Image; see the offline rebuild probe for the
remaining provenance gap.

For the standard-rootfs candidate, substitute
`samurai-standard.config` in the same fixed output path and keep the camera
patch applied. Its Image hash is `5069b1b4…`; it differs from the camera
Image by the initramfs and bootconfig options, not by the camera/module ABI.
The candidate boot is built from the tested camera boot with the new BDS and
the existing camera DTB:

```sh
python3 linux-port/scripts/build-eud-off-bds.py \
  --source <candidate>/PlatformBm.c --output <candidate>/bds --execute
python3 linux-port/scripts/build-boot-larger.py \
  --boot <camera-final-boot>/boot-eud-production-off.img \
  --bds <candidate>/bds/BdsDxe.efi \
  --dtb <camera-final-boot>/sm8150-samurai-v731-camera.dtb \
  --output <candidate>/boot --execute
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

The v7.3.1 binaries produced by this checkpoint are deployed:

| Artifact | SHA-256 |
| --- | --- |
| `Image-v731-camera` | `aa6c4b6b43ec45f4c41d3d420b980e35876860537cb6f2cb96ec5063aab8432a` |
| `Image-v731-thin-private` | `f8d8962197827dafbe50e551f5df03391c43ec0269449fa87b833e57799656a5` |
| `sm8150-samurai-v731-camera.dtb` | `3799ec6c7d3e0c67a657859a37b2fe147fa21a9dedc84d49c8eb83fd8debc805` |
| `sm8150-samurai-v731-flash-led-v4l2.dtb` | `b244b3f10a14811dca2e808efa8c840f432cac69020e66b60eba97d02794a18e` |
| `modules-v731-camera.tar.gz` | `22f50f56a4e912a6d6fc4f07785b1c02acbf536a96b3328edb3743f1d9bf7636` |
| `modules-v731-camera-selection.tar.gz` | `c656fe1f16c7e7ffed0e10d00dc0e00f41f863f92151e0078917232237f9cd4a` |
| `modules-v731-flash-led-v4l2.tar.gz` (774) | `c12a0513caf664200e1df47da5061b227090ffe8cf8d3586030cdbb9241a8b30` |
| camera boot | `9b9be136bd3ee2328f0c4273a829471ad0cd73a7fe7d718825ac024f7af3ae54` |
| flash/V4L2 boot | `5b4dd4871f6856710ff58e722ffd8b2c30d04baf0104b262adcb02e46a7651bf` |
| flash/V4L2 kernel FAT | `c99c690ee923238b0954975682c0e40ce99ae63afd048d40b5059fea70e5862e` |
| thin-private kernel FAT | `1f4bbb302a62d1f8a950994ac93b00ca194a41c768d4d11b1b97c69f5702574b` |
| final BdsDxe | `f3b946b1660cd444048aba7e5fe434e08a6f41d8dd11cc83f944455fea6855ac` |
| flash/V4L2 post-reboot runtime JSON | `c73fd0217e41862e2cc052cc2f6624cd3888a00aab17931f2f738a5e056312e7` |
| flash/V4L2 ordinary-reboot network JSON | `88d5ed6596c0f5229416d944f3d10367561bb2c0109afc73bd3c70cfb77fcbf3` |
| Bluetooth host APK | `a4cbe10a1a7a5b6e13ba01bf2a27e64663a0e290c2fd168c54e2b17f44a4be5e` |
| Bluetooth install probe | `96d956739d4c72dfe4731ad623e9529807b079786ca52a7f5718e0b90bde5dbc` |
| Bluetooth post-reboot probe | `2e32bd16cb4f969fb35c262594490f65596ad5254c5a6827899c82c35a5a1988` |
| Bluetooth ordinary-reboot network JSON | `1e1752e52d554840370be3397efe9ab1a860adcbf1760245f720f35b0e2e142e` |
| 777-module full runtime JSON | `8e2da5371afc79a73efff20158e58900edd5ddbb777f7ad02427c81d46a39459` |
| NFC/neard probe | `bc85deed81b86031d64d1afdec168e7c5cf70d70104c4b12b6870a6de4dd4c67` |
| NFC/neard post-reboot probe | `908959f97331317c7cf4006518e97a688ee587b563e6edfb84d586f1c7c5a15c` |
| NFC ordinary-reboot network JSON | `19532375b526d702b458f2d25164f3fc4284e1d635d7519c0ba535b60b4c0f19` |
| NFC/Bluetooth 777-module full runtime JSON | `0a30b1313580e006d506057e153b684ecf1719e3fe27b9ce5a3dd2734d014f40` |
| Selection-fix runtime JSON | `23965aa4f3510eb0376d497954ca6e6689484ab47dfff00a977d627219efa79a` |
| first final-boot runtime JSON | `345d630d04c2897f36e165ecf9d8bcfd42a2d76c8a93babd7b8f4a1cc3bfbf14` |
| ordinary-reboot runtime JSON | `812c7064969d602f5bfa58725a7f3e906f127c3d4d9949f54902de3799abbc4d` |
| poweroff-cycle runtime JSON | `78348acbc3514220e7e142236c31624bc01740e09ce1106fa8078ec72d9b3dcb` |
| post-s2idle runtime JSON | `e7a0b4e23e2081171d4b057a8787853f586f2cb767f0830d06b8041b5b8882dc` |
| thin-private first-reboot runtime JSON | `57c8bccc31f865604f3aa7847d927c72fb566528a61a5673d2fb6817b414417b` |
| thin-private second-reboot runtime JSON | `137d6c3adc24fbeb462c21cd2453a5bfb32ced9980c890bfa7a83d0593443cf3` |
| suspend attempt evidence | `9a77775b525fb1516b0ce8bd139cf9fbc97077f0a79a05dcf2d97a07e8e817ed` |
| display/s2idle evidence summary | `48cf51d32a12fb4dcfb5062c0360842a7c29a30e26ac760aa3eaaeb54a531847` |

The Windows-side flash helper defaults to a dry run. It refuses to write
unless the expected serial `62bc28a1`, `msmnile` product and boot SHA-256 all
match:

```powershell
powershell -ExecutionPolicy Bypass -File .\linux-port\scripts\flash-v731-camera.ps1
powershell -ExecutionPolicy Bypass -File .\linux-port\scripts\flash-v731-camera.ps1 -Flash
```

If a hot reboot into fastboot leaves Windows showing
`USB\VID_0000&PID_0001` with Code 43, the host saw a USB attach without a
valid descriptor. Re-entering fastboot reinitializes the ABL USB block. For a
Linux-side clean handoff, run
`linux-port/scripts/restart-bootloader-clean.py --inspect` first, then run it
without `--inspect` from Wi-Fi SSH (it unbinds the NCM gadget and drops USB
SSH). This is a workaround pending an ABL-side root cause.

After the reboot, run the on-device verifier. It produces JSON and returns
non-zero if any required boot, hardware, desktop or camera check fails:

```sh
python3 linux-port/scripts/verify-v731-final-runtime.py \
  --output /tmp/v731-final-runtime.json
```

### Offline rebuild probe

On 2026-11-08 the source worktree was freed of the diagnostic
`CLOCK_ALLOW_WRITE_DEBUGFS` change. A temporary index confirmed that the
worktree then had camera tree
`0347b4f91fa16695864406480ea41849b7d7b3c5`, and a fresh out-of-tree build
used the recorded config, `LOCALVERSION=` and the deployed `#4` build stamp.
The first clean probe (`f25488d7…`) is now invalidated: its generated
`autoconf.h` was stale relative to `.config` and lacked the camera
CCI/V4L2/sensor module symbols. The corrected login-shell, full-config
build with the fixed output tree `/home/cy122/samurai-v731-build` produced
`6b0580c1dbe814414370099f4c8efb5bb8fdecd905d33ca50656a9db04e53eba`.
A second output path produced `d943be51…`, differing in only 39 bytes of
the GNU build-id note. The deployed `aa6c4b6b…` Image still has a
different provenance and remains the runtime authority; the probe Image
must not be substituted for it. The machine-readable probe is
[`../dts/v731/offline-rebuild-probe-20261108.json`](../dts/v731/offline-rebuild-probe-20261108.json).
The corrected Image is a clean reproducible-candidate, not a
device-tested deployment. Its stripped 773-module tree is 772/773
byte-identical to the deployed tree, including CAMSS, IMX471, S5K3M5 and
S5KGW1; the only difference is the 33792-byte `imx319.ko` build-id note.
The later Selection API fix advances the camera tree to
`de256d3a46ecb80a80015fc996360127154bfe65`; the offline probe remains
evidence for the earlier tree, not for the two updated sensor modules.

USB NCM large-transfer behavior was reproduced and narrowed to the DWC3 TX
FIFO path. The unattended matrix is
[`../scripts/test-usb-ncm-stability.py`](../scripts/test-usb-ncm-stability.py);
it covers both SCP directions, 64 KiB through 4 MiB, host/device SHA-256,
UDC/carrier/dmesg capture and an optional heartbeat. It has passed offline
`--dry-run` and unreachable-device behavior checks. On the r16 standard
rootfs boot, the production DTB reproduced a 4 MiB device-to-host
`Broken pipe` after about 15 seconds, followed by a 17-second SSH outage.
The standard `tx-fifo-resize` DWC3 property then passed 24/24 transfers,
a 5-minute matrix and a 30-minute matrix with 1800.598 seconds of heartbeat.
Wi-Fi independently passed 1800 SSH samples over 1810 seconds. After the
ordinary reboot, the deployed pair repeated 24/24 transfers with 1800.169
seconds of NCM heartbeat and independently passed 1800 Wi-Fi SSH samples over
1811 seconds. The property is now in the production source and reproduces the
same DTB
`c9f948cd…`; the boot/FAT pair is deployed on `7f8d7a65…` /
`1f3a40f4…` and passed the new ordinary-reboot gate above.
[`verify-usb-ncm-result.py`](../scripts/verify-usb-ncm-result.py) is the
independent acceptance gate: it rejects dry runs, partial matrices,
timeouts, byte/hash mismatches, taint or boot-ID drift, missing
UDC/carrier state and short heartbeats.
The boot writer is
[`flash-v731-usb-fifo.ps1`](../scripts/flash-v731-usb-fifo.ps1), which is
dry-run by default and guards the fixed candidate size/hash before touching
the `boot` partition. The pair helper is
[`flash-v731-usb-fifo-pair.ps1`](../scripts/flash-v731-usb-fifo-pair.ps1)
and rejects a partial boot-only or logdump-only write. The deployed pair is
`E:/edk2-samurai-out/standard-arm64-v731/usb-fifo-standard-r16-20261108-b/`
(`7f8d7a65…` / `1f3a40f4…`). The new boot has also passed a second 30-minute
run for both NCM and Wi-Fi; repeated cold boots, longer idle, Linux-host and
multi-host testing remain open.

## Rollback and remaining work

The immediately previous tested boot is
`E:/edk2-samurai-out/standard-arm64-v731/camera-final-rollback/boot-before-camera.img`
(`c8a6c616f60c8ee8f314bfc9e1329c61af3eb070b0cee3724b99080ad3444eaf`).
Its matching previous kernel Image and FAT DTB are preserved in the same
directory. The older production envelope is
`E:/edk2-samurai-out/runtime-20261106-eud-default-off/boot/boot-eud-production-off.img`
(`8d1d6de2a3c63599080a16ded6ced1e410c9434e4e411a969e19b25ff03e690b`).

The fastboot name `logdump` is the same 64 MiB `sde32` KERNEL FAT
(`LABEL=KERNEL`). A locally validated recovery image
`E:/edk2-samurai-out/standard-arm64-v731/camera-final-boot/recovery-kernel-fat.img`
(`6a6aa520e4adda750450c3fd9b80a553c1988d6d76803c674c279b3a5df4f562`)
contains the final `/Image` and `/samurai.dtb`; `fastboot flash logdump`
restores it. `flash-v731-recovery.ps1` checks the serial, `msmnile` product,
size and SHA-256 and is dry-run by default. The image has passed
`fsck.vfat -n` and `mdir`, but has not yet been flashed on hardware.

Still open:

- the direct-rootfs boot/FAT pair is deployed, but the UEFI/GRUB candidate
  still requires a paired boot/logdump deployment and hardware validation;
- repeated cold boots are still open; the single ordinary reboot is not a
  cold-boot proof;
- `poweroff` re-power passed, but a manually keyed boot after removing
  external USB power has not been verified;
- short 90 Hz and s2idle tests passed; deep sleep, longer suspend and
  long-duration power/thermal stability remain open;
- RAM/UFS SKU coverage is not proven;
- RPMh read diagnostics still emit `ret=-95` noise;
- the UEFI standard boot candidate is offline built but not flashed; GRUB
  execution, file-based volume discovery, root mount and rollback remain
  unverified, and persistent UEFI variables are still not implemented;
- the PM8150L flash/V4L2 pair is deployed and passed control, optical torch,
  runtime and ordinary-reboot gates; external-power-removed cold boot,
  repeated cold boots and long flash thermal endurance remain open;
- the BNEP/UHID/uinput package is installed and auto-loads after an ordinary
  reboot; external PAN/HID peers, cold boot and suspend/resume with active
  peers remain open;
- managed high-voltage charging and camera ICP userspace remain separate
  profiles; standard V4L2 RAW camera capture is part of the deployed image.

The installed `samurai-platform 5-r21` / `samurai-desktop 4-r10` packages
align the user-space policy with the official postmarketOS/Nura base UI at
pmaports commit
`b5810eb2f3b24ce380a00c54569236f5559f78b1`: optional hardware services do
not gate tinydm, `sshd` and NetworkManager start independently of NCM/radio
preparation, and a carrier-only USB link is not a permanent sleep lock.
The default sleep policy keeps only the standard `ssh-session-open` and
`apk-running` plugins; an active SSH session still keeps the system awake
with the panel off. The USB carrier guard remains available but must be
enabled explicitly. The ordinary-reboot network and runtime gates passed;
cold boot and a Linux USB host remain open.
