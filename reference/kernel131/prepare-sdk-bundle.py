#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import tarfile

private = Path('/mnt/e/edk2-samurai-out/kernel131/native-sdk')
receipts = json.loads((private / 'sdk-download-receipts.json').read_text(encoding='utf-8-sig'))
with tarfile.open(private / 'native-sdk-inputs.tar', 'w') as out:
    for receipt in receipts:
        path = private / receipt['Package']
        assert path.stat().st_size == receipt['Bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt['SHA256']
        out.add(path, arcname=path.name)
    out.add(private / 'glmark2-2023.01.tar.gz', arcname='glmark2-2023.01.tar.gz')
bundle = private / 'native-sdk-inputs.tar'
(private / 'native-sdk-inputs.tar.sha256').write_text(hashlib.sha256(bundle.read_bytes()).hexdigest() + '  native-sdk-inputs.tar\n')
with tarfile.open(private / 'glmark2-2023.01.tar.gz') as src:
    for name in ['src/main.cpp', 'src/gl-state-egl.cpp', 'src/canvas-generic.h']:
        body = src.extractfile('glmark2-2023.01/' + name).read().decode()
        if name.endswith('main.cpp'):
            print('\n'.join(line for line in body.splitlines() if 'GLMARK' in line or 'config' in line))
    print('source_members', len(src.getmembers()))
print('sdk_inputs_bytes', bundle.stat().st_size)
