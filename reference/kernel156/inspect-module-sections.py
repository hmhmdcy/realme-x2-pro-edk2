from pathlib import Path
import hashlib,json,struct,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel156')
mod=Path('/home/cy122/pmos-samurai-kernel136/modules-root156')
diff=json.loads((out/'module-difference-private.json').read_text())
def sections(data):
    assert data[:6]==b'\x7fELF\x02\x01'
    off=struct.unpack_from('<Q',data,40)[0]
    size,count,index=struct.unpack_from('<HHH',data,58)
    headers=[struct.unpack_from('<IIQQQQIIQQ',data,off+i*size) for i in range(count)]
    strings=data[headers[index][4]:headers[index][4]+headers[index][5]]
    return {strings[h[0]:].split(b'\x00',1)[0].decode():data[h[4]:h[4]+h[5]]
        for h in headers if h[1]!=8}
rows=[]
with tarfile.open(out.parent/'kernel132/modules-k132-private.tar.gz') as tar:
    for name in diff['unexplained_modules']:
        a=tar.extractfile(name).read();b=(mod/name).read_bytes()
        sa,sb=sections(a),sections(b)
        changes=[n for n in set(sa)|set(sb) if sa.get(n)!=sb.get(n)]
        row=dict(module=name,changed_sections=sorted(changes),
            text_equal=sa.get('.text')==sb.get('.text'),rodata_equal=sa.get('.rodata')==sb.get('.rodata'),
            modinfo_before=sa.get('.modinfo',b'').replace(b'\x00',b'\n').decode(),
            modinfo_after=sb.get('.modinfo',b'').replace(b'\x00',b'\n').decode())
        rows.append(row)
(out/'module-sections-private.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
