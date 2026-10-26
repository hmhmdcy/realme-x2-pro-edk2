"""Read-only stock blob/layout validation; never extracts or publishes firmware."""
from pathlib import Path
import hashlib
import json
import struct
import tarfile

root = Path(__file__).resolve().parent
manifest = json.loads((root.parent/'kernel73/gpu-firmware-manifest.json').read_text())
archive = Path('/mnt/e/edk2-samurai-out/kernel73/gpu-firmware-stock.tar')
sha = lambda data: hashlib.sha256(data).hexdigest()
assert sha(archive.read_bytes()) == manifest['archive_sha256']
files = {}
with tarfile.open(archive) as tar:
    assert {m.name for m in tar.getmembers()} == set(manifest['files'])
    for name, record in manifest['files'].items():
        member = tar.getmember(name)
        assert member.isfile()
        raw = tar.extractfile(member).read()
        assert len(raw) == record['bytes'] and sha(raw) == record['sha256'], name
        files[name] = raw
elf = files['a640_zap.elf']
assert elf[:6] == b'\x7fELF\x01\x01'
header = struct.unpack_from('<16sHHIIIIIHHHHHH',elf)
assert header[2]==164 and header[9]==32 and header[10]==3
headers = [struct.unpack_from('<IIIIIIII',elf,header[5]+i*header[9]) for i in range(header[10])]
assert files['a640_zap.b00'] == elf[:148]
assert files['a640_zap.b01'] == elf[4096:4096+6712]
assert files['a640_zap.b02'] == elf[12288:12288+1968]
assert files['a640_zap.mdt'] == files['a640_zap.b00']+files['a640_zap.b01']
hash_headers = [p for p in headers if (p[6] & (7<<24)) == (2<<24)]
loads = [p for p in headers if p[0]==1 and p[5] and (p[6] & (7<<24)) != (2<<24)]
assert len(hash_headers)==1 and len(loads)==1
for p in loads:
    assert p[4]<=p[5] and p[1]+p[4]<=len(elf)
    assert p[6] & (1<<27)
minimum = min(p[3] for p in loads)
maximum = max((p[3]+p[5]+4095)&~4095 for p in loads)
assert minimum==0x5000 and maximum==0x6000
assert maximum-minimum<=0x2000
result = dict(archive_sha256=manifest['archive_sha256'],all_seven_blob_hashes_match=True,
    elf_split_segments_match=True,packed_mdt_matches_full_elf_metadata=True,
    full_elf_non_split_load_pass=True,relocatable=True,load_min=hex(minimum),
    load_max_4k=hex(maximum),required_bytes=maximum-minimum,
    handset_carveout_base='0x99515000',handset_carveout_bytes=8192,
    footprint_fits=True,firmware_installed=False,gpu_enabled=False,
    secure_world_authentication_verified=False,gmu_boot_verified=False,render_verified=False,
    interpretation='Layout is compatible with the inspected mainline MDT loader; PAS acceptance needs a handset test.')
(root/'gpu-loader-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
