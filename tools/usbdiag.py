import io
p = 'Common/edk2/MdeModulePkg/Universal/BdsDxe/BdsEntry.c'
s = io.open(p, encoding='utf-8', errors='replace').read()
if 'DIAGUSB-BEGIN' in s:
    print('already patched'); raise SystemExit
helper = '''/* DIAGUSB-BEGIN */
STATIC EFI_EVENT mDiagUsbEvent = NULL;

STATIC
VOID
EFIAPI
DiagUsbReport (
  VOID
  )
{
  STATIC EFI_GUID mGuids[] = {
    { 0x11faed4c, 0xb21f, 0x4d88, { 0x8e, 0x48, 0xc4, 0xc2, 0x8a, 0x1e, 0x50, 0xdf } },
    { 0x94f8a6a7, 0xdc34, 0x4101, { 0x88, 0xc1, 0x99, 0x17, 0x9c, 0xce, 0xae, 0x83 } },
    { 0xbeb12bee, 0xf6e1, 0x11e1, { 0x9f, 0xb8, 0x6c, 0x62, 0x6d, 0xe4, 0xae, 0xb1 } },
    { 0xb7f50e91, 0xa759, 0x412c, { 0xad, 0xe4, 0xdc, 0xd0, 0x3e, 0x7f, 0x7c, 0x28 } },
    { 0x240612b7, 0xa063, 0x11d4, { 0x9a, 0x3a, 0x00, 0x90, 0x27, 0x3f, 0xc1, 0x4d } },
    { 0x2d2e62cf, 0x9ecf, 0x43b7, { 0x82, 0x19, 0x94, 0xe7, 0xfc, 0x71, 0x3d, 0xfe } },
    { 0x9fb4b4a7, 0x42c0, 0x4bcd, { 0x85, 0x40, 0x9b, 0xcc, 0x67, 0x11, 0xf8, 0x3e } },
    { 0xcd823a4d, 0x7dec, 0x4531, { 0xae, 0x5d, 0x41, 0x34, 0xfa, 0x41, 0x27, 0xb8 } },
    { 0x0a134f0e, 0x075e, 0x40b3, { 0x9c, 0x63, 0x3b, 0x39, 0x06, 0x80, 0x46, 0x63 } },
    { 0x3299a266, 0x15f0, 0x4346, { 0x83, 0x18, 0x71, 0x63, 0x36, 0x73, 0x6d, 0x3e } },
    { 0x8e9bd160, 0xb184, 0x11df, { 0x94, 0xe2, 0x08, 0x00, 0x20, 0x0c, 0x9a, 0x66 } },
  };
  STATIC CHAR16 *mNames[] = {
    L"UsbPwrCtrlDxe", L"UsbfnDwc3Dxe", L"XhciPciEmul", L"XhciDxe", L"UsbBusDxe",
    L"UsbKbDxe", L"UsbMassStor", L"UsbConfigDxe", L"UsbInitDxe", L"UsbDeviceDxe", L"DALSys"
  };
  EFI_GUID     LiGuid  = { 0x5b1b31a1, 0x9562, 0x11d2, { 0x8e, 0x3f, 0x00, 0xa0, 0xc9, 0x69, 0x72, 0x3b } };
  EFI_GUID     BlkGuid = { 0x964e5b21, 0x6459, 0x11d2, { 0x8e, 0x39, 0x00, 0xa0, 0xc9, 0x69, 0x72, 0x3b } };
  EFI_GUID     FsGuid  = { 0x964e5b22, 0x6459, 0x11d2, { 0x8e, 0x39, 0x00, 0xa0, 0xc9, 0x69, 0x72, 0x3b } };
  EFI_GUID     UsbGuid = { 0x2b2f68d6, 0x0cd2, 0x44cf, { 0x8e, 0x8b, 0xbb, 0xa2, 0x0b, 0x1b, 0x5b, 0x18 } };
  EFI_STATUS   Status;
  UINTN        N = 0, NBlk = 0, NFs = 0, NUsb = 0, i, j;
  EFI_HANDLE   *H = NULL;
  EFI_HANDLE   *Tmp = NULL;

  Status = gBS->LocateHandleBuffer (ByProtocol, &BlkGuid, NULL, &NBlk, &Tmp);
  if (Tmp != NULL) { gBS->FreePool (Tmp); Tmp = NULL; }
  Status = gBS->LocateHandleBuffer (ByProtocol, &FsGuid, NULL, &NFs, &Tmp);
  if (Tmp != NULL) { gBS->FreePool (Tmp); Tmp = NULL; }
  Status = gBS->LocateHandleBuffer (ByProtocol, &UsbGuid, NULL, &NUsb, &Tmp);
  if (Tmp != NULL) { gBS->FreePool (Tmp); Tmp = NULL; }
  Status = gBS->LocateHandleBuffer (ByProtocol, &LiGuid, NULL, &N, &H);

  Print (L"\\n=== DIAGUSB images=%d blk=%d fs=%d usb=%d ===\\n", N, NBlk, NFs, NUsb);
  if (!EFI_ERROR (Status) && (H != NULL)) {
    for (j = 0; j < ARRAY_SIZE (mGuids); j++) {
      CHAR16  G[64];
      BOOLEAN Found = FALSE;
      UnicodeSPrint (G, sizeof (G), L"%g", &mGuids[j]);
      for (i = 0; i < N; i++) {
        EFI_LOADED_IMAGE_PROTOCOL  *Li = NULL;
        CHAR16                     *T;
        if (EFI_ERROR (gBS->HandleProtocol (H[i], &LiGuid, (VOID **)&Li)) || (Li == NULL) || (Li->FilePath == NULL)) {
          continue;
        }
        T = ConvertDevicePathToText (Li->FilePath, TRUE, TRUE);
        if (T != NULL) {
          if (StrStr (T, G) != NULL) {
            Found = TRUE;
          }
          FreePool (T);
        }
        if (Found) {
          break;
        }
      }
      Print (L"  %s %s\\n", mNames[j], Found ? L"OK" : L"--");
    }
    gBS->FreePool (H);
  }
  Print (L"=== DIAGUSB-END ===\\n");
}

STATIC
VOID
EFIAPI
DiagUsbTimer (
  IN EFI_EVENT  Event,
  IN VOID       *Context
  )
{
  DiagUsbReport ();
}
/* DIAGUSB-END */

'''
anchor = '/**\n\n  Service routine for BdsInstance->Entry()'
i = s.find(anchor)
if i < 0:
    print('ANCHOR1 not found'); raise SystemExit
s = s[:i] + helper + s[i:]
call = '''  /* DIAGUSB-CALL */
  DiagUsbReport ();
  if (mDiagUsbEvent == NULL) {
    if (!EFI_ERROR (gBS->CreateEvent (EVT_TIMER | EVT_NOTIFY_SIGNAL, TPL_CALLBACK, DiagUsbTimer, NULL, &mDiagUsbEvent))) {
      gBS->SetTimer (mDiagUsbEvent, TimerPeriodic, 50000000);
    }
  }

'''
anchor2 = '  BOOLEAN                         PlatformRecovery;'
i2 = s.find(anchor2)
if i2 < 0:
    print('ANCHOR2 not found'); raise SystemExit
i2 += len(anchor2)
s = s[:i2] + '\n' + call + s[i2:]
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('PATCHED OK')
