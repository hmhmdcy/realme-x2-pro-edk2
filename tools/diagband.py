import re, sys, io
FB = '0x9D000000ULL'
BANDS = [
    ('Silicon/Qualcomm/sm8150/Library/PlatformPrePiLib/PlatformUtils.c', 'VOID PlatformInitialize(VOID)', 0,  '0xFF0000FF'),
    ('Silicon/Qualcomm/QcomPkg/Library/MemoryInitPeiLib/MemoryInitPeiLib.c', 'MemoryPeim(IN EFI_PHYSICAL_ADDRESS', 80, '0xFF00FF00'),
    ('Common/edk2/MdeModulePkg/Core/Dxe/DxeMain/DxeMain.c', 'DxeMain (', 160, '0xFFFF00FF'),
    ('Common/edk2/MdeModulePkg/Universal/BdsDxe/BdsEntry.c', 'BdsEntry (', 240, '0xFFFFFF00'),
]
def snippet(y, color):
    return ('\n  { /* DIAGBAND y=%d */\n'
            '    volatile UINT32 *DiagFb = (volatile UINT32 *)(UINTN)(%s + (%dULL * 1080ULL * 4ULL));\n'
            '    UINTN DiagI;\n'
            '    for (DiagI = 0; DiagI < (UINTN)(80ULL * 1080ULL); DiagI++) { DiagFb[DiagI] = %s; }\n'
            '  }\n') % (y, FB, y, color)
for path, anchor, y, color in BANDS:
    try:
        s = io.open(path, encoding='utf-8', errors='replace').read()
    except Exception as e:
        print('MISS', path, e); continue
    if 'DIAGBAND' in s:
        print('SKIP already patched', path); continue
    i = s.find(anchor)
    if i < 0:
        print('ANCHOR-NOT-FOUND', path, '|', anchor); continue
    j = s.find('\n{\n', i)
    if j < 0:
        print('BRACE-NOT-FOUND', path); continue
    k = j + len('\n{\n')
    s2 = s[:k] + snippet(y, color) + s[k:]
    io.open(path, 'w', encoding='utf-8', newline='\n').write(s2)
    print('PATCHED', path, 'band y=%d' % y)
