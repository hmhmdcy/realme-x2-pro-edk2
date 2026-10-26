import io, struct, sys
OP = {0x00:'BEFORE',0x01:'AFTER',0x02:'PUSH',0x03:'AND',0x04:'OR',0x05:'NOT',0x06:'TRUE',0x07:'FALSE',0x08:'END',0x09:'SOR'}
def guid_str(b):
    d1, d2, d3 = struct.unpack_from('<IHH', b, 0)
    return '%08X-%04X-%04X-%s-%s' % (d1, d2, d3, b[8:10].hex().upper(), b[10:16].hex().upper())
for f in sys.argv[1:]:
    d = io.open(f, 'rb').read()
    print('==', f, len(d), 'bytes')
    i = 0
    while i < len(d):
        op = d[i]; name = OP.get(op, 'OP%02X' % op); i += 1
        if name == 'PUSH':
            if i + 16 > len(d):
                print('   PUSH <truncated>'); break
            print('   PUSH', guid_str(d[i:i+16])); i += 16
        else:
            print('  ', name)
            if name == 'END':
                break
