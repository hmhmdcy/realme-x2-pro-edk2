"""Offline helpers for the fixed k363 payload; no phone or SDK access."""
from pathlib import Path
import hashlib
import json
import re
import struct
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_lock():
    return json.loads((HERE / 'source-lock.json').read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def elf_sections(data):
    require(data[:6] == b'\x7fELF\x02\x01', 'Expected little-endian ELF64')
    require(struct.unpack_from('<H', data, 18)[0] == 183, 'Expected AArch64 ELF')
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    require(size == 64 and index < count and offset + count * size <= len(data), 'Invalid ELF section table')
    rows = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    strings = data[rows[index][4]:rows[index][4] + rows[index][5]]
    result = {}
    for row in rows:
        name = strings[row[0]:].split(b'\0', 1)[0].decode('ascii')
        if row[1] != 8:  # SHT_NOBITS has no data in the file.
            require(row[4] + row[5] <= len(data), 'Invalid ELF section extent')
            result[name] = data[row[4]:row[4] + row[5]]
    return result


def validate_module(data, record, lock):
    require(len(data) == record['bytes'] and sha(data) == record['sha256'], 'Module payload hash mismatch: ' + record['name'])
    sections = elf_sections(data)
    fields = {}
    for item in sections['.modinfo'].split(b'\0'):
        if b'=' in item:
            key, value = item.split(b'=', 1)
            fields.setdefault(key.decode(), []).append(value.decode())
    require(fields.get('vermagic') == [lock['vermagic']], 'Wrong kernel ABI: ' + record['name'])
    require(fields.get('name') == [record['name']], 'Wrong module name')
    deps = fields.get('depends', [''])[0].split(',')
    require(sorted(filter(None, deps)) == sorted(record['depends']), 'Wrong module dependencies')
    require('.note.gnu.build-id' in sections, 'Missing module build-id')
    return dict(name=record['name'], sha256=sha(data), vermagic=fields['vermagic'][0],
                dependencies=record['depends'], build_id_note_sha256=sha(sections['.note.gnu.build-id']))


def load_modules(archive, lock):
    result = {}
    with tarfile.open(archive) as handle:
        for record in lock['modules']:
            matches = [m for m in handle.getmembers() if m.name.removeprefix('./') == record['target']]
            require(len(matches) == 1 and matches[0].isfile(), 'Missing, duplicate or nonregular module: ' + record['name'])
            require(matches[0].size == record['bytes'], 'Unexpected module size')
            data = handle.extractfile(matches[0]).read()
            validate_module(data, record, lock)
            result[record['name']] = data
    return result


def audit_sources(lock):
    result = []
    for record in lock['files']:
        path = REPO / record['source']
        data = path.read_bytes()
        require(len(data) == record['bytes'] and sha(data) == record['sha256'], 'Source differs from lock: ' + record['source'])
        recipe = path.parent / 'APKBUILD'
        checksums = re.findall(r'^([a-f0-9]{128})  (.+)$', recipe.read_text(), re.M)
        entries = [digest for digest, name in checksums if name == path.name]
        require(entries == [hashlib.sha512(data).hexdigest()], 'Missing, duplicate or stale recipe checksum: ' + path.name)
        target = '$pkgdir"/' + record['target']
        require(target in recipe.read_text(), 'Recipe installation path missing: ' + record['target'])
        result.append(dict(source=record['source'], target=record['target'], sha256=sha(data), recipe_checksum_verified=True))
    repair = lock['historical_repair']
    require(sha((REPO / repair['patch']).read_bytes()) == repair['patch_sha256'], '185 patch changed')
    provenance = json.loads((HERE / 'current-source-validation.json').read_text())
    require(provenance['commit'] == lock['kernel_commit'] and provenance['hci_qca_exact185'], 'Current source provenance mismatch')
    for name, digest in provenance['source_sha256'].items():
        require(sha((HERE / 'rebuild-sources' / Path(name).name).read_bytes()) == digest, 'Archived source object changed: ' + name)
    require(provenance['source_sha256']['drivers/bluetooth/hci_qca.c'] == repair['source_after_sha256'], 'Current source does not retain185 repair')
    return result
