from pathlib import Path
import hashlib, json, lzma, struct, sys, uuid, zlib

root = Path('/mnt/e/edk2-samurai-out/kernel79')
dt_guid = '25462cda-221f-47df-ac1d-259cfaa4e326'
lz_guid = 'ee4e5898-3914-4259-9d6e-dc7bd79403cf'
cmd = ('earlycon=eud,mmio,0x88e0000 console=tty0 console=eud loglevel=7 '
       'ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused '
       'regulator_ignore_unused')
sha = lambda b: hashlib.sha256(b).hexdigest()
align = lambda n, a: (n+a-1)//a*a

def sections(b):
    out, off = [], 0
    while off < len(b):
        if all(c in (0,255) for c in b[off:]):
            break
        assert off+4 <= len(b)
        size = int.from_bytes(b[off:off+3], 'little')
        typ, hl = b[off+3], 4
        if size == 0xffffff:
            size, hl = struct.unpack_from('<I', b, off+4)[0], 8
        assert hl <= size <= len(b)-off, (off, size, len(b))
        out.append((typ, b[off+hl:off+size], b[off:off+size]))
        off = align(off+size, 4)
    return out

def fv(b):
    assert b[40:44] == b'_FVH'
    length = struct.unpack_from('<Q', b, 32)[0]
    hl = struct.unpack_from('<H', b, 48)[0]
    assert length == len(b)
    assert sum(struct.unpack('<'+'H'*(hl//2), b[:hl])) % 65536 == 0
    result, off = {}, align(hl, 8)
    while off+24 <= len(b):
        if b[off:off+24] == b'\xff'*24:
            assert b[off:] == b'\xff'*(len(b)-off)
            break
        head = bytearray(b[off:off+24])
        typ, attrs = head[18], head[19]
        size, hs = int.from_bytes(head[20:23], 'little'), 24
        if attrs & 1:
            assert size == 0xffffff
            size, hs = struct.unpack_from('<Q', b, off+24)[0], 32
            head = bytearray(b[off:off+hs])
        assert hs <= size <= len(b)-off, (off, size)
        head[17] = head[23] = 0
        assert sum(head) % 256 == 0, ('header checksum', off)
        body = b[off+hs:off+size]
        if attrs & 0x40:
            assert (sum(body)+b[off+17]) % 256 == 0
        else:
            assert b[off+17] == 0xaa
        if typ != 0xf0:
            guid = str(uuid.UUID(bytes_le=b[off:off+16]))
            assert guid not in result
            secs = sections(body) if typ != 1 else []
            ui = [s[1].decode('utf-16-le').rstrip('\0') for s in secs if s[0] == 0x15]
            result[guid] = dict(type=typ, attrs=attrs, body=body, sections=secs,
                                name=ui[0] if ui else '', size=size)
        off = align(off+size, 8)
    return result

def fdt_nodes(b):
    assert b[:4] == bytes.fromhex('d00dfeed')
    total, off, strings = struct.unpack_from('>III', b, 4)
    assert total == len(b)
    stack, result = [], {}
    while True:
        token = struct.unpack_from('>I', b, off)[0]
        off += 4
        if token == 1:
            end=b.index(0, off)
            stack.append(b[off:end].decode())
            off=align(end+1,4)
            path='/'.join(stack) or '/'
            assert path not in result
            result[path]={}
        elif token == 2:
            stack.pop()
        elif token == 3:
            size, nameoff = struct.unpack_from('>II', b, off)
            off += 8
            end=b.index(0,strings+nameoff)
            name=b[strings+nameoff:end].decode()
            path='/'.join(stack) or '/'
            assert name not in result[path]
            result[path][name]=b[off:off+size]
            off=align(off+size,4)
        elif token == 4:
            pass
        elif token == 9:
            assert not stack
            return result
        else:
            raise AssertionError(token)


dt_audit=json.loads((root/'dtb-validation.json').read_text())

data = {}
for tag in ('before', 'after'):
    boot = (root / ('boot-before.img' if tag=='before' else 'boot-k79-bus.img')).read_bytes()
    fd = (root / ('firmware-'+tag+'.fd')).read_bytes()
    main = (root / ('fvmain-'+tag+'.Fv')).read_bytes()
    compact = (root / ('fvcompact-'+tag+'.Fv')).read_bytes()
    dtb = (root / ('firmware-'+tag+'.dtb')).read_bytes()
    compat = (root / 'compat-before.dtb').read_bytes()
    assert boot[:8] == b'ANDROID!'
    ks, rs, ss, pg, ver = [struct.unpack_from('<I', boot, o)[0] for o in (8,16,24,36,40)]
    assert ver == 1 and pg == 2048 and rs == 1 and ss == 0
    assert len(boot) == pg+align(ks, pg)+align(rs, pg)
    payload = boot[pg:pg+ks]
    d = zlib.decompressobj(31)
    raw = d.decompress(payload)+d.flush()
    assert d.eof and not d.unconsumed_tail and d.unused_data == compat
    assert raw[144:] == fd and raw[:144][:4] != b'\xd0\x0d\xfe\xed'
    assert fd == compact and len(fd) == 0x700000
    modules = fv(main)
    compact_modules = fv(compact)
    dt_sections = modules[dt_guid]['sections']
    assert len(dt_sections)==1 and dt_sections[0][0]==0x19 and dt_sections[0][1]==dtb
    images = [m for m in compact_modules.values() if m['type'] == 0xb]
    assert len(images)==1 and len(images[0]['sections'])==1
    typ, body, sec = images[0]['sections'][0]
    assert typ == 2 and str(uuid.UUID(bytes_le=body[:16])) == lz_guid
    offset, attrs = struct.unpack_from('<HH', body, 16)
    decoded = lzma.decompress(sec[offset:], format=lzma.FORMAT_ALONE)
    nested = sections(decoded)
    assert len(nested)==1 and nested[0][0]==0x17 and nested[0][1]==main
    assert cmd.encode('utf-16-le') in main
    assert 'Linux (mainline samurai)'.encode('utf-16-le') in main
    data[tag] = dict(boot=boot, shim=raw[:144], modules=modules, page=pg,
                     ramdisk=boot[pg+align(ks,pg):pg+align(ks,pg)+rs],
                     compact_modules=compact_modules, main=main)

old, new = data['before'], data['after']
assert old['shim'] == new['shim']
assert old['ramdisk'] == new['ramdisk']
oldheader, newheader = bytearray(old['boot'][:old['page']]), bytearray(new['boot'][:new['page']])
for h in (oldheader,newheader):
    h[8:12] = b'\0'*4
    h[576:608] = b'\0'*32
assert oldheader==newheader, 'Unexpected Android boot header change'
assert old['modules'].keys()==new['modules'].keys(), 'Module set changed'
changes=[]
version_before='136157b'
version_after='3dd07f4'
def version_only(m, n):
    oldver=version_before.encode('utf-16-le')+b'\0\0'
    newver=version_after.encode('utf-16-le')+b'\0\0'
    assert len(m)==len(n) and m.count(oldver)==1
    assert m.replace(oldver,newver)==n, 'Unexpected executable change beyond firmware version'

for guid, m in old['modules'].items():
    n = new['modules'][guid]
    assert (m['type'],m['attrs'])==(n['type'],n['attrs'])
    if m['body'] != n['body']:
        if guid != dt_guid:
            assert n['name'] in ('PlatformSmbiosDxe','BdsDxe','UiApp')
            version_only(m['body'],n['body'])
        changes.append(dict(guid=guid,name=n['name'], before_size=m['size'],after_size=n['size'],
                            classification='i2c1_adapter_only' if guid==dt_guid else 'firmware_version_string_only',
                            before_sha256=sha(m['body']),after_sha256=sha(n['body']),
                            changed_sections=[hex(a[0]) for a,b in zip(m['sections'],n['sections']) if a[2]!=b[2]]))
compact_changes=[]
assert old['compact_modules'].keys()==new['compact_modules'].keys()
for guid, m in old['compact_modules'].items():
    n = new['compact_modules'][guid]
    if m['body'] != n['body']:
        if m['type'] != 0xb:
            assert m['type']==3
            version_only(m['body'],n['body'])
        compact_changes.append(dict(guid=guid,name=n['name'],type=hex(m['type'])))
report=dict(boot_gzip_crc_pass=True, old_boot_matches_backed_up_fv=True,
            embedded_fd_matches=True, fd_bytes=0x700000, bootshim_bytes=144, bootshim_sha256=sha(old['shim']),
            compact_lzma_matches_main_fv=True, firmware_dtb_raw_section_matches=True,
            ffs_header_checksums_pass=True, fv_header_checksums_pass=True,
            android_header_unchanged_except_size_and_digest=True,
            compat_append_unchanged=True, cmdline_preserved=cmd, module_count=len(new['modules']),
            semantic_dtb_changes=dt_audit, firmware_version_before=version_before,
            firmware_version_after=version_after, other_executable_bytes_unchanged=True,
            changed_modules=changes, changed_compact_modules=compact_changes,
            boot_after_bytes=len(new['boot']),boot_after_sha256=sha(new['boot']))
(root/'firmware-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
