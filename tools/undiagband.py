import io, re, glob
files = [
  'Silicon/Qualcomm/sm8150/Library/PlatformPrePiLib/PlatformUtils.c',
  'Silicon/Qualcomm/QcomPkg/Library/MemoryInitPeiLib/MemoryInitPeiLib.c',
  'Common/edk2/MdeModulePkg/Core/Dxe/DxeMain/DxeMain.c',
  'Common/edk2/MdeModulePkg/Universal/BdsDxe/BdsEntry.c',
]
pat = re.compile(r'\n  \{ /\* DIAGBAND y=\d+ \*/.*?\n  \}\n', re.S)
for f in files:
    try:
        s = io.open(f, encoding='utf-8', errors='replace').read()
    except Exception as e:
        print('MISS', f, e); continue
    if 'DIAGBAND' not in s:
        print('CLEAN already', f); continue
    s2 = pat.sub('\n', s, count=1)
    io.open(f, 'w', encoding='utf-8', newline='\n').write(s2)
    print('REVERTED' if 'DIAGBAND' not in s2 else 'PARTIAL', f)
