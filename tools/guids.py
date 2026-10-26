import io, struct, sys, glob
def guid_bytes(s):
    p = s.split('-')
    d1 = int(p[0], 16); d2 = int(p[1], 16); d3 = int(p[2], 16)
    d4 = bytes.fromhex(p[3]); d5 = bytes.fromhex(p[4])
    return struct.pack('<IHH', d1, d2, d3) + d4 + d5
GUIDS = {
    'SimpleTextIn':    '387477C1-69C7-11D2-8E39-00A0C969723B',
    'SimpleTextInEx':  'DD9E7534-7762-4698-8C14-F58517A625AA',
    'SimpleTextOut':   '387477C2-69C7-11D2-8E39-00A0C969723B',
    'UsbIo':           '2B2F68D6-0CD2-44CF-8E8B-BBA20B1B5B18',
    'LoadedImage':     '5B1B31A1-9562-11D2-8E3F-00A0C969723B',
}
files = sys.argv[1:]
for f in files:
    try:
        d = io.open(f, 'rb').read()
    except Exception as e:
        print('MISS', f, e); continue
    print('==', f, len(d), 'bytes')
    for name, g in GUIDS.items():
        b = guid_bytes(g)
        print('   %-14s %d' % (name, d.count(b)))
