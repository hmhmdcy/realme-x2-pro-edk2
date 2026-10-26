[Defines]
  VENDOR_NAME                    = Realme
  PLATFORM_NAME                  = samurai
  PLATFORM_GUID                  = d0b7e40c-fde6-4c06-9ee7-516918a4c0cb
  PLATFORM_VERSION               = 0.1
  DSC_SPECIFICATION              = 0x00010019
  OUTPUT_DIRECTORY               = Build/$(PLATFORM_NAME)
  SUPPORTED_ARCHITECTURES        = AARCH64
  BUILD_TARGETS                  = DEBUG|RELEASE
  SKUID_IDENTIFIER               = DEFAULT
  FLASH_DEFINITION               = Platform/Qualcomm/sm8150/sm8150.fdf
  DEVICE_DXE_FV_COMPONENTS       = Platform/Realme/sm8150/samurai.fdf.inc

  # A/B Slot Environment
  AB_SLOTS_SUPPORT               = FALSE

!include Platform/Qualcomm/sm8150/sm8150.dsc

[BuildOptions.common]
  GCC:*_*_AARCH64_CC_FLAGS = -DHAS_MLVM -DENABLE_SIMPLE_INIT -DENABLE_LINUX_SIMPLE_MASS_STORAGE -DSAMURAI_ENABLE_EUD -DSAMURAI_LINUX_KERNEL

[PcdsFixedAtBuild.common]
  gQcomTokenSpaceGuid.PcdMipiFrameBufferWidth|1080
  gQcomTokenSpaceGuid.PcdMipiFrameBufferHeight|2400
  gQcomTokenSpaceGuid.PcdMipiFrameBufferAddress|0x9D000000
  gEfiMdePkgTokenSpaceGuid.PcdDebugPrintErrorLevel|0x800B05C7

  # Simple Init
  gSimpleInitTokenSpaceGuid.PcdGuiDefaultDPI|400

  gRenegadePkgTokenSpaceGuid.PcdDeviceVendor|"Realme"
  gRenegadePkgTokenSpaceGuid.PcdDeviceProduct|"X2 Pro"
  gRenegadePkgTokenSpaceGuid.PcdDeviceCodeName|"samurai"


[LibraryClasses.common.DXE_DRIVER]
  SerialPortLib|Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.inf

[LibraryClasses.common.DXE_RUNTIME_DRIVER]
  SerialPortLib|Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.inf

[LibraryClasses.common.UEFI_DRIVER]
  SerialPortLib|Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.inf

[LibraryClasses.common.UEFI_APPLICATION]
  SerialPortLib|Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.inf


[Components.common]
  Platform/Realme/sm8150/EudLogDxe/EudLogDxe.inf
