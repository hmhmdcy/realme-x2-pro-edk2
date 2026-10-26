import io, struct, os
def gb(s):
    p = s.split('-')
    return struct.pack('<IHH', int(p[0],16), int(p[1],16), int(p[2],16)) + bytes.fromhex(p[3]) + bytes.fromhex(p[4])
T = {'60759B13':'60759B13-A8BF-46FE-B7E6-797BFB335DF3','9BA45B66':'9BA45B66-EFA4-441C-A3E4-ED2224786BE2'}
for k,g in T.items():
    print('===', k, '(? sm8150 ??????????) ===')
    root = 'Platform/EFI_Binaries/Drivers/sm8150'
    for dp, dn, fs in os.walk(root):
        for fn in fs:
            if not fn.lower().endswith('.efi'):
                continue
            p = os.path.join(dp, fn)
            try:
                d = io.open(p, 'rb').read()
            except Exception:
                continue
            c = d.count(gb(g))
            if c:
                print('   %-70s x%d' % (p.replace('Platform/EFI_Binaries/Drivers/sm8150/',''), c))
