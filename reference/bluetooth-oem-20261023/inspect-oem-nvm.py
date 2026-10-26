"""Read the existing private OEM archive; emit only transport tags 17 and 27."""
from pathlib import Path
import hashlib
import json
import struct
import tarfile

archive = Path('/mnt/e/edk2-samurai-out/kernel92/bluetooth-firmware.tar')
expected_sha = '148255b19bce3b7a048da461279dff908f97365140bd93c18cec32691cf0057c'
with tarfile.open(archive) as tar:
    matches = [m for m in tar.getmembers() if m.name.endswith('/crnv21.bin')]
    assert len(matches) == 1
    data = tar.extractfile(matches[0]).read()
assert hashlib.sha256(data).hexdigest() == expected_sha
assert len(data) == 4710 and data[0] == 4
assert int.from_bytes(data[1:4], 'little') == len(data) - 4

pos = 4
blocks = []
while pos < len(data):
    assert pos + 4 <= len(data)
    typ = data[pos]
    size = int.from_bytes(data[pos + 1:pos + 4], 'little')
    cursor = pos + 4
    end = cursor + size
    assert end <= len(data)
    tags = []
    while cursor < end:
        assert cursor + 12 <= end
        tag_id, length, _, _ = struct.unpack_from('<HHII', data, cursor)
        cursor += 12
        assert cursor + length <= end
        value = data[cursor:cursor + length]
        tags.append(dict(id=tag_id, len=length,
                         data=value.hex() if typ == 2 and tag_id in (17, 27) else '<omitted>'))
        cursor += length
    assert cursor == end
    blocks.append(dict(type=typ, length=size, tags=tags))
    pos = end

report = dict(source='same-handset saved kernel92 Bluetooth firmware export',
              file='crnv21.bin', sha256=expected_sha, size=len(data), outer_type=4,
              blocks=blocks, private_address_and_nontransport_tags_omitted=True)
target = Path(__file__).parent / 'nvm-summary.json'
target.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(block_types=[b['type'] for b in blocks],
                      block_lengths=[b['length'] for b in blocks],
                      bt_tag44_present=any(t['id'] == 44 for t in blocks[0]['tags']),
                      private_payloads_omitted=True)))
