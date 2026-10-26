// per-device BSP DXEs (extracted from stock samurai xbl.img)
// Factory ResetRuntimeDxe (reset reason service).  Missing from the shared
// sm8150 driver set; required by the factory realme ButtonsDxe / OppoProject.
FILE DRIVER = 3AE17DB7-3CC5-4B89-9304-9549211057EF {
    SECTION DXE_DEPEX = Platform/EFI_Binaries/Drivers/Devices/samurai/ResetRuntimeDxe/ResetRuntimeDxe.depex
    SECTION PE32 = Platform/EFI_Binaries/Drivers/Devices/samurai/ResetRuntimeDxe/ResetRuntimeDxe.efi
    SECTION UI = "ResetRuntimeDxe"
}

// OPPO project protocol provider (OcdtDxe).  Required at runtime by the
// factory realme/OPPO ButtonsDxe; without it ButtonsDxe fails to start.
// Binary from mu_aloha_platforms device realme-rmx2086 (SM8150 / SDM855LA_Core build).
FILE DRIVER = 68A710AB-A58D-4C0B-BE1E-5F6EE2C36AD8 {
    SECTION DXE_DEPEX = Platform/EFI_Binaries/Drivers/Devices/samurai/OcdtDxe/OppoProject.depex
    SECTION PE32 = Platform/EFI_Binaries/Drivers/Devices/samurai/OcdtDxe/OppoProject.efi
    SECTION UI = "OppoProject"
}

FILE DRIVER = 8e9bd160-b184-11df-94e2-0800200c9a66 {
    SECTION DXE_DEPEX = Platform/EFI_Binaries/Drivers/Devices/samurai/DALSys/DALSys.depex
    SECTION PE32 = Platform/EFI_Binaries/Drivers/Devices/samurai/DALSys/DALSys.efi
    SECTION UI = "DALSys"
}

FILE DRIVER = 5bd181db-0487-4f1a-ae73-820e165611b3 {
    SECTION DXE_DEPEX = Platform/EFI_Binaries/Drivers/Devices/samurai/ButtonsDxe/ButtonsDxe.depex
    SECTION PE32 = Platform/EFI_Binaries/Drivers/Devices/samurai/ButtonsDxe/ButtonsDxe.efi
    SECTION UI = "ButtonsDxe"
}

FILE DRIVER = 11faed4c-b21f-4d88-8e48-c4c28a1e50df {
    SECTION DXE_DEPEX = Platform/EFI_Binaries/Drivers/Devices/samurai/UsbPwrCtrlDxe/UsbPwrCtrlDxe.depex
    SECTION PE32 = Platform/EFI_Binaries/Drivers/Devices/samurai/UsbPwrCtrlDxe/UsbPwrCtrlDxe.efi
    SECTION UI = "UsbPwrCtrlDxe"
}

// ACPI Tables
FILE FREEFORM = 7E374E25-8E01-4FEE-87F2-390C23C606CD {
    SECTION RAW = Platform/Realme/sm8150/AcpiTables/samurai/DSDT.aml
    SECTION RAW = Silicon/Qualcomm/sm8150/AcpiTables/BuiltIn/APIC.aml
    SECTION RAW = Silicon/Qualcomm/sm8150/AcpiTables/BuiltIn/CSRT.aml
    SECTION RAW = Silicon/Qualcomm/sm8150/AcpiTables/BuiltIn/DBG2.aml
    SECTION RAW = Silicon/Qualcomm/sm8150/AcpiTables/BuiltIn/FACP.aml
    SECTION RAW = Silicon/Qualcomm/sm8150/AcpiTables/BuiltIn/GTDT.aml
    SECTION RAW = Silicon/Qualcomm/sm8150/AcpiTables/BuiltIn/IORT.aml
    SECTION RAW = Silicon/Qualcomm/sm8150/AcpiTables/BuiltIn/MCFG.aml
    SECTION RAW = Silicon/Qualcomm/sm8150/AcpiTables/BuiltIn/PPTT.aml
    SECTION RAW = Silicon/Qualcomm/sm8150/AcpiTables/BuiltIn/TPM2.aml
    SECTION UI = "AcpiTables"
}

// Mainline device tree blob
FILE FREEFORM = 25462CDA-221F-47DF-AC1D-259CFAA4E326 {
  SECTION RAW = Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb
}

// Factory TLMMDxe (provides EFI_QCOM_TLMM_PROTOCOL) - required by the factory ButtonsDxe for VOL-/VOL+ GPIO
FILE DRIVER = 8681CC5B-0DF6-441E-B4B8-E915C538F067 {
    SECTION DXE_DEPEX = Platform/EFI_Binaries/Drivers/Devices/samurai/TLMMDxe/TLMMDxe.depex
    SECTION PE32 = Platform/EFI_Binaries/Drivers/Devices/samurai/TLMMDxe/TLMMDxe.efi
    SECTION UI = "TLMMDxe"
}

  // EUD log drainer: replays the fixed-address ring buffer declared in
  // Platform/Realme/sm8150/Library/EudSerialPortLib/EudLog.h into the EUD COM
  // TX FIFO once a host PC has attached.
  INF Platform/Realme/sm8150/EudLogDxe/EudLogDxe.inf

// SAMURAI: the mainline Linux kernel is NOT in this firmware volume.  A 30 MiB
// blob cannot be stored as an FFS file (24 bit size field) and the 62 MiB volume
// that resulted did not fit the PrePi memory pool, so the DXE core was never
// loaded.  The kernel lives on the FAT partition named "logdump" instead and
// PlatformBm.c finds it there.  See HANDOVER-NEXT.md section 20.
