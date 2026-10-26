#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import tarfile

out = Path('/mnt/e/edk2-samurai-out')
def read(name, prefix):
    with tarfile.open(out / name) as tar:
        data = {m.name.removeprefix(prefix): tar.extractfile(m).read()
                for m in tar if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest, path = line.split('  ', 1)
        assert hashlib.sha256(data[path.removeprefix('./')]).hexdigest() == digest
    return data
before = read('kernel111/layout-before.tar', 'k109-layout-before-sensors111/')
after = read('kernel112/layout-after.tar', './')
for dev in ('sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf'):
    for part in ('head', 'tail', 'geometry'):
        assert before[f'{dev}.{part}'] == after[f'{dev}.{part}'], (dev, part)
assert after['nv-check.txt'].decode().count(': OK') == 6
assert after['source-check.txt'].decode().count(': OK') == 4
hashes = dict(line.split('  ')[::-1] for line in after['partition-check.sha256'].decode().splitlines())
assert hashes['/dev/sde11'] == hashlib.sha256((out / 'kernel111/boot-partition-k111.img').read_bytes()).hexdigest()
assert hashes['/dev/sde32'] == hashlib.sha256((out / 'kernel112/logdump-k112-startup.img').read_bytes()).hexdigest()
assert hashes['/dev/sda2'] == '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
report = dict(all_six_lun_geometry_and_gpt_bytes_equal=True,
              compared_parts=18, boot_matches_111=True, logdump_matches_112=True,
              persist_unchanged=True, nv_6_unchanged=True, stock_sources_4_unchanged=True)
(out / 'kernel112/layout-after-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS: six-LUN GPT and geometry unchanged; boot/logdump exact; persist/NV/source hashes unchanged')
