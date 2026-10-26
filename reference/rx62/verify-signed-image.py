"""Verify this produced PE image digest and unchanged code, without trusting a root."""
from pathlib import Path
import hashlib
import json
import struct

base = Path('/mnt/e/edk2-samurai-out/rx62')
dest = base / 'signed-image-audit.json'
assert not dest.exists(), 'Preserve the prior audit'
original = (base / 'package-windows11/qcwdfserial.sys').read_bytes()
signed = (base / 'package-test-signed/qcwdfserial.sys').read_bytes()
assert hashlib.sha256(original).hexdigest() == '3cceeafcb3c5656e87de130d938f748cdc3875e826c63f9826440b56674b4a2a'
pe = struct.unpack_from('<I', signed, 0x3c)[0]
optional = pe + 24
assert signed[pe:pe+4] == b'PE\0\0'
assert struct.unpack_from('<H', signed, optional)[0] == 0x20b
checksum = optional + 64
security = optional + 112 + 4 * 8
certificate_offset, certificate_size = struct.unpack_from('<II', signed, security)
assert certificate_offset == len(original)
assert certificate_offset + certificate_size == len(signed)
allowed = set(range(checksum, checksum + 4)) | set(range(security, security + 8))
changed = [i for i, pair in enumerate(zip(original, signed)) if pair[0] != pair[1]]
assert changed and set(changed) <= allowed, 'Signing altered other original bytes'

headers = struct.unpack_from('<I', signed, optional + 60)[0]
optional_size = struct.unpack_from('<H', signed, pe + 20)[0]
sections_count = struct.unpack_from('<H', signed, pe + 6)[0]
section_table = optional + optional_size
sections = []
for i in range(sections_count):
    row = section_table + i * 40
    size, offset = struct.unpack_from('<II', signed, row + 16)
    if size:
        sections.append((offset, size))
sections.sort()
# This exact linked image has contiguous section raw data and no overlay.
cursor = headers
for offset, size in sections:
    assert offset == cursor, 'Unexpected raw section gap/overlap'
    cursor += size
assert cursor == certificate_offset
digest = hashlib.sha256()
for start, end in [(0, checksum), (checksum + 4, security), (security + 8, headers)]:
    digest.update(signed[start:end])
for offset, size in sections:
    digest.update(signed[offset:offset+size])

def tlv(data, offset=0):
    start = offset
    tag = data[offset]
    length = data[offset + 1]
    offset += 2
    if length & 128:
        count = length & 127
        assert count and count <= 4
        length = int.from_bytes(data[offset:offset+count], 'big')
        offset += count
    end = offset + length
    assert end <= len(data)
    return tag, data[offset:end], end, start

def children(data):
    result = []
    cursor = 0
    while cursor < len(data):
        tag, value, cursor, _ = tlv(data, cursor)
        result.append((tag, value))
    assert cursor == len(data)
    return result

content = (base / 'qcwdfserial.sys.cms-content.bin').read_bytes()
root_tag, root_value, end, _ = tlv(content)
assert root_tag == 0x30 and end == len(content)
indirect = children(root_value)
assert len(indirect) == 2 and indirect[1][0] == 0x30
digest_info = children(indirect[1][1])
assert digest_info[0][0] == 0x30 and digest_info[1][0] == 0x04
algorithm = children(digest_info[0][1])
assert algorithm[0] == (0x06, bytes.fromhex('608648016503040201')), 'Expected SHA256 OID'
assert digest.digest() == digest_info[1][1], 'Signed digest does not match file image'
for name in ('qceudexp.inf', 'QUALCOMM-LICENSE.txt'):
    assert (base / 'package-windows11' / name).read_bytes() == (base / 'package-test-signed' / name).read_bytes()
signing = json.loads((base / 'offline-signing.json').read_text())
assert all(x['signature_only_valid'] for x in signing['cms_signature_checks'])
report = {
    'unsigned_sys_sha256': hashlib.sha256(original).hexdigest(),
    'test_signed_sys_sha256': hashlib.sha256(signed).hexdigest(),
    'authenticode_sha256': digest.hexdigest(),
    'signed_digest_matches_image': True,
    'all_original_bytes_unchanged_except_pe_checksum_and_security_directory': True,
    'changed_original_offsets': changed,
    'allowed_original_ranges': [[checksum, checksum + 4], [security, security + 8]],
    'certificate_table_offset': certificate_offset,
    'certificate_table_bytes': certificate_size,
    'inf_and_license_unchanged': True,
    'cms_signature_only_valid': True,
    'kernel_loading_trust_proved': False,
    'hardware_validated': False,
    'limits': 'Verifies this exact image and CMS signature, not trust policy, catalog installation, HVCI runtime or USB stability.',
}
dest.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
