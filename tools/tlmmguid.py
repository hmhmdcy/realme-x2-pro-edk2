import io, struct, sys
def gb(s):
    p = s.split('-')
    return struct.pack('<IHH', int(p[0],16), int(p[1],16), int(p[2],16)) + bytes.fromhex(p[3]) + bytes.fromhex(p[4])
TLMM   = 'ad9aec18-7bf0-4809-9e96-3012309f3df7'
TLMMRT = 'cc3f4da6-51ee' + ''  # placeholder fix below
TLMMRT = 'cc3f4da6-a51e-4fb7-98d1-a06eb85d8e1e'
for f in sys.argv[1:]:
    d = io.open(f, 'rb').read()
    print('==', f, len(d))
    print('   TLMM protocol guid      :', d.count(gb(TLMM)))
    print('   TLMM RT protocol guid   :', d.count(gb(TLMMRT)))
