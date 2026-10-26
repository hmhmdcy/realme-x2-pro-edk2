import struct, binascii, zlib, sys, re
def rep(path):
    d = open(path, 'rb').read()
    print('=' * 62)
    print(path, 'size', len(d))
    if d[:8] != b'ANDROID!':
        print('  not ANDROID ->', d[:8]); return
    ks, ka, rs, ra, ss, sa, tags, pg, hv, osv = struct.unpack_from('<10I', d, 8)
    print('  hdr_ver', hv, 'page', pg, 'kernel_size', ks, 'kernel_addr', hex(ka))
    print('  ramdisk_size', rs, 'ramdisk_addr', hex(ra), 'tags', hex(tags), 'second_size', ss)
    print('  name', d[48:64].rstrip(b'\x00'), 'cmdline', d[64:128].rstrip(b'\x00')[:60])
    if hv >= 2:
        rds = struct.unpack_from('<I', d, 1632)[0]
        rdo = struct.unpack_from('<Q', d, 1636)[0]
        hsz = struct.unpack_from('<I', d, 1644)[0]
        ds  = struct.unpack_from('<I', d, 1648)[0]
        da  = struct.unpack_from('<Q', d, 1652)[0]
        print('  v2: recovery_dtbo_size', rds, 'hdr_size', hsz, 'DTB_size', ds, 'DTB_addr', hex(da))
    print('  tail16', binascii.hexlify(d[-16:]).decode())
    k = d[pg:pg + ks]
    print('  kernel head', binascii.hexlify(k[:16]).decode())
    body = k; comp = 'raw'
    if k[:2] == b'\x1f\x8b':
        comp = 'gzip'
        o = zlib.decompressobj(16 + zlib.MAX_WBITS)
        body = o.decompress(k); body += o.flush()
        print('  kernel gzip -> payload', len(body), 'trailing', len(o.unused_data))
    print('  compression', comp, 'magic@0x38', body[0x38:0x3c])
    if body[0x38:0x3c] == b'ARM\x64':
        print('  text_offset', hex(struct.unpack_from('<Q', body, 8)[0]),
              'image_size', hex(struct.unpack_from('<Q', body, 0x10)[0]),
              'flags', hex(struct.unpack_from('<Q', body, 0x18)[0]))
    for lbl, buf in (('payload', body),):
        off = [m.start() for m in re.finditer(b'\xd0\x0d\xfe\xed', buf)]
        print('  FDT candidates in', lbl, [hex(x) for x in off[:3]])
        for x in off[:1]:
            tot = struct.unpack_from('>I', buf, x + 4)[0]
            if 0 < tot <= len(buf) - x:
                print('    fdt totalsize', hex(tot), 'strings', [s.decode() for s in re.findall(rb'[ -~]{6,}', buf[x:x+tot])[:3]])
for p in sys.argv[1:]:
    try: rep(p)
    except Exception as e: print(p, 'ERR', e)
