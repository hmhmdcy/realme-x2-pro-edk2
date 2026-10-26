import io, struct, os, sys
def gb(s):
    p = s.split('-')
    return struct.pack('<IHH', int(p[0],16), int(p[1],16), int(p[2],16)) + bytes.fromhex(p[3]) + bytes.fromhex(p[4])
TARGETS = {
    '60759B13': '60759B13-A8BF-46FE-B7E6-797BFB335DF3',
    '9BA45B66': '9BA45B66-EFA4-441C-A3E4-ED2224786BE2',
    '13A3F0F6': '13A3F0F6-264A-3EF0-F2E0-DEC512342F34',
}
root = 'Platform/EFI_Binaries'
hits = {k: [] for k in TARGETS}
for dirpath, dirs, files in os.walk(root):
    for fn in files:
        if not fn.lower().endswith(('.efi', '.depex')):
            continue
        p = os.path.join(dirpath, fn)
        try:
            d = io.open(p, 'rb').read()
        except Exception:
            continue
        for k, g in TARGETS.items():
            if gb(g) in d:
                hits[k].append(p)
for k in TARGETS:
    print('==', k, TARGETS[k])
    for p in hits[k][:10]:
        print('    ', p)
    if not hits[k]:
        print('     (???)')
