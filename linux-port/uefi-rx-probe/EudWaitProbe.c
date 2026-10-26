/** @file
  Bounded SM8150 AHB2PHY one-wait-state EUD RX comparison.
  SPDX-License-Identifier: BSD-2-Clause-Patent
**/
#include <Uefi.h>
#include <Protocol/LoadedImage.h>
#include <Library/BaseLib.h>
#include <Library/DevicePathLib.h>
#include <Library/IoLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/PrintLib.h>
#include <Library/TimerLib.h>
#include <Library/UefiBootServicesTableLib.h>

#define EUD_BASE  0x088E0000U
#define TX_ID     0x00U
#define TX_LEN    0x04U
#define TX_DAT    0x08U
#define RX_ID     0x0CU
#define RX_LEN    0x10U
#define RX_DAT    0x14U
#define STATUS1   0x44U
#define TOP_CFG   0x088EE010U

STATIC VOID
Put (UINTN Offset, UINT32 Value)
{
  MicroSecondDelay (200);
  MmioWrite32 (EUD_BASE + Offset, Value);
}

// Four-byte TX frames, matching the known-good Linux console pacing.
STATIC VOID
Send (CONST CHAR8 *Text)
{
  UINTN Length = AsciiStrLen (Text);
  UINTN Offset;
  UINTN Index;
  UINTN Count;

  for (Offset = 0; Offset < Length; Offset += Count) {
    Count = MIN (4, Length - Offset);
    Put (TX_ID, 0x90);
    Put (TX_LEN, (UINT32)Count);
    for (Index = 0; Index < Count; Index++) {
      Put (TX_DAT, (UINT8)Text[Offset + Index]);
    }
    MicroSecondDelay (2000);
  }
}

// No Boot Services, logging, status reads or delays between payload reads.
// TPL_HIGH_LEVEL excludes the firmware's EudLogDxe timer writer. It does
// not establish that an invisible secure-world consumer has been excluded.
STATIC VOID
Probe (UINT32 ExpectedLength, CONST CHAR8 *Name, UINT64 Frequency)
{
  UINT64 Start;
  UINT64 Now;
  UINT64 PreviousPoll;
  UINT64 PollGap;
  UINT32 Status;
  UINT32 Id;
  UINT32 Length;
  UINT32 Data[14];
  UINTN Index;
  CHAR8 Line[192];

  AsciiSPrint (Line, sizeof (Line), "\r\nRX41-WAIT READY %a len=%u wait=25s poll=tight\r\n", Name, ExpectedLength);
  Send (Line);
  Start = GetPerformanceCounter ();
  PreviousPoll = Start;
  while (((Now = GetPerformanceCounter ()) - Start) < Frequency * 25) {
    PollGap = Now - PreviousPoll;
    PreviousPoll = Now;
    Status = MmioRead32 (EUD_BASE + STATUS1);
    if ((Status & 1U) != 0) {
      Id = MmioRead32 (EUD_BASE + RX_ID);
      Length = MmioRead32 (EUD_BASE + RX_LEN);
      if (((Id & 0xFFU) == 0x90) && ((Length & 0xFFU) == ExpectedLength)) {
        for (Index = 0; Index < ExpectedLength; Index++) {
          Data[Index] = MmioRead32 (EUD_BASE + RX_DAT);
        }
        // Only now may this app write to EUD. Keep raw words as evidence.
        AsciiSPrint (Line, sizeof (Line), "RX41-WAIT RESULT %a gap_ns=%Lu status=%08x id=%08x len=%08x words=", Name, GetTimeInNanoSecond (PollGap), Status, Id, Length);
        Send (Line);
        for (Index = 0; Index < ExpectedLength; Index++) {
          AsciiSPrint (Line, sizeof (Line), "%08x ", Data[Index]);
          Send (Line);
        }
        Send ("\r\n");
        return;
      }
    }
    // Keep the RX39 tight poll and adjacent payload reads unchanged.
    // Only the verified AHB2PHY wait-state setting differs in this trial.
  }
  AsciiSPrint (Line, sizeof (Line), "RX41-WAIT TIMEOUT %a\r\n", Name);
  Send (Line);
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
  UINT64 Frequency;
  UINT32 OriginalCfg;
  UINT32 AppliedCfg;
  UINT32 ConfirmCfg;
  UINT32 RestoredCfg;
  CHAR8 ConfigLine[160];

  // Preload the original EFI-stub kernel and retain BDS's command line and
  // existing DTB configuration table. Never experiment before this succeeds.
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
    SystemTable->ConOut->OutputString (SystemTable->ConOut, L"RX38: cannot load \\Kernel\r\n");
    return Status;
  }
  Status = gBS->HandleProtocol (KernelHandle, &gEfiLoadedImageProtocolGuid, (VOID **)&Kernel);
  if (EFI_ERROR (Status)) {
    gBS->UnloadImage (KernelHandle);
    return Status;
  }
  Kernel->LoadOptions = Self->LoadOptions;
  Kernel->LoadOptionsSize = Self->LoadOptionsSize;
  Frequency = GetPerformanceCounterProperties (NULL, NULL);
  if (Frequency != 0) {
    // Stock RMX1931 DAL map identifies SOUTH SWMAN at 0x088ee000;
    // the matching vendor dwc3-msm.c defines TOP_CFG +0x10 and value 0x11.
    // RX41 read-only snapshot measured 0 twice. Do not write another state.
    OldTpl = gBS->RaiseTPL (TPL_HIGH_LEVEL);
    OriginalCfg = MmioRead32 (TOP_CFG);
    if (OriginalCfg == 0) {
      MmioWrite32 (TOP_CFG, 0x11);
      MemoryFence ();
      MicroSecondDelay (1000);
      AppliedCfg = MmioRead32 (TOP_CFG);
      MicroSecondDelay (1000);
      ConfirmCfg = MmioRead32 (TOP_CFG);
      AsciiSPrint (ConfigLine, sizeof (ConfigLine),
                  "\r\nRX41-WAIT CONFIG addr=%08x original=%08x applied=%08x confirm=%08x\r\n",
                  TOP_CFG, OriginalCfg, AppliedCfg, ConfirmCfg);
      Send (ConfigLine);
      // Give the bounded host capture time to open before the READY marker.
      MicroSecondDelay (2000000);
      if ((AppliedCfg == 0x11) && (ConfirmCfg == 0x11)) {
        Probe (3, "ABC", Frequency);
        Probe (4, "DEFG", Frequency);
      } else {
        Send ("RX41-WAIT SKIP write did not read back 00000011\r\n");
      }
      // Restore even when readback failed. No Linux boot with trial settings.
      MmioWrite32 (TOP_CFG, OriginalCfg);
      MemoryFence ();
      MicroSecondDelay (1000);
      RestoredCfg = MmioRead32 (TOP_CFG);
      AsciiSPrint (ConfigLine, sizeof (ConfigLine),
                  "RX41-WAIT RESTORE expected=%08x readback=%08x\r\n",
                  OriginalCfg, RestoredCfg);
      Send (ConfigLine);
    } else {
      AsciiSPrint (ConfigLine, sizeof (ConfigLine),
                  "RX41-WAIT SKIP unexpected original=%08x; no write\r\n", OriginalCfg);
      Send (ConfigLine);
    }
    Send ("RX41-WAIT CHAINLOAD original Kernel\r\n");
    gBS->RestoreTPL (OldTpl);
  }
  return gBS->StartImage (KernelHandle, NULL, NULL);
}
