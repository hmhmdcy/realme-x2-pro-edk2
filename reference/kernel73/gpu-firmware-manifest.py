"""Archive only identities/ELF geometry of device-local firmware, never blobs."""
from pathlib import Path
import hashlib
import json
import struct
import tarfile

source = Path('/mnt/e/edk2-samurai-out/kernel73/gpu-firmware-stock.tar')
sha = lambda data: hashlib.sha256(data).hexdigest()
files = {}
with tarfile.open(source) as archive:
    for member in archive.getmembers():
        if not member.isfile():
            continue
        raw = archive.extractfile(member).read()
        entry = dict(bytes=len(raw),sha256=sha(raw))
        if raw[:5]==b'\x7fELF\x01' and raw[5]==1:
            header = struct.unpack_from('<16sHHIIIIIHHHHHH',raw)
            phoff,phentsize,phnum=header[5],header[9],header[10]
            assert phentsize==32
            entry['elf32'] = dict(machine=header[2],entry=hex(header[4]),program_headers=[
                dict(zip(('type','offset','vaddr','paddr','filesz','memsz','flags','align'),
                         struct.unpack_from('<8I',raw,phoff+i*phentsize))) for i in range(phnum)])
        files[member.name]=entry
result = dict(archive_sha256=sha(source.read_bytes()),
    source='handset PARTNAME=vendor, ext4 mounted ro,noload then unmounted',
    blobs_location=str(source),blobs_published=False,gpu_enabled=False,files=files)
Path(__file__).with_name('gpu-firmware-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
