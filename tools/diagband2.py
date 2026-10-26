import io
p = 'Silicon/Qualcomm/sm8150/Library/PlatformPrePiLib/PlatformUtils.c'
s = io.open(p, encoding='utf-8', errors='replace').read()
if 'DIAGBAND' in s:
    print('SKIP pre-patched')
else:
    i = s.find('PlatformInitialize')
    j = s.find('\n{\n', i)
    snip = ('\n  { /* DIAGBAND y=0 */\n'
            '    volatile UINT32 *DiagFb = (volatile UINT32 *)(UINTN)(0x9D000000ULL + (0ULL * 1080ULL * 4ULL));\n'
            '    UINTN DiagI;\n'
            '    for (DiagI = 0; DiagI < (UINTN)(80ULL * 1080ULL); DiagI++) { DiagFb[DiagI] = 0xFF0000FF; }\n'
            '  }\n')
    k = j + len('\n{\n')
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s[:k] + snip + s[k:])
    print('PATCHED', p)
d = 'Platform/Realme/sm8150/samurai.dsc'
t = io.open(d, encoding='utf-8', errors='replace').read()
if 'PcdMipiFrameBufferAddress' in t:
    print('SKIP pcd already set')
else:
    t = t.replace('gQcomTokenSpaceGuid.PcdMipiFrameBufferHeight|2400',
                  'gQcomTokenSpaceGuid.PcdMipiFrameBufferHeight|2400\n  gQcomTokenSpaceGuid.PcdMipiFrameBufferAddress|0x9D000000', 1)
    io.open(d, 'w', encoding='utf-8', newline='\n').write(t)
    print('PCD set')
