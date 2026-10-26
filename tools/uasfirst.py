import io, re

# --- 1) revert DIAGUSB in BdsEntry.c ---
p = 'Common/edk2/MdeModulePkg/Universal/BdsDxe/BdsEntry.c'
s = io.open(p, encoding='utf-8', errors='replace').read()
if 'DIAGUSB' in s:
    s = re.sub(r'/\* DIAGUSB-BEGIN \*/.*?/\* DIAGUSB-END \*/\n\n', '', s, flags=re.S)
    s = re.sub(r'\n  /\* DIAGUSB-CALL \*/.*?\n  \}\n', '\n', s, flags=re.S)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('BdsEntry: DIAGUSB removed ->', 'DIAGUSB' not in s)
else:
    print('BdsEntry: already clean')

# --- 2) PlatformBm.c: boot UAS storage app first ---
q = 'Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c'
t = io.open(q, encoding='utf-8', errors='replace').read()
if 'DIAGUAS' in t:
    print('PlatformBm: already patched')
else:
    anchor = '      &gLinuxSimpleMassStorageGuid, L"USB Attached SCSI (UAS) Storage", LOAD_OPTION_ACTIVE);'
    i = t.find(anchor)
    if i < 0:
        print('ANCHOR not found'); raise SystemExit
    i += len(anchor)
    add = '''

  /* DIAGUAS-BEGIN: try the USB mass-storage (UAS) app first, fall back to normal boot */
  {
    EFI_BOOT_MANAGER_LOAD_OPTION  *UasOpts  = NULL;
    UINTN                         UasCount = 0;
    UINTN                         UasIdx;
    UasOpts = EfiBootManagerGetLoadOptions (&UasCount, LoadOptionTypeBoot);
    for (UasIdx = 0; UasIdx < UasCount; UasIdx++) {
      if ((UasOpts[UasIdx].Description != NULL) &&
          (StrCmp (UasOpts[UasIdx].Description, L"USB Attached SCSI (UAS) Storage") == 0)) {
        Print (L"\\n[DIAGUAS] launching USB mass-storage app ...\\n");
        EfiBootManagerBoot (&UasOpts[UasIdx]);
        Print (L"[DIAGUAS] USB mass-storage app returned\\n");
        break;
      }
    }
    if (UasOpts != NULL) {
      EfiBootManagerFreeLoadOptions (UasOpts, UasCount);
    }
  }
  /* DIAGUAS-END */
'''
    t = t[:i] + add + t[i:]
    io.open(q, 'w', encoding='utf-8', newline='\n').write(t)
    print('PlatformBm: DIAGUAS inserted')
