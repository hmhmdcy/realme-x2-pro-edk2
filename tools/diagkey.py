import io, re
p = 'Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c'
s = io.open(p, encoding='utf-8', errors='replace').read()

# 1) remove old DIAGUAS block
if 'DIAGUAS' in s:
    s = re.sub(r'\n  /\* DIAGUAS-BEGIN.*?/\* DIAGUAS-END \*/\n', '\n', s, flags=re.S)
    print('DIAGUAS removed')

if 'DIAGKEY' in s:
    print('already patched'); raise SystemExit

anchor = '      &gLinuxSimpleMassStorageGuid, L"USB Attached SCSI (UAS) Storage", LOAD_OPTION_ACTIVE);'
i = s.find(anchor)
if i < 0:
    print('ANCHOR not found'); raise SystemExit
i += len(anchor)

add = r'''

  /* DIAGKEY-BEGIN: input diagnostics + key echo window */
  {
    EFI_GUID     mDrvGuids[] = {
      { 0x5bd181db, 0x0487, 0x4f1a, { 0xae, 0x73, 0x82, 0x0e, 0x16, 0x56, 0x11, 0xb3 } },
      { 0x408edcec, 0xcf6d, 0x477c, { 0xa5, 0xa8, 0xb4, 0x84, 0x4e, 0x3d, 0xe2, 0x81 } },
      { 0x5776232e, 0x082d, 0x4b75, { 0x9a, 0x0e, 0xfe, 0x1d, 0x13, 0xf7, 0xa5, 0xd9 } },
    };
    CHAR16       *mDrvNames[] = { L"ButtonsDxe", L"ConSplitterDxe", L"PmicDxe" };
    EFI_GUID     LiGuid   = { 0x5b1b31a1, 0x9562, 0x11d2, { 0x8e, 0x3f, 0x00, 0xa0, 0xc9, 0x69, 0x72, 0x3b } };
    EFI_GUID     InGuid   = { 0x387477c1, 0x69c7, 0x11d2, { 0x8e, 0x39, 0x00, 0xa0, 0xc9, 0x69, 0x72, 0x3b } };
    EFI_GUID     InExGuid = { 0xdd9e7534, 0x7762, 0x4698, { 0x8c, 0x14, 0xf5, 0x85, 0x17, 0xa6, 0x25, 0xaa } };
    EFI_STATUS   St;
    UINTN        N = 0, NIn = 0, NInEx = 0, i, j;
    EFI_HANDLE   *H = NULL;
    EFI_HANDLE   *T = NULL;
    BOOLEAN      GotKey = FALSE;

    St = gBS->LocateHandleBuffer (ByProtocol, &InGuid, NULL, &NIn, &T);
    if (T != NULL) { gBS->FreePool (T); T = NULL; }
    St = gBS->LocateHandleBuffer (ByProtocol, &InExGuid, NULL, &NInEx, &T);
    if (T != NULL) { gBS->FreePool (T); T = NULL; }
    St = gBS->LocateHandleBuffer (ByProtocol, &LiGuid, NULL, &N, &H);

    Print (L"\n=== DIAGKEY ConIn=%s SimpleTextIn=%d InEx=%d images=%d ===\n",
           (gST->ConIn != NULL) ? L"yes" : L"NO", NIn, NInEx, N);
    if (!EFI_ERROR (St) && (H != NULL)) {
      for (j = 0; j < ARRAY_SIZE (mDrvGuids); j++) {
        CHAR16  G[64];
        BOOLEAN Found = FALSE;
        UnicodeSPrint (G, sizeof (G), L"%g", &mDrvGuids[j]);
        for (i = 0; i < N; i++) {
          EFI_LOADED_IMAGE_PROTOCOL  *Li = NULL;
          CHAR16                     *PathText;
          if (EFI_ERROR (gBS->HandleProtocol (H[i], &LiGuid, (VOID **)&Li)) || (Li == NULL) || (Li->FilePath == NULL)) {
            continue;
          }
          PathText = ConvertDevicePathToText (Li->FilePath, TRUE, TRUE);
          if (PathText != NULL) {
            if (StrStr (PathText, G) != NULL) { Found = TRUE; }
            FreePool (PathText);
          }
          if (Found) { break; }
        }
        Print (L"  %s %s\n", mDrvNames[j], Found ? L"LOADED" : L"missing");
      }
      gBS->FreePool (H);
    }
    Print (L"[DIAGKEY] press VOLUME keys now (30s window) ...\n");
    if (gST->ConIn != NULL) {
      for (i = 0; i < 60; i++) {
        EFI_INPUT_KEY  Key;
        if (!EFI_ERROR (gST->ConIn->ReadKeyStroke (gST->ConIn, &Key))) {
          Print (L"[DIAGKEY] KEY scan=0x%04x unicode=0x%04x\n", Key.ScanCode, Key.UnicodeChar);
          GotKey = TRUE;
        }
        gBS->Stall (500000);
      }
    }
    Print (L"=== DIAGKEY end (key=%s) ===\n", GotKey ? L"YES" : L"NO");

    if (!GotKey) {
      EFI_BOOT_MANAGER_LOAD_OPTION  *UasOpts  = NULL;
      UINTN                         UasCount = 0;
      UINTN                         UasIdx;
      UasOpts = EfiBootManagerGetLoadOptions (&UasCount, LoadOptionTypeBoot);
      for (UasIdx = 0; UasIdx < UasCount; UasIdx++) {
        if ((UasOpts[UasIdx].Description != NULL) &&
            (StrCmp (UasOpts[UasIdx].Description, L"USB Attached SCSI (UAS) Storage") == 0)) {
          Print (L"[DIAGKEY] no key -> launching mass-storage kernel\n");
          EfiBootManagerBoot (&UasOpts[UasIdx]);
          Print (L"[DIAGKEY] mass-storage kernel returned\n");
          break;
        }
      }
      if (UasOpts != NULL) { EfiBootManagerFreeLoadOptions (UasOpts, UasCount); }
    } else {
      Print (L"[DIAGKEY] key detected -> continue to UEFI boot menu\n");
    }
  }
  /* DIAGKEY-END */
'''
s = s[:i] + add + s[i:]
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('DIAGKEY inserted')
