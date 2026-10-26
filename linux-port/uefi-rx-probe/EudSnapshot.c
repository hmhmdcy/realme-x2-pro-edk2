/** @file
  Read-only SM8150 AHB2PHY wait-state snapshot, then chainload original Linux.
  SPDX-License-Identifier: BSD-2-Clause-Patent
**/
#include <Uefi.h>
#include <Protocol/LoadedImage.h>
#include <Library/BaseLib.h>
#include <Library/DevicePathLib.h>
#include <Library/IoLib.h>
#include <Library/PrintLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/TimerLib.h>
#include <Library/UefiBootServicesTableLib.h>

#define EUD_BASE  0x088E0000U
#define TOP_CFG   0x088EE010U

STATIC VOID
Send (CONST CHAR8 *Text)
{
  UINTN Offset;
  UINTN Index;
  UINTN Count;
  UINTN Length = AsciiStrLen (Text);

  for (Offset = 0; Offset < Length; Offset += Count) {
    Count = MIN (4, Length - Offset);
    MicroSecondDelay (200);
    MmioWrite32 (EUD_BASE, 0x90);
    MicroSecondDelay (200);
    MmioWrite32 (EUD_BASE + 4, (UINT32)Count);
    for (Index = 0; Index < Count; Index++) {
      MicroSecondDelay (200);
      MmioWrite32 (EUD_BASE + 8, (UINT8)Text[Offset + Index]);
    }
    MicroSecondDelay (2000);
  }
}

EFI_STATUS EFIAPI
UefiMain (EFI_HANDLE ImageHandle, EFI_SYSTEM_TABLE *SystemTable)
{
  EFI_STATUS Status;
  EFI_LOADED_IMAGE_PROTOCOL *Self;
  EFI_LOADED_IMAGE_PROTOCOL *Kernel;
  EFI_DEVICE_PATH_PROTOCOL *Path;
  EFI_HANDLE KernelHandle;
  EFI_TPL OldTpl;
  UINT32 First;
  UINT32 Second;
  UINTN Repeat;
  CHAR8 Line[128];

  Status = gBS->HandleProtocol (ImageHandle, &gEfiLoadedImageProtocolGuid, (VOID **)&Self);
  if (EFI_ERROR (Status)) {
    return Status;
  }
  Path = FileDevicePath (Self->DeviceHandle, L"\\Kernel");
  if (Path == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }
  Status = gBS->LoadImage (FALSE, ImageHandle, Path, NULL, 0, &KernelHandle);
  FreePool (Path);
  if (EFI_ERROR (Status)) {
    return Status;
  }
  Status = gBS->HandleProtocol (KernelHandle, &gEfiLoadedImageProtocolGuid, (VOID **)&Kernel);
  if (EFI_ERROR (Status)) {
    gBS->UnloadImage (KernelHandle);
    return Status;
  }
  Kernel->LoadOptions = Self->LoadOptions;
  Kernel->LoadOptionsSize = Self->LoadOptionsSize;
  OldTpl = gBS->RaiseTPL (TPL_HIGH_LEVEL);
  // Stock RMX1931 DAL map: SOUTH base 0x88e0000 + SWMAN 0xe000.
  // Stock dwc3-msm.c: TOP_CFG +0x10. Never write this register here.
  First = MmioRead32 (TOP_CFG);
  MicroSecondDelay (1000);
  Second = MmioRead32 (TOP_CFG);
  AsciiSPrint (Line, sizeof (Line), "\r\nRX41-UEFI TOP_CFG addr=%08x samples=%08x %08x readonly\r\n", TOP_CFG, First, Second);
  // Replay cached values for host enumeration; these are still only two reads.
  for (Repeat = 0; Repeat < 5; Repeat++) {
    Send (Line);
    MicroSecondDelay (1000000);
  }
  Send ("RX41-UEFI CHAINLOAD original Kernel\r\n");
  gBS->RestoreTPL (OldTpl);
  return gBS->StartImage (KernelHandle, NULL, NULL);
}
