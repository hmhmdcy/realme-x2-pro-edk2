from pathlib import Path
import hashlib, json, struct, tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel92')
report=[]
with tarfile.open(out/'bluetooth-firmware.tar') as source:
    for m in source:
        if not m.isfile() or 'btfw' not in m.name: continue
        data=source.extractfile(m).read()
        type_len=struct.unpack_from('<I',data)[0]
        fields=struct.unpack_from('<IIBBBBHHHHI',data,4)
        report.append(dict(name=m.name,size=len(data),sha256=hashlib.sha256(data).hexdigest(),
            type=type_len&255,tlv_len=type_len>>8,total_size=fields[0],data_length=fields[1],
            format=fields[2],signature=fields[3],download_mode=fields[4],product_id=fields[6],
            rom_build=hex(fields[7]),patch_version=hex(fields[8])))
(out/'bluetooth-headers.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
