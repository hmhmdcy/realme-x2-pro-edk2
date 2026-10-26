import io, re
p = 'Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c'
s = io.open(p, encoding='utf-8', errors='replace').read()
if 'Library/PrintLib.h' in s:
    print('include already present')
else:
    m = list(re.finditer(r'^#include <Library/[^>]+>$', s, re.M))
    if not m:
        print('no include anchor'); raise SystemExit
    last = m[-1]
    s = s[:last.end()] + '\n#include <Library/PrintLib.h>' + s[last.end():]
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('PrintLib.h include added')
