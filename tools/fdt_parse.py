import struct, sys
def u32(d, o): return struct.unpack_from('>I', d, o)[0]
def walk(d, path):
    print('== FDT', path, 'totalsize', u32(d, 4), 'version', u32(d, 20))
    off = u32(d, 8); end = off + u32(d, 36); so = u32(d, 12)
    pos = off; depth = 0; stack = []; node = []
    mem = 0
    while pos < end:
        tok = u32(d, pos); pos += 4
        if tok == 1:
            j = d.index(b'\x00', pos); nm = d[pos:j].decode('utf-8', 'replace')
            pos = (j + 4) & ~3
            depth += 1; stack.append(nm); node = [nm, [], depth]
        elif tok == 2:
            nm, props, dep = node
            full = '/'.join([s for s in stack if s])
            ismem = nm.startswith('memory') or any(k == 'device_type' and v.rstrip(b'\x00') == b'memory' for k, v in props)
            if ismem or 'reserved-memory' in full:
                regs = []
                for k, v in props:
                    if k == 'reg':
                        for i in range(0, len(v) - 7, 16):
                            a, s = struct.unpack_from('>QQ', v, i)
                            regs.append((a, s))
                    if k in ('compatible', 'device_type', 'status', 'no-map', 'reusable'):
                        regs.append((k, v.rstrip(b'\x00').decode('utf-8', 'replace')))
                print('  ', full, regs)
                if ismem and regs: mem += 1
            depth -= 1; stack.pop()
            if stack: node = [stack[-1], [], depth]
        elif tok == 3:
            ln = u32(d, pos); no = u32(d, pos + 4); pos += 8
            v = d[pos:pos + ln]; pos = (pos + ln + 3) & ~3
            j = d.index(b'\x00', so + no); name = d[so + no:j].decode()
            node[1].append((name, v))
        elif tok == 4:
            pass
        elif tok == 9:
            break
        else:
            print('  bad token', tok, 'at', pos); break
for p in sys.argv[1:]:
    walk(open(p, 'rb').read(), p)
