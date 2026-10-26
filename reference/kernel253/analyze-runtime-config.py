#!/usr/bin/env python3
"""Decode bounded live configuration copies using the matching ELF tables.

Reads saved local evidence only. Does not connect to or modify a process.
String values (server names etc.) are withheld from the output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from elfview_relr import RelrElf


def analyze(core_path, core_memory, api_path, rf_memory):
    core, api = RelrElf(core_path), RelrElf(api_path)
    config = next(s for s in core.syms if s['demangled'] == 'loc_core::ContextBase::mGps_conf' and s['shndx'])
    table = next(s for s in core.syms if s['demangled'] == 'loc_core::ContextBase::mGps_conf_table' and s['shndx'])
    data = core_memory.read_bytes()
    if len(data) != config['size'] or table['size'] % 32:
        raise ValueError('Configuration object/table size mismatch')
    values, strings = {}, []
    for offset in range(0, table['size'], 32):
        entry = table['value'] + offset
        name = core.read(core.pointer(entry)['value'], 120).split(b'\0', 1)[0].decode()
        target = core.pointer(entry + 8)['value'] - config['value']
        kind = chr(core.read(entry + 24, 1)[0])
        if not 0 <= target < len(data):
            raise ValueError('Config pointer outside saved object')
        if kind == 'n':
            values[name] = struct.unpack_from('<I', data, target)[0]
        elif kind == 'f':
            values[name] = struct.unpack_from('<f', data, target)[0]
        elif kind == 's':
            strings.append(name)
        else:
            raise ValueError('Unknown config type')
    rf = []
    for address in api.relocs:
        pointer = api.pointer(address)
        if pointer['external']:
            continue
        try:
            if api.read(pointer['value'], 8) != b'RF_LOSS_':
                continue
            name = api.read(pointer['value'], 80).split(b'\0', 1)[0].decode()
            if api.read(address + 24, 1) == b'n':
                rf.append((name, api.pointer(address + 8)['value']))
        except (ValueError, UnicodeDecodeError, AssertionError):
            continue
    if len(rf) != 10:
        raise ValueError('Matching RF loss table was not found')
    start = min(address for _, address in rf)
    raw = rf_memory.read_bytes()
    if max(address for _, address in rf) + 4 - start != len(raw) or len(raw) != 40:
        raise ValueError('RF loss object size mismatch')
    values.update({name: struct.unpack_from('<I', raw, address - start)[0] for name, address in rf})
    return dict(object_bytes=len(data), table_fields=table['size'] // 32,
        rf_loss_fields=len(rf), numeric_values=values, string_values_withheld=strings,
        elf_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [core_path, api_path]},
        relr_entries=dict(core=core.relr_count, loc_api=api.relr_count),
        rf_loss_values_are_software_configuration_not_lna_voltage=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('core_elf', type=Path)
    parser.add_argument('private_core_memory', type=Path)
    parser.add_argument('loc_api_elf', type=Path)
    parser.add_argument('private_rf_loss_memory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.core_elf, args.private_core_memory, args.loc_api_elf, args.private_rf_loss_memory)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(object_bytes=result['object_bytes'], table_fields=result['table_fields'],
                         rf_loss_fields=result['rf_loss_fields'], relr_entries=result['relr_entries'])))


if __name__ == '__main__':
    main()
