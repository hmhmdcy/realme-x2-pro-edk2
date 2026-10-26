/** @file
  Implementation for PlatformBootManagerLib library class interfaces.

  Copyright (C) 2015-2016, Red Hat, Inc.
  Copyright (c) 2014 - 2019, ARM Ltd. All rights reserved.<BR>
  Copyright (c) 2004 - 2018, Intel Corporation. All rights reserved.<BR>
  Copyright (c) 2016, Linaro Ltd. All rights reserved.<BR>

  SPDX-License-Identifier: BSD-2-Clause-Patent

**/

#include <Guid/EventGroup.h>
#include <Guid/SerialPortLibVendor.h>
#include <Guid/TtyTerm.h>
#include <IndustryStandard/Pci22.h>
#include <Library/BaseMemoryLib.h>
#include <Library/BootLogoLib.h>
#include <Library/CapsuleLib.h>
#include <Library/DevicePathLib.h>
#include <Library/HobLib.h>
#include <Library/DebugLib.h>
#include <Library/IoLib.h>
#include <Library/PcdLib.h>
#include <Library/PrintLib.h>
#include <Library/UefiBootManagerLib.h>
#include <Library/UefiLib.h>
#include <Library/UefiRuntimeServicesTableLib.h>

#include <Library/MsPlatformDevicesLib.h>

#include <Protocol/DevicePath.h>
#include <Protocol/EsrtManagement.h>
#include <Protocol/GraphicsOutput.h>
#include <Protocol/LoadedImage.h>
#include <Protocol/PciIo.h>
#include <Protocol/PciRootBridgeIo.h>
#include <Protocol/PlatformBootManager.h>
#include <Protocol/SimpleFileSystem.h>
#include <Protocol/EFITlmm.h>

#include <Library/MemoryAllocationLib.h>

#include "PlatformBm.h"

#ifdef SAMURAI_LINUX_KERNEL

#define SAMURAI_PANEL_RESET_CONFIG \
  EFI_GPIO_CFG (6, 0, GPIO_OUTPUT, GPIO_NO_PULL, GPIO_8MA)

typedef struct {
  EFI_QCOM_TLMM_PROTOCOL  *Tlmm;
  EFI_EVENT              Event;
  BOOLEAN                Attempted;
  EFI_STATUS             Status;
} SAMURAI_PANEL_HANDOFF;

STATIC
VOID
EFIAPI
SamuraiPanelBeforeExitBootServices (
  IN EFI_EVENT  Event,
  IN VOID       *Context
  )
{
  SAMURAI_PANEL_HANDOFF  *Handoff;

  (VOID)Event;
  Handoff = Context;
  if ((Handoff == NULL) || Handoff->Attempted) {
    return;
  }

  Handoff->Attempted = TRUE;
  if ((Handoff->Tlmm == NULL) || (Handoff->Tlmm->ConfigGpio == NULL) ||
      (Handoff->Tlmm->GpioOut == NULL)) {
    Handoff->Status = EFI_UNSUPPORTED;
    return;
  }

  // This group runs while firmware interfaces and timers are still available.
  Handoff->Status = Handoff->Tlmm->ConfigGpio (
                                    SAMURAI_PANEL_RESET_CONFIG,
                                    TLMM_GPIO_ENABLE
                                    );
  if (!EFI_ERROR (Handoff->Status)) {
    Handoff->Status = Handoff->Tlmm->GpioOut (
                                      SAMURAI_PANEL_RESET_CONFIG,
                                      GPIO_LOW_VALUE
                                      );
  }
  DEBUG ((DEBUG_INFO, "[SAMURAI] panel reset before Linux ExitBootServices: %r\n",
          Handoff->Status));
}

STATIC
EFI_STATUS
SamuraiArmPanelHandoff (
  OUT SAMURAI_PANEL_HANDOFF  *Handoff
  )
{
  EFI_STATUS  Status;

  ZeroMem (Handoff, sizeof (*Handoff));
  Handoff->Status = EFI_NOT_READY;
  Status = gBS->LocateProtocol (
                  &gQcomTlmmProtocolGuid,
                  NULL,
                  (VOID **)&Handoff->Tlmm
                  );
  if (EFI_ERROR (Status)) {
    return Status;
  }
  if ((Handoff->Tlmm->Revision < QCOM_TLMM_PROTOCOL_REVISION) ||
      (Handoff->Tlmm->ConfigGpio == NULL) || (Handoff->Tlmm->GpioOut == NULL)) {
    return EFI_UNSUPPORTED;
  }

  Status = gBS->CreateEventEx (
                  EVT_NOTIFY_SIGNAL,
                  TPL_CALLBACK,
                  SamuraiPanelBeforeExitBootServices,
                  Handoff,
                  &gEfiEventBeforeExitBootServicesGuid,
                  &Handoff->Event
                  );
  if (EFI_ERROR (Status)) {
    Handoff->Event = NULL;
  }
  return Status;
}

STATIC
VOID
SamuraiDisarmPanelHandoff (
  IN OUT SAMURAI_PANEL_HANDOFF  *Handoff
  )
{
  if (Handoff->Event != NULL) {
    if (gBS != NULL) {
      gBS->CloseEvent (Handoff->Event);
    }
    Handoff->Event = NULL;
  }
}

//
// SAMURAI: where the mainline Linux kernel lives on a file system.  It used to be
// an FFS file in this firmware volume; see SamuraiRegisterKernelBootOption() for why
// that cannot work with a 30 MB kernel.  The name is 8.3 friendly on purpose, so the
// volume does not depend on VFAT long name support.
//
#define SAMURAI_KERNEL_FILE  L"\\Image"

//
// SAMURAI: same string as /chosen/bootargs of the device tree in
// FdtBlob/samurai/.  It is passed as the LoadOptions of the boot option so
// the log channel survives even if the device tree reaches the kernel
// without bootargs.  CHAR16 on purpose: the EFI stub reads LoadOptions as
// UTF-16 and an ASCII buffer would be decoded into garbage that *replaces*
// the device tree's bootargs.
//
STATIC CHAR16  mSamuraiLinuxCmdLine[] =
  L"earlycon=eud,mmio,0x88e0000 console=tty0 console=eud loglevel=7 ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused regulator_ignore_unused";

/**
  SAMURAI: register the mainline Linux kernel that lives on a file system.

  The kernel is a plain EFI application (CONFIG_EFI_STUB), so this is a normal
  LoadImage - no loader stub is needed.  The device tree does not have to sit
  next to it either: DtPlatformDxe already installed FdtBlob/samurai/ as the EFI
  configuration table and the stub takes the device tree from there.

  Keeping the kernel out of the firmware volume is deliberate:
    - an FFS file cannot exceed 16 MiB because the size field is 24 bit, and the
      kernel is 30 MB, so embedding it silently truncated the file and
      corrupted FVMAIN;
    - that volume decompressed to 62 MB, which does not fit in the PrePi/DXE
      memory pool (PcdUefiMemPoolSize), so the DXE core was never loaded.

  On this handset the kernel sits on the FAT16 "logdump" partition, a 64 MiB
  Qualcomm log partition that the Android ROM never mounts.
**/
STATIC
VOID
SamuraiRegisterKernelBootOption (
  VOID
  )
{
  EFI_STATUS                       Status;
  EFI_HANDLE                       *Handles;
  UINTN                            HandleCount;
  UINTN                            Index;
  EFI_SIMPLE_FILE_SYSTEM_PROTOCOL  *FileSystem;
  EFI_FILE_PROTOCOL                *Root;
  EFI_FILE_PROTOCOL                *File;
  EFI_DEVICE_PATH_PROTOCOL         *DevicePath;
  EFI_BOOT_MANAGER_LOAD_OPTION     NewOption;
  SAMURAI_PANEL_HANDOFF            PanelHandoff;
  EFI_BOOT_MANAGER_LOAD_OPTION     *BootOptions;
  UINTN                            BootOptionCount;
  INTN                             OptionIndex;
  UINTN                            CmdLineSize;

  Status = gBS->LocateHandleBuffer (
                  ByProtocol,
                  &gEfiSimpleFileSystemProtocolGuid,
                  NULL,
                  &HandleCount,
                  &Handles
                  );
  if (EFI_ERROR (Status)) {
    Print (L"[SAMURAI] no file system to look for the kernel on\n");
    return;
  }

  for (Index = 0; Index < HandleCount; Index++) {
    Status = gBS->HandleProtocol (
                    Handles[Index],
                    &gEfiSimpleFileSystemProtocolGuid,
                    (VOID **)&FileSystem
                    );
    if (EFI_ERROR (Status)) {
      continue;
    }

    Status = FileSystem->OpenVolume (FileSystem, &Root);
    if (EFI_ERROR (Status)) {
      continue;
    }

    Status = Root->Open (Root, &File, SAMURAI_KERNEL_FILE, EFI_FILE_MODE_READ, 0);
    Root->Close (Root);
    if (EFI_ERROR (Status)) {
      continue;
    }

    //
    // Do not trust the file name alone.  The FAT driver mis-binds to the modem
    // partition on this handset and that bogus volume even exposes a \Image, and
    // booting a kernel that is not there makes BdsDxe die with a fatal error.  A
    // kernel image starts with the PE signature "MZ".
    //
    {
      UINT8    Magic[2] = { 0, 0 };
      UINTN    MagicSize = sizeof (Magic);
      BOOLEAN  LooksLikeKernel;

      LooksLikeKernel = !EFI_ERROR (File->Read (File, &MagicSize, Magic)) &&
                        (MagicSize == 2) && (Magic[0] == 'M') && (Magic[1] == 'Z');
      File->Close (File);
      if (!LooksLikeKernel) {
        Print (L"[SAMURAI] a file system has a \\Image that is not a kernel, skipped\n");
        continue;
      }
    }

    DevicePath = FileDevicePath (Handles[Index], SAMURAI_KERNEL_FILE);
    if (DevicePath == NULL) {
      continue;
    }

    CmdLineSize = (StrLen (mSamuraiLinuxCmdLine) + 1) * sizeof (CHAR16);
    Status      = EfiBootManagerInitializeLoadOption (
                    &NewOption,
                    LoadOptionNumberUnassigned,
                    LoadOptionTypeBoot,
                    LOAD_OPTION_ACTIVE,
                    L"Linux (mainline samurai)",
                    DevicePath,
                    (UINT8 *)mSamuraiLinuxCmdLine,
                    (UINT32)CmdLineSize
                    );
    FreePool (DevicePath);
    if (EFI_ERROR (Status)) {
      break;
    }

    BootOptions = EfiBootManagerGetLoadOptions (&BootOptionCount, LoadOptionTypeBoot);
    OptionIndex = EfiBootManagerFindLoadOption (&NewOption, BootOptions, BootOptionCount);
    if (OptionIndex == -1) {
      EfiBootManagerAddLoadOptionVariable (&NewOption, MAX_UINTN);
      Print (L"[SAMURAI] kernel found, registered \"Linux (mainline samurai)\"\n");
    } else {
      Print (L"[SAMURAI] kernel boot option is already present\n");
    }

    //
    // SAMURAI: start it right now.  SimpleInit is the configured boot manager on this
    // handset and its default entry fails (it points at the boot partition, which holds
    // this firmware), after which it resets the phone about eight seconds later - so its
    // GUI only ever loops and nothing can be selected in time.  Booting here skips the
    // boot order altogether and is what bring-up wants anyway.  Comment the next two
    // lines out to get the boot menu back.
    //
    Print (L"[SAMURAI] starting \\Image now\n");
    Status = SamuraiArmPanelHandoff (&PanelHandoff);
    if (EFI_ERROR (Status)) {
      DEBUG ((DEBUG_WARN, "[SAMURAI] panel handoff unavailable: %r\n", Status));
    }
    EfiBootManagerBoot (&NewOption);
    SamuraiDisarmPanelHandoff (&PanelHandoff);
    Print (L"[SAMURAI] EfiBootManagerBoot returned - the kernel did not take over\n");

    EfiBootManagerFreeLoadOption (&NewOption);
    EfiBootManagerFreeLoadOptions (BootOptions, BootOptionCount);
    break;
  }

  if (Index == HandleCount) {
    Print (L"[SAMURAI] no \\Image on any file system - kernel not registered\n");
  }

  FreePool (Handles);
}
#endif

#define DP_NODE_LEN(Type)                                                      \
  {                                                                            \
    (UINT8)sizeof(Type), (UINT8)(sizeof(Type) >> 8)                            \
  }

#pragma pack(1)
typedef struct {
  VENDOR_DEVICE_PATH         SerialDxe;
  UART_DEVICE_PATH           Uart;
  VENDOR_DEFINED_DEVICE_PATH TermType;
  EFI_DEVICE_PATH_PROTOCOL   End;
} PLATFORM_SERIAL_CONSOLE;
#pragma pack()

STATIC PLATFORM_SERIAL_CONSOLE mSerialConsole = {
    //
    // VENDOR_DEVICE_PATH SerialDxe
    //
    {{HARDWARE_DEVICE_PATH, HW_VENDOR_DP, DP_NODE_LEN(VENDOR_DEVICE_PATH)},
     EDKII_SERIAL_PORT_LIB_VENDOR_GUID},

    //
    // UART_DEVICE_PATH Uart
    //
    {
        {MESSAGING_DEVICE_PATH, MSG_UART_DP, DP_NODE_LEN(UART_DEVICE_PATH)},
        0,                                     // Reserved
        FixedPcdGet64(PcdUartDefaultBaudRate), // BaudRate
        FixedPcdGet8(PcdUartDefaultDataBits),  // DataBits
        FixedPcdGet8(PcdUartDefaultParity),    // Parity
        FixedPcdGet8(PcdUartDefaultStopBits)   // StopBits
    },

    //
    // VENDOR_DEFINED_DEVICE_PATH TermType
    //
    {
        {MESSAGING_DEVICE_PATH, MSG_VENDOR_DP,
         DP_NODE_LEN(VENDOR_DEFINED_DEVICE_PATH)}
        //
        // Guid to be filled in dynamically
        //
    },

    //
    // EFI_DEVICE_PATH_PROTOCOL End
    //
    {END_DEVICE_PATH_TYPE, END_ENTIRE_DEVICE_PATH_SUBTYPE,
     DP_NODE_LEN(EFI_DEVICE_PATH_PROTOCOL)}};

#pragma pack(1)
typedef struct {
  USB_CLASS_DEVICE_PATH    Keyboard;
  EFI_DEVICE_PATH_PROTOCOL End;
} PLATFORM_USB_KEYBOARD;
#pragma pack()

STATIC PLATFORM_USB_KEYBOARD mUsbKeyboard = {
    //
    // USB_CLASS_DEVICE_PATH Keyboard
    //
    {
        {MESSAGING_DEVICE_PATH, MSG_USB_CLASS_DP,
         DP_NODE_LEN(USB_CLASS_DEVICE_PATH)},
        0xFFFF, // VendorId: any
        0xFFFF, // ProductId: any
        3,      // DeviceClass: HID
        1,      // DeviceSubClass: boot
        1       // DeviceProtocol: keyboard
    },

    //
    // EFI_DEVICE_PATH_PROTOCOL End
    //
    {END_DEVICE_PATH_TYPE, END_ENTIRE_DEVICE_PATH_SUBTYPE,
     DP_NODE_LEN(EFI_DEVICE_PATH_PROTOCOL)}};

/**
  Check if the handle satisfies a particular condition.

  @param[in] Handle      The handle to check.
  @param[in] ReportText  A caller-allocated string passed in for reporting
                         purposes. It must never be NULL.

  @retval TRUE   The condition is satisfied.
  @retval FALSE  Otherwise. This includes the case when the condition could not
                 be fully evaluated due to an error.
**/
typedef BOOLEAN(EFIAPI *FILTER_FUNCTION)(
    IN EFI_HANDLE Handle, IN CONST CHAR16 *ReportText);

/**
  Process a handle.

  @param[in] Handle      The handle to process.
  @param[in] ReportText  A caller-allocated string passed in for reporting
                         purposes. It must never be NULL.
**/
typedef VOID(EFIAPI *CALLBACK_FUNCTION)(
    IN EFI_HANDLE Handle, IN CONST CHAR16 *ReportText);

/**
  Locate all handles that carry the specified protocol, filter them with a
  callback function, and pass each handle that passes the filter to another
  callback.

  @param[in] ProtocolGuid  The protocol to look for.

  @param[in] Filter        The filter function to pass each handle to. If this
                           parameter is NULL, then all handles are processed.

  @param[in] Process       The callback function to pass each handle to that
                           clears the filter.
**/
STATIC
VOID FilterAndProcess(
    IN EFI_GUID *ProtocolGuid, IN FILTER_FUNCTION Filter OPTIONAL,
    IN CALLBACK_FUNCTION Process)
{
  EFI_STATUS  Status;
  EFI_HANDLE *Handles;
  UINTN       NoHandles;
  UINTN       Idx;

  Status = gBS->LocateHandleBuffer(
      ByProtocol, ProtocolGuid, NULL /* SearchKey */, &NoHandles, &Handles);
  if (EFI_ERROR(Status)) {
    //
    // This is not an error, just an informative condition.
    //
    DEBUG((EFI_D_VERBOSE, "%a: %g: %r\n", __FUNCTION__, ProtocolGuid, Status));
    return;
  }

  ASSERT(NoHandles > 0);
  for (Idx = 0; Idx < NoHandles; ++Idx) {
    CHAR16 *      DevicePathText;
    STATIC CHAR16 Fallback[] = L"<device path unavailable>";

    //
    // The ConvertDevicePathToText() function handles NULL input transparently.
    //
    DevicePathText = ConvertDevicePathToText(
        DevicePathFromHandle(Handles[Idx]),
        FALSE, // DisplayOnly
        FALSE  // AllowShortcuts
    );
    if (DevicePathText == NULL) {
      DevicePathText = Fallback;
    }

    if (Filter == NULL || Filter(Handles[Idx], DevicePathText)) {
      Process(Handles[Idx], DevicePathText);
    }

    if (DevicePathText != Fallback) {
      FreePool(DevicePathText);
    }
  }
  gBS->FreePool(Handles);
}

/**
  This FILTER_FUNCTION checks if a handle corresponds to a PCI display device.
**/
STATIC
BOOLEAN
EFIAPI
IsPciDisplay(IN EFI_HANDLE Handle, IN CONST CHAR16 *ReportText)
{
  EFI_STATUS           Status;
  EFI_PCI_IO_PROTOCOL *PciIo;
  PCI_TYPE00           Pci;

  Status = gBS->HandleProtocol(Handle, &gEfiPciIoProtocolGuid, (VOID **)&PciIo);
  if (EFI_ERROR(Status)) {
    //
    // This is not an error worth reporting.
    //
    return FALSE;
  }

  Status = PciIo->Pci.Read(
      PciIo, EfiPciIoWidthUint32, 0 /* Offset */, sizeof Pci / sizeof(UINT32),
      &Pci);
  if (EFI_ERROR(Status)) {
    DEBUG((EFI_D_ERROR, "%a: %s: %r\n", __FUNCTION__, ReportText, Status));
    return FALSE;
  }

  return IS_PCI_DISPLAY(&Pci);
}

/**
  This CALLBACK_FUNCTION attempts to connect a handle non-recursively, asking
  the matching driver to produce all first-level child handles.
**/
STATIC
VOID EFIAPI Connect(IN EFI_HANDLE Handle, IN CONST CHAR16 *ReportText)
{
  EFI_STATUS Status;

  Status = gBS->ConnectController(
      Handle, // ControllerHandle
      NULL,   // DriverImageHandle
      NULL,   // RemainingDevicePath -- produce all children
      FALSE   // Recursive
  );
  DEBUG(
      (EFI_ERROR(Status) ? EFI_D_ERROR : EFI_D_VERBOSE, "%a: %s: %r\n",
       __FUNCTION__, ReportText, Status));
}

/**
  This CALLBACK_FUNCTION retrieves the EFI_DEVICE_PATH_PROTOCOL from the
  handle, and adds it to ConOut and ErrOut.
**/
STATIC
VOID EFIAPI AddOutput(IN EFI_HANDLE Handle, IN CONST CHAR16 *ReportText)
{
  EFI_STATUS                Status;
  EFI_DEVICE_PATH_PROTOCOL *DevicePath;

  DevicePath = DevicePathFromHandle(Handle);
  if (DevicePath == NULL) {
    DEBUG(
        (EFI_D_ERROR, "%a: %s: handle %p: device path not found\n",
         __FUNCTION__, ReportText, Handle));
    return;
  }

  Status = EfiBootManagerUpdateConsoleVariable(ConOut, DevicePath, NULL);
  if (EFI_ERROR(Status)) {
    DEBUG(
        (EFI_D_ERROR, "%a: %s: adding to ConOut: %r\n", __FUNCTION__,
         ReportText, Status));
    return;
  }

  Status = EfiBootManagerUpdateConsoleVariable(ErrOut, DevicePath, NULL);
  if (EFI_ERROR(Status)) {
    DEBUG(
        (EFI_D_ERROR, "%a: %s: adding to ErrOut: %r\n", __FUNCTION__,
         ReportText, Status));
    return;
  }

  DEBUG(
      (EFI_D_VERBOSE, "%a: %s: added to ConOut and ErrOut\n", __FUNCTION__,
       ReportText));
}

STATIC
UINT16
PlatformRegisterFvBootOption(
    CONST EFI_GUID *FileGuid,
    CHAR16 *Description,
    UINT32 Attributes,
    CHAR16 *CommandLine OPTIONAL)
{
  EFI_STATUS                        Status;
  INTN                              OptionIndex;
  EFI_BOOT_MANAGER_LOAD_OPTION      NewOption;
  EFI_BOOT_MANAGER_LOAD_OPTION *    BootOptions;
  UINTN                             BootOptionCount;
  MEDIA_FW_VOL_FILEPATH_DEVICE_PATH FileNode;
  EFI_LOADED_IMAGE_PROTOCOL *       LoadedImage;
  EFI_DEVICE_PATH_PROTOCOL *        DevicePath;
  UINT16                            OptionNumber;
  UINTN                             OptionalDataSize;

  Status = gBS->HandleProtocol(
      gImageHandle, &gEfiLoadedImageProtocolGuid, (VOID **)&LoadedImage);
  ASSERT_EFI_ERROR(Status);

  EfiInitializeFwVolDevicepathNode(&FileNode, FileGuid);
  DevicePath = DevicePathFromHandle(LoadedImage->DeviceHandle);
  ASSERT(DevicePath != NULL);
  DevicePath =
      AppendDevicePathNode(DevicePath, (EFI_DEVICE_PATH_PROTOCOL *)&FileNode);
  ASSERT(DevicePath != NULL);

  //
  // OptionalData becomes the loaded image's LoadOptions.  A kernel command
  // line has to be a NUL terminated CHAR16 string, because the Linux EFI
  // stub reads LoadOptions as UTF-16.
  //
  OptionalDataSize = 0;
  if (CommandLine != NULL) {
    OptionalDataSize = (StrLen(CommandLine) + 1) * sizeof(CHAR16);
  }

  Status = EfiBootManagerInitializeLoadOption(
      &NewOption, LoadOptionNumberUnassigned, LoadOptionTypeBoot, Attributes,
      Description, DevicePath, (UINT8 *)CommandLine, (UINT32)OptionalDataSize);
  ASSERT_EFI_ERROR(Status);
  FreePool(DevicePath);

  BootOptions =
      EfiBootManagerGetLoadOptions(&BootOptionCount, LoadOptionTypeBoot);

  OptionIndex =
      EfiBootManagerFindLoadOption(&NewOption, BootOptions, BootOptionCount);

  if (OptionIndex == -1) {
    Status = EfiBootManagerAddLoadOptionVariable(&NewOption, MAX_UINTN);
    ASSERT_EFI_ERROR(Status);
  }
  OptionNumber = NewOption.OptionNumber;
  EfiBootManagerFreeLoadOption(&NewOption);
  EfiBootManagerFreeLoadOptions(BootOptions, BootOptionCount);
  return OptionNumber;
}

STATIC
VOID GetPlatformOptions(VOID)
{
  EFI_STATUS                      Status;
  EFI_BOOT_MANAGER_LOAD_OPTION *  CurrentBootOptions;
  EFI_BOOT_MANAGER_LOAD_OPTION *  BootOptions;
  EFI_INPUT_KEY *                 BootKeys;
  PLATFORM_BOOT_MANAGER_PROTOCOL *PlatformBootManager;
  UINTN                           CurrentBootOptionCount;
  UINTN                           Index;
  UINTN                           BootCount;

  Status = gBS->LocateProtocol(
      &gPlatformBootManagerProtocolGuid, NULL, (VOID **)&PlatformBootManager);
  if (EFI_ERROR(Status)) {
    return;
  }
  Status = PlatformBootManager->GetPlatformBootOptionsAndKeys(
      &BootCount, &BootOptions, &BootKeys);
  if (EFI_ERROR(Status)) {
    return;
  }
  //
  // Fetch the existent boot options. If there are none, CurrentBootCount
  // will be zeroed.
  //
  CurrentBootOptions =
      EfiBootManagerGetLoadOptions(&CurrentBootOptionCount, LoadOptionTypeBoot);
  //
  // Process the platform boot options.
  //
  for (Index = 0; Index < BootCount; Index++) {
    INTN  Match;
    UINTN BootOptionNumber;

    //
    // If there are any preexistent boot options, and the subject platform boot
    // option is already among them, then don't try to add it. Just get its
    // assigned boot option number so we can associate a hotkey with it. Note
    // that EfiBootManagerFindLoadOption() deals fine with (CurrentBootOptions
    // == NULL) if (CurrentBootCount == 0).
    //
    Match = EfiBootManagerFindLoadOption(
        &BootOptions[Index], CurrentBootOptions, CurrentBootOptionCount);
    if (Match >= 0) {
      BootOptionNumber = CurrentBootOptions[Match].OptionNumber;
    }
    else {
      //
      // Add the platform boot options as a new one, at the end of the boot
      // order. Note that if the platform provided this boot option with an
      // unassigned option number, then the below function call will assign a
      // number.
      //
      Status =
          EfiBootManagerAddLoadOptionVariable(&BootOptions[Index], MAX_UINTN);
      if (EFI_ERROR(Status)) {
        DEBUG(
            (DEBUG_ERROR, "%a: failed to register \"%s\": %r\n", __FUNCTION__,
             BootOptions[Index].Description, Status));
        continue;
      }
      BootOptionNumber = BootOptions[Index].OptionNumber;
    }

    //
    // Register a hotkey with the boot option, if requested.
    //
    if (BootKeys[Index].UnicodeChar == L'\0') {
      continue;
    }

    Status = EfiBootManagerAddKeyOptionVariable(
        NULL, BootOptionNumber, 0, &BootKeys[Index], NULL);
    if (EFI_ERROR(Status)) {
      DEBUG(
          (DEBUG_ERROR, "%a: failed to register hotkey for \"%s\": %r\n",
           __FUNCTION__, BootOptions[Index].Description, Status));
    }
  }
  EfiBootManagerFreeLoadOptions(CurrentBootOptions, CurrentBootOptionCount);
  EfiBootManagerFreeLoadOptions(BootOptions, BootCount);
  FreePool(BootKeys);
}

STATIC
VOID PlatformRegisterOptionsAndKeys(VOID)
{
  EFI_STATUS                   Status;
  EFI_INPUT_KEY                Enter;
  EFI_INPUT_KEY                UP;
  EFI_INPUT_KEY                Esc;
  EFI_BOOT_MANAGER_LOAD_OPTION BootOption;

  GetPlatformOptions();

  //
  // Register ENTER as CONTINUE key
  //
  Enter.ScanCode    = SCAN_NULL;
  Enter.UnicodeChar = CHAR_CARRIAGE_RETURN;
  Status            = EfiBootManagerRegisterContinueKeyOption(0, &Enter, NULL);
  ASSERT_EFI_ERROR(Status);

  //
  // Map UP and ESC to Boot Manager Menu or SimpleInitGUI
  //
  UP.ScanCode     = SCAN_UP;
  UP.UnicodeChar  = CHAR_NULL;
  Esc.ScanCode    = SCAN_ESC;
  Esc.UnicodeChar = CHAR_NULL;
  Status          = EfiBootManagerGetBootManagerMenu(&BootOption);
  ASSERT_EFI_ERROR(Status);
#ifdef ENABLE_SIMPLE_INIT

  //
  // Register Simple Init GUI APP
  //
  UINT16 OptionSimpleInit = PlatformRegisterFvBootOption(
      &gSimpleInitFileGuid, L"Simple Init", LOAD_OPTION_ACTIVE, NULL);
  Status = EfiBootManagerAddKeyOptionVariable(
      NULL, (UINT16)OptionSimpleInit, 0, &UP, NULL);
#else
  Status = EfiBootManagerAddKeyOptionVariable(
      NULL, (UINT16)BootOption.OptionNumber, 0, &UP, NULL);
#endif
  ASSERT(Status == EFI_SUCCESS || Status == EFI_ALREADY_STARTED);
}

//
// BDS Platform Functions
//
/**
  Do the platform init, can be customized by OEM/IBV
  Possible things that can be done in PlatformBootManagerBeforeConsole:
  > Update console variable: 1. include hot-plug devices;
  >                          2. Clear ConIn and add SOL for AMT
  > Register new Driver#### or Boot####
  > Register new Key####: e.g.: F12
  > Signal ReadyToLock event
  > Authentication action: 1. connect Auth devices;
  >                        2. Identify auto logon user.
**/
VOID EFIAPI PlatformBootManagerBeforeConsole(VOID)
{
  //
  // Signal EndOfDxe PI Event
  //
  EfiEventGroupSignal(&gEfiEndOfDxeEventGroupGuid);

  //
  // Dispatch deferred images after EndOfDxe event.
  //
  EfiBootManagerDispatchDeferredImages();

  //
  // Locate the PCI root bridges and make the PCI bus driver connect each,
  // non-recursively. This will produce a number of child handles with PciIo on
  // them.
  //
  FilterAndProcess(&gEfiPciRootBridgeIoProtocolGuid, NULL, Connect);

  //
  // Find all display class PCI devices (using the handles from the previous
  // step), and connect them non-recursively. This should produce a number of
  // child handles with GOPs on them.
  //
  FilterAndProcess(&gEfiPciIoProtocolGuid, IsPciDisplay, Connect);

  //
  // Now add the device path of all handles with GOP on them to ConOut and
  // ErrOut.
  //
  FilterAndProcess(&gEfiGraphicsOutputProtocolGuid, NULL, AddOutput);

  //
  // Add the hardcoded short-form USB keyboard device path to ConIn.
  //
  EfiBootManagerUpdateConsoleVariable(
      ConIn, (EFI_DEVICE_PATH_PROTOCOL *)&mUsbKeyboard, NULL);

  EFI_HANDLE *              handles;
  UINTN                     NoHandles;
  EFI_DEVICE_PATH_PROTOCOL *devicehandle;
  /*CHAR16 *devicepathtxt;*/
  // EfiBootManagerUpdateConsoleVariable(ConIn,
  //  (EFI_DEVICE_PATH_PROTOCOL*)&gQcomKeypadDeviceGuid, NULL);
  gBS->LocateHandleBuffer(
      ByProtocol, &gEfiSimpleTextInputExProtocolGuid, NULL, &NoHandles,
      &handles);
  devicehandle = DevicePathFromHandle(handles[1]);
  EfiBootManagerUpdateConsoleVariable(
      ConIn, devicehandle, NULL); /*
            devicepathtxt = ConvertDevicePathToText(devicehandle,TRUE,TRUE);
            DEBUG((DEBUG_ERROR,"There are %s handles\n",devicepathtxt));
            ASSERT(0);*/

  //
  // Add the hardcoded serial console device path to ConIn, ConOut, ErrOut.
  //
  ASSERT(FixedPcdGet8(PcdDefaultTerminalType) == 4);
  CopyGuid(&mSerialConsole.TermType.Guid, &gEfiTtyTermGuid);

  EfiBootManagerUpdateConsoleVariable(
      ConIn, (EFI_DEVICE_PATH_PROTOCOL *)&mSerialConsole, NULL);
  EfiBootManagerUpdateConsoleVariable(
      ConOut, (EFI_DEVICE_PATH_PROTOCOL *)&mSerialConsole, NULL);
  EfiBootManagerUpdateConsoleVariable(
      ErrOut, (EFI_DEVICE_PATH_PROTOCOL *)&mSerialConsole, NULL);

  //
  // Register platform-specific boot options and keyboard shortcuts.
  //
  PlatformRegisterOptionsAndKeys();
}

STATIC
VOID HandleCapsules(VOID)
{
  ESRT_MANAGEMENT_PROTOCOL *EsrtManagement;
  EFI_PEI_HOB_POINTERS      HobPointer;
  EFI_CAPSULE_HEADER *      CapsuleHeader;
  BOOLEAN                   NeedReset;
  EFI_STATUS                Status;

  DEBUG((DEBUG_INFO, "%a: processing capsules ...\n", __FUNCTION__));

  Status = gBS->LocateProtocol(
      &gEsrtManagementProtocolGuid, NULL, (VOID **)&EsrtManagement);
  if (!EFI_ERROR(Status)) {
    EsrtManagement->SyncEsrtFmp();
  }

  //
  // Find all capsule images from hob
  //
  HobPointer.Raw = GetHobList();
  NeedReset      = FALSE;
  while ((HobPointer.Raw =
              GetNextHob(EFI_HOB_TYPE_UEFI_CAPSULE, HobPointer.Raw)) != NULL) {
    CapsuleHeader = (VOID *)(UINTN)HobPointer.Capsule->BaseAddress;

    Status = ProcessCapsuleImage(CapsuleHeader);
    if (EFI_ERROR(Status)) {
      DEBUG(
          (DEBUG_ERROR, "%a: failed to process capsule %p - %r\n", __FUNCTION__,
           CapsuleHeader, Status));
      return;
    }

    NeedReset      = TRUE;
    HobPointer.Raw = GET_NEXT_HOB(HobPointer);
  }

  if (NeedReset) {
    DEBUG(
        (DEBUG_WARN, "%a: capsule update successful, resetting ...\n",
         __FUNCTION__));

    gRT->ResetSystem(EfiResetCold, EFI_SUCCESS, 0, NULL);
    CpuDeadLoop();
  }
}

#define VERSION_STRING_PREFIX L"Tianocore/EDK2 firmware version "

#ifdef SAMURAI_ENABLE_EUD
/**
  SAMURAI: write an ASCII string to the EUD COM TX FIFO so the host can read
  it on the "Qualcomm EUD Port 9505 (COMx)" port.  Register map taken from
  the stock kernel driver drivers/soc/qcom/eud.c:
    +0x0000 TX_ID  (must read back as UART_ID 0x90)
    +0x0008 TX_DAT (one byte per write, same as eud_uart_tx())
**/
STATIC
VOID
SamuraiEudComPuts (
  IN CONST CHAR8  *Msg
  )
{
  UINTN  Index;
  UINTN  Len;
  UINTN  Offset;
  UINTN  Chunk;
  UINT32 Reg;

  if (Msg == NULL) {
    return;
  }

  MmioWrite32 (0x088E0000U + 0x0000U, 0x90U);
  Reg = MmioRead32 (0x088E0000U + 0x0000U);
  //
  // NOTE: the EUD register block replicates the low byte into all four lanes
  // (writing 1 reads back 0x01010101).  The TX_ID readback is therefore only
  // informational - hardware status bits may also be ORed in (0x90 -> 0x99).
  // Never gate the data writes on an exact match.
  //
  (VOID)Reg;

  Len = 0;
  while (Msg[Len] != 0) {
    Len++;
  }

  //
  // The EUD COM TX FIFO is tiny: sending a whole string in one go truncates it
  // after a few payload bytes (observed: [ID][LEN] + 7 data bytes).  Send the
  // string in small chunks, each with its own [TX_ID][TX_LEN][DATA...] frame,
  // with generous gaps so the FIFO can drain.
  //
  for (Offset = 0; Offset < Len; Offset += 6) {
    Chunk = ((Len - Offset) > 6) ? 6 : (Len - Offset);
    MmioWrite32 (0x088E0000U + 0x0000U, 0x90U);
    MmioWrite32 (0x088E0000U + 0x0004U, (UINT32)Chunk);
    for (Index = 0; Index < Chunk; Index++) {
      MmioWrite32 (0x088E0000U + 0x0008U, (UINT32)(UINT8)Msg[Offset + Index]);
      gBS->Stall (10000);
    }
    gBS->Stall (50000);
  }
}
#endif

/**
  Do the platform specific action after the console is ready
  Possible things that can be done in PlatformBootManagerAfterConsole:
  > Console post action:
    > Dynamically switch output mode from 100x31 to 80x25 for certain scenario
    > Signal console ready platform customized event
  > Run diagnostics like memory testing
  > Connect certain devices
  > Dispatch additional option roms
  > Special boot: e.g.: USB boot, enter UI
**/
VOID EFIAPI PlatformBootManagerAfterConsole(VOID)
{
  EFI_STATUS                    Status;
  EFI_GRAPHICS_OUTPUT_PROTOCOL *GraphicsOutput;
  UINTN                         FirmwareVerLength;
  UINTN                         PosX;
  UINTN                         PosY;

  FirmwareVerLength = StrLen(PcdGetPtr(PcdFirmwareVersionString));

  //
  // Show the splash screen.
  //
  Status = BootLogoEnableLogo();
  if (EFI_ERROR(Status)) {
    if (FirmwareVerLength > 0) {
      Print(VERSION_STRING_PREFIX L"%s\n", PcdGetPtr(PcdFirmwareVersionString));
    }
#ifdef ENABLE_SIMPLE_INIT
    Print(L"Press any side button for SimpleInitGUI");
#else
    Print(L"Press any side button for Boot Options");
#endif
  }
  else if (FirmwareVerLength > 0) {
    Status = gBS->HandleProtocol(
        gST->ConsoleOutHandle, &gEfiGraphicsOutputProtocolGuid,
        (VOID **)&GraphicsOutput);
    if (!EFI_ERROR(Status)) {
      PosX = (GraphicsOutput->Mode->Info->HorizontalResolution -
              (StrLen(VERSION_STRING_PREFIX) + FirmwareVerLength) *
                  EFI_GLYPH_WIDTH) /
             2;
      PosY = 0;

      PrintXY(
          PosX, PosY, NULL, NULL, VERSION_STRING_PREFIX L"%s",
          PcdGetPtr(PcdFirmwareVersionString));
    }
  }

  //
  // Connect the rest of the devices.
  //
  EfiBootManagerConnectAll();

  //
  // On ARM, there is currently no reason to use the phased capsule
  // update approach where some capsules are dispatched before EndOfDxe
  // and some are dispatched after. So just handle all capsules here,
  // when the console is up and we can actually give the user some
  // feedback about what is going on.
  //
  HandleCapsules();

  //
  // SAMURAI: do NOT enumerate every device as a boot option.
  //
  // EfiBootManagerRefreshAllBootOption() creates an option for every handle that
  // has a device path, including devices that cannot be booted.  On this port that
  // produced eight entries ("UEFI Misc Device" x6 for the UFS LUNs and "UEFI
  // Non-Block Boot Device" x2).  BDS then tried each one, failed to load it, and
  // reported EFI_SW_DXE_BS_EC_BOOT_OPTION_LOAD_ERROR / BOOT_OPTION_FAILED about
  // nine times per boot.  Those records are only visible now that the EUD log ring
  // captures full DEBUG, but the load attempts always cost boot time.
  //
  // The menu entries this platform wants are registered explicitly below, and
  // SimpleInit enumerates partitions itself; anything else can be started from the
  // UEFI Shell (also registered below).  Uncommenting the call restores the stock
  // behaviour, which also auto-exposes every UFS LUN in the boot menu.
  //
  // EfiBootManagerRefreshAllBootOption();

  //
  // Register UEFI Shell
  //
  PlatformRegisterFvBootOption(
      &gUefiShellFileGuid, L"UEFI Shell", LOAD_OPTION_ACTIVE, NULL);

#ifdef ENABLE_LINUX_SIMPLE_MASS_STORAGE
  //
  // Register Built-in Linux Kernel
  //
  PlatformRegisterFvBootOption(
      &gLinuxSimpleMassStorageGuid, L"USB Attached SCSI (UAS) Storage", LOAD_OPTION_ACTIVE,
      NULL);
#endif

#ifdef SAMURAI_LINUX_KERNEL
#endif

#ifdef AB_SLOTS_SUPPORT
  //
  // Register Switch Slots App
  //
  PlatformRegisterFvBootOption(
      &gSwitchSlotsAppFileGuid, L"Reboot to other slot", LOAD_OPTION_ACTIVE, NULL);
#endif

#ifdef SAMURAI_ENABLE_EUD
  //
  // SAMURAI: enable the Qualcomm Embedded USB Debugger (EUD) so a host PC can
  // attach OpenOCD (JTAG/SWD over USB) while UEFI is running.
  //
  //   EUD base = 0x088E0000          (DTB: qcom,msm-eud@88e0000)
  //   +0x1014  = BIT(0) -> CSR_EUD_EN
  //   +0x0024  = 0x1C   -> INT1_EN_MASK (VBUS|CHGR|SAFE_MODE)
  //
  // Same two writes the Linux "eud" driver performs in enable_eud(); EUD is not
  // fused off on this device.  Note: EUD hijacks the USB port, so fastboot and
  // USB mass-storage mode are unavailable until the next power cycle.
  //
  {
    UINTN  EudTry;
    for (EudTry = 0; EudTry < 10; EudTry++) {
      MmioWrite32 (0x088E0000U + 0x1014U, 1U);
      MmioWrite32 (0x088E0000U + 0x0024U, 0x1CU);
      gBS->Stall (200000);
    }
    Print (
      L"[SAMURAI-EUD] CSR_EUD_EN=0x%08x INT1_EN_MASK=0x%08x\n",
      MmioRead32 (0x088E0000U + 0x1014U),
      MmioRead32 (0x088E0000U + 0x0024U)
      );
  }

    SamuraiEudComPuts ("[SAMURAI-EUD-COM] direct FIFO path\r\n");

    //
    // From here on DEBUG() flows over the EUD COM SerialPortLib.  Emit one
    // marker so the host can confirm the channel is alive.
    //
    DEBUG ((DEBUG_ERROR, "[SAMURAI-EUD-COM] SerialPortLib ready\n"));
#endif

  PlatformSetup();

#ifdef SAMURAI_LINUX_KERNEL
  //
  // SAMURAI: find the mainline Linux kernel on a file system, register it and start it.
  // Kept last on purpose: EUD is enabled above, so the complete earlycon log of the
  // kernel reaches a host PC that already ran "eudtool com-up".
  //
  SamuraiRegisterKernelBootOption ();
#endif
}

/**
  This function is called each second during the boot manager waits the
  timeout.

  @param TimeoutRemain  The remaining timeout.
**/
VOID EFIAPI PlatformBootManagerWaitCallback(UINT16 TimeoutRemain)
{
#ifdef SAMURAI_ENABLE_EUD
  {
    STATIC UINT32  EudComTick = 0;
    CHAR8          EudComBuf[64];

    AsciiSPrint (EudComBuf, sizeof (EudComBuf), "[SAMURAI-EUD-COM] tick %u\r\n", EudComTick++);
    SamuraiEudComPuts (EudComBuf);
  }
#endif

  EFI_GRAPHICS_OUTPUT_BLT_PIXEL_UNION Black;
  EFI_GRAPHICS_OUTPUT_BLT_PIXEL_UNION White;
  UINT16                              Timeout;
  EFI_STATUS                          Status;

  Timeout = PcdGet16(PcdPlatformBootTimeOut);

  if (Timeout != 0 && TimeoutRemain <= 0) {
    gST->ConOut->ClearScreen(gST->ConOut);
    BootLogoEnableLogo ();
    return;
  }

  Black.Raw = 0x00000000;
  White.Raw = 0x00FFFFFF;

  Status = BootLogoUpdateProgress(
      White.Pixel, Black.Pixel,
#ifdef ENABLE_SIMPLE_INIT
      L"Press any side button for SimpleInitGUI",
#else
      L"Press any side button for Boot Options",
#endif
      White.Pixel, (Timeout - TimeoutRemain) * 100 / Timeout, 0);
  if (EFI_ERROR(Status)) {
    Print(L".");
  }
}

/**
  The function is called when no boot option could be launched,
  including platform recovery options and options pointing to applications
  built into firmware volumes.

  If this function returns, BDS attempts to enter an infinite loop.
**/
VOID EFIAPI PlatformBootManagerUnableToBoot(VOID) { return; }
