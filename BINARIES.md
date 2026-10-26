# Device firmware blobs required by the samurai port

The per-device DXE drivers are Qualcomm/OPPO firmware. They are **not** stored in
this repository: they belong to the `Platform/EFI_Binaries` submodule, which is
an upstream project we do not own. This page lists exactly which blobs the port
needs, where to get each one, and how to install them.

## How the blobs ship

`Platform/EFI_Binaries` is a submodule. This fork points it at
**`hmhmdcy/edk2-msm-binary`**, branch **`samurai-blobs`** (commit `2420ecf`),
which carries the samurai device blobs - so a recursive clone is all you need:

```bash
git clone --recursive https://github.com/hmhmdcy/edk2-realme-x2-pro.git
```

Already have a clone? Just re-sync the submodule:

```bash
git submodule sync Platform/EFI_Binaries
git submodule update --init Platform/EFI_Binaries
```

`fetch-binaries.sh` is kept as a fallback: it re-downloads the same files from
public mirrors of the stock firmware and re-applies the `ButtonsDxe.depex` patch
(see below).

## Files and sources

Everything goes under `Platform/EFI_Binaries/Drivers/Devices/samurai/`.

| Path | Source | Notes |
|---|---|---|
| `DALSys/DALSys.{efi,depex}` | stock X2 Pro `xbl.img` | upstream file name is `DALSYSDxe/DALSYSDxe.*` |
| `UsbPwrCtrlDxe/UsbPwrCtrlDxe.{efi,depex}` | stock `xbl.img` | |
| `ButtonsDxe/ButtonsDxe.efi` | stock `xbl.img` | **factory realme/OPPO build**. Do *not* substitute the shared `Drivers/sm8150/ButtonsDxe` |
| `ButtonsDxe/ButtonsDxe.depex` | stock `xbl.img`, **then patched** | see the DEPEX patch below |
| `TLMMDxe/TLMMDxe.{efi,depex}` | stock `xbl.img` | provides `EFI_QCOM_TLMM_PROTOCOL`. The shared `DALTLMM` is not enough for the factory `ButtonsDxe` |
| `ResetRuntimeDxe/ResetRuntimeDxe.{efi,depex}` | stock `xbl.img` | **not part of the shared sm8150 driver set**; provides the reset-reason protocol (`A022155A-...`) |
| `OcdtDxe/OppoProject.{efi,depex}` | another OPPO/realme **SM8150** port | provides the OPPO project protocol (`903C579D-...`). **Not present in the X2 Pro's own XBL dump** |

Public sources used by `fetch-binaries.sh`:

* stock realme X2 Pro (`realme-rmx1931`) DXE set -
  <https://github.com/Project-Aloha/UEFIFirmwareBackup/tree/main/realme-rmx1931/Binaries/QcomPkg/Drivers>
* `OppoProject.efi` (`OcdtDxe`) -
  <https://github.com/Project-Aloha/mu_aloha_platforms/tree/main/Platforms/SurfaceDuo1Pkg/Device/realme-rmx2086/Binaries/QcomPkg/Drivers/OcdtDxe>
  (the identical file also exists for `oppo-pclm10`, the OPPO Reno ACE, same SM8150 platform)

Both come from `SDM855LA_Core` builds of the OPPO/realme XBL source tree, i.e.
the same generation as this phone.

## Why the factory ButtonsDxe needs all of this

The X2 Pro's own `xbl.img` ships the OPPO-customised `ButtonsDxe`, which is
**not** self-contained. During `ButtonsInit` it additionally wants, at run time:

1. `EFI_QCOM_TLMM_PROTOCOL` - the TLMM GPIO block (`TLMMDxe`),
2. the **OPPO project protocol** - provided by `OppoProject.efi` (`OcdtDxe`).
   When it is missing the driver prints `Locate oppo project protocol failed`
   and returns `EFI_NOT_FOUND`,
3. the **reset-reason protocol** (`A022155A-4828-4535-A499-11F15240B91B`),
   provided by `ResetRuntimeDxe`.

If any of them is missing the driver is unloaded and **no side button works at
all** - not even Volume-Up or Power.

It also reads the SMEM project entry, which on this device reports
`Project:19781`; that value selects the per-project key map.

## DEPEX patch

`ButtonsDxe` locates the OPPO project protocol at run time, but its DEPEX does
not mention it. If the DXE dispatcher dispatches `ButtonsDxe` before
`OppoProject` has installed `903C579D-...`, the lookup fails and the driver is
unloaded.

The fix is to add the GUID to the driver's DEPEX, which makes the dispatcher
guarantee the ordering:

```bash
python3 Platform/Realme/sm8150/fix-buttons-depex.py \
        Platform/EFI_Binaries/Drivers/Devices/samurai/ButtonsDxe/ButtonsDxe.depex
```

Resulting DEPEX (4 original GUIDs + the OPPO project protocol):

```
PUSH 387477C1-69C7-11D2-8E39-00A0C969723B   ; SimpleTextIn
PUSH 157A5C45-21B2-43C5-BA7C-822FEE5FE599   ; PlatformInfo
PUSH 60759B13-A8BF-46FE-B7E6-797BFB335DF3   ; PMIC
PUSH 9BA45B66-EFA4-441C-A3E4-ED2224786BE2   ; PMIC
PUSH 903C579D-EBDE-19E0-39A7-43B95FA73F91   ; OPPO project protocol (OppoProject)
AND AND AND AND END
```

## Offline copy

`E:\edk2-samurai-out\samurai-binaries.zip` (15 files, ~144 KB) is a local copy of
the same tree; unpack it into
`Platform/EFI_Binaries/Drivers/Devices/samurai/` on a machine without network
access.
