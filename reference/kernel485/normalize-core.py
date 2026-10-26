"""Apply Meson's install-time RPATH removal to a verified, new ELF copy.

For the fixed libcamera build inputs validated in this series, not arbitrary ELF.
No source, original artifact, IPA module, signature, or installed file is changed.
Run with the host Python which provides mesonbuild; no SDK is required.
"""
from pathlib import Path
import argparse
import hashlib
import shutil
import struct


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def elf(path):
    raw = Path(path).read_bytes()
    assert raw[:6] == b'\x7fELF\x02\x01', 'Expected little-endian ELF64'
    machine = struct.unpack_from('<H', raw, 18)[0]
    offset = struct.unpack_from('<Q', raw, 40)[0]
    stride, count, names_index = struct.unpack_from('<HHH', raw, 58)
    assert stride == 64 and count and names_index < count
    headers = [struct.unpack_from('<IIQQQQIIQQ', raw, offset + i * stride)
               for i in range(count)]
    names_header = headers[names_index]
    names = raw[names_header[4]:names_header[4] + names_header[5]]
    sections = {}
    for header in headers:
        name = names[header[0]:].split(b'\0', 1)[0].decode()
        assert name not in sections
        sections[name] = header
    dynamic = sections['.dynamic']
    entries = []
    for at in range(dynamic[4], dynamic[4] + dynamic[5], 16):
        tag, value = struct.unpack_from('<qQ', raw, at)
        if tag == 0:
            break
        entries.append((tag, value))
    strings = sections['.dynstr']
    paths = []
    for tag, value in entries:
        if tag in (15, 29):
            start = strings[4] + value
            end = raw.index(0, start, strings[4] + strings[5])
            paths.append((tag, value, start, end, raw[start:end]))
    return raw, machine, sections, entries, paths


def normalize(source, destination, expected_sha, expected_rpath, machine=183):
    from mesonbuild.scripts import depfixer

    source, destination = Path(source), Path(destination)
    assert source.is_file() and not source.is_symlink()
    assert source.resolve() != destination.resolve()
    assert not destination.exists() and not destination.is_symlink()
    assert destination.parent.is_dir()
    assert sha256(source) == expected_sha, 'Unverified input bytes'
    before, actual_machine, sections, entries, paths = elf(source)
    assert actual_machine == machine
    assert len(paths) == 1 and paths[0][-1] == expected_rpath
    tag, value, start, end, old_path = paths[0]

    # These known inputs have no symbol or loader string which reuses a suffix
    # of their build path. Require that fact before accepting Meson's X fill.
    for other_tag, other_value in entries:
        if other_tag in (1, 14, 0x7ffffffd, 0x7fffffff):
            assert not value <= other_value < value + len(old_path)
    dynsym = sections['.dynsym']
    assert dynsym[9] == 24
    for at in range(dynsym[4], dynsym[4] + dynsym[5], dynsym[9]):
        name_offset = struct.unpack_from('<I', before, at)[0]
        assert not value <= name_offset < value + len(old_path)

    shutil.copy2(source, destination)
    depfixer.fix_rpath(str(destination), set(old_path.split(b':')), b'',
                      str(destination), {}, verbose=False)
    after, after_machine, after_sections, after_entries, after_paths = elf(destination)
    assert actual_machine == after_machine and sections == after_sections
    assert not after_paths
    assert after_entries == [(t, v) for t, v in entries if t not in (15, 29)]

    # Every other byte (including headers, code, data, key, symbols and debug
    # sections) must match. Only .dynamic and exactly the old path string differ.
    dynamic = sections['.dynamic']
    expected = bytearray(before)
    expected[start:end] = b'X' * (end - start)
    expected[dynamic[4]:dynamic[4] + dynamic[5]] = after[dynamic[4]:dynamic[4] + dynamic[5]]
    assert bytes(expected) == after, 'Change beyond install-time path removal'
    assert after[start:end] == b'X' * (end - start)
    assert sha256(source) == expected_sha, 'Original changed'
    return {
        'input_sha256': expected_sha,
        'output_sha256': sha256(destination),
        'size': len(after),
        'machine': machine,
        'removed_dynamic_tag': tag,
        'removed_build_rpath': old_path.decode(),
        'all_other_dynamic_entries_identical': True,
        'all_bytes_outside_dynamic_and_old_path_identical': True,
        'original_unchanged': True,
        'normalizer': 'mesonbuild.scripts.depfixer.fix_rpath',
        'meson_depfixer_sha256': sha256(depfixer.__file__),
    }


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(normalize(args.source, args.destination, args.expected_sha256,
                               b'$ORIGIN/base:/'), indent=2))
