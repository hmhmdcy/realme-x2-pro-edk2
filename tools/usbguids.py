import io, re
files = ['Platform/Qualcomm/sm8150/Apriori.fdf.inc', 'Platform/Realme/sm8150/samurai.fdf.inc']
pat = re.compile(r'FILE DRIVER = ([0-9a-fA-F-]{36})\s*\{(.*?)\n\s*\}', re.S)
ui = re.compile(r'SECTION UI = "([^"]+)"')
pairs = []
for f in files:
    s = io.open(f, encoding='utf-8', errors='replace').read()
    for m in pat.finditer(s):
        g = m.group(1); b = m.group(2)
        n = ui.search(b)
        pairs.append((g, n.group(1) if n else '?'))
want = ('usb', 'xhci')
seen = set()
for g, n in pairs:
    if any(w in n.lower() for w in want):
        key = (g.lower(), n)
        if key in seen: continue
        seen.add(key)
        print('%-40s %s' % (g, n))
print('--- total FILE DRIVER entries:', len(pairs))
