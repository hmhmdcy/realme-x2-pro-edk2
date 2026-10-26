import io, re, sys
def strings(path, minlen=5):
    d = io.open(path, 'rb').read()
    return re.findall(rb'[ -~]{%d,}' % minlen, d)
KEYS = ('key', 'gpio', 'volume', 'vol_', 'pwr', 'pmic', 'pon', 'scan', 'button', 'resin', 'kpdpwr', 'dal', 'config', 'matrix')
files = sys.argv[1:]
for f in files:
    print('=' * 70)
    print(f)
    try:
        ss = strings(f)
    except Exception as e:
        print('  ERR', e); continue
    seen = set()
    for s in ss:
        t = s.decode('utf-8', 'replace')
        low = t.lower()
        if any(k in low for k in KEYS):
            if t in seen: continue
            seen.add(t)
            print('   ', t)
