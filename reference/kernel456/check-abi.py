"""Actual ELF exports, DWARF layouts, 455 imports and new Image identity."""
from pathlib import Path
import argparse
import gzip
import hashlib
import importlib.util
import json
import re
import struct
import subprocess
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('preflight456', HERE/'preflight.py')
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
SHARED = pre.storage.mount.mounted_build()
PRIVATE = pre.PRIVATE
DATA = json.loads((PRIVATE/'preflight-private.json').read_text())
TYPES = ['v4l2_subdev', 'v4l2_subdev_internal_ops', 'v4l2_device', 'video_device', 'v4l2_subdev_fh',
         'v4l2_ctrl_handler', 'device', 'dev_pm_info', 'regulator', 'module', 'kref', 'mutex',
         'list_head', 'i2c_client', 'media_entity']


def symvers(path):
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        assert len(fields) in [4, 5]
        crc, symbol, module, kind = fields[:4]
        namespace = fields[4] if len(fields) == 5 else ''
        assert symbol not in result
        result[symbol] = dict(crc=crc, module=module, export=kind, namespace=namespace)
    return result


def identity(elf):
    notes = pre.run(['aarch64-linux-gnu-readelf', '-n', elf])
    match = re.search(r'Build ID: ([0-9a-f]+)', notes)
    assert match
    return match[1]


def elf_exports(elf):
    text = pre.run(['aarch64-linux-gnu-nm', '--defined-only', elf])
    exports = {line.split()[-1][len('__ksymtab_'):] for line in text.splitlines()
               if line.split() and line.split()[-1].startswith('__ksymtab_')}
    assert exports
    return exports, text


def embedded_initramfs(elf, nm, dump=None):
    symbols = {line.split()[-1]: int(line.split()[0], 16) for line in nm.splitlines()
               if line.split() and line.split()[-1] in ['__initramfs_start', '__initramfs_size']}
    assert set(symbols) == {'__initramfs_start', '__initramfs_size'}
    with elf.open('rb') as handle:
        header = handle.read(64)
        assert header[:6] == b'\x7fELF\x02\x01'
        offset = struct.unpack_from('<Q', header, 40)[0]
        stride, count = struct.unpack_from('<HH', header, 58)
        sections = []
        for index in range(count):
            handle.seek(offset+index*stride)
            sections.append(struct.unpack('<IIQQQQIIQQ', handle.read(64)))
        def file_offset(address):
            section = next(s for s in sections if s[3] <= address < s[3]+s[5] and s[1] != 8)
            return section[4]+address-section[3]
        handle.seek(file_offset(symbols['__initramfs_size']))
        size = struct.unpack('<Q', handle.read(8))[0]
        assert 0 < size < 64*1024**2
        handle.seek(file_offset(symbols['__initramfs_start']))
        blob = handle.read(size)
        assert len(blob) == size
    if dump is not None:
        Path(dump).write_bytes(blob)
    return dict(bytes=size, sha256=hashlib.sha256(blob).hexdigest())


def archive_comparison(original_path, candidate_path):
    normalized = []
    timestamps = []
    for path in [original_path, candidate_path]:
        raw = bytearray(gzip.decompress(path.read_bytes()))
        offset = 0
        times = []
        while raw[offset:offset+6] in [b'070701', b'070702']:
            values = [int(raw[offset+6+i*8:offset+14+i*8], 16) for i in range(13)]
            name = raw[offset+110:offset+110+values[11]-1]
            raw[offset+46:offset+54] = b'00000000'
            data_start = (offset+110+values[11]+3)&~3
            offset = (data_start+values[6]+3)&~3
            if name == b'TRAILER!!!':
                break
            times.append(values[5])
        assert len(times) == 396
        normalized.append(bytes(raw))
        timestamps.append(times)
    # Exact byte equality after replacing only each newc mtime field also proves
    # identical ordering, padding, names, data, modes, owners and device numbers.
    assert normalized[0] == normalized[1]
    return dict(entries=396, compressed_bytes_identical=original_path.read_bytes()==candidate_path.read_bytes(),
                archive_byte_identity=original_path.read_bytes()==candidate_path.read_bytes(),
                all_content_order_padding_and_non_time_metadata_identical=True,
                data_mode_uid_gid_nlink_dev_inode_content_identical=True, only_mtime_changed=True,
                changed_mtime_entries=sum(a != b for a, b in zip(*timestamps)),
                original_entry_mtimes=sorted(set(timestamps[0])), candidate_entry_mtimes=sorted(set(timestamps[1])),
                normalized_newc_sha256=hashlib.sha256(normalized[0]).hexdigest(),
                modification_is_build_archive_metadata_only=True)


def layouts(elf, label, names=None):
    names = TYPES if names is None else names
    output = PRIVATE/(label+'-layouts-private.json')
    commands = PRIVATE/(label+'-gdb-commands-private.txt')
    python = '''import gdb,json
names=NAMES
rows={}
for name in names:
 try:
  t=gdb.lookup_type('struct '+name).strip_typedefs()
  row={'size':int(t.sizeof),'alignment':int(t.alignof),'fields':[]}
  for field in t.fields():
   row['fields'].append({'name':field.name,'type':str(field.type),'bitpos':getattr(field,'bitpos',None),'bitsize':int(field.bitsize)})
  assert row['size']>0 and row['fields']
  rows[name]=row
 except Exception as error:
  rows[name]={'error':str(error)}
with open(OUTPUT,'w') as handle:json.dump(rows,handle,indent=2)
'''.replace('NAMES', repr(names)).replace('OUTPUT', repr(str(output)))
    commands.write_text('set auto-load off\nset pagination off\nfile '+str(elf)+'\npython\n'+python+'\nend\n')
    process = subprocess.run(['gdb-multiarch', '-nx', '-batch', '-x', str(commands)], capture_output=True, timeout=60)
    (PRIVATE/(label+'-gdb-private.log')).write_bytes(process.stdout+process.stderr)
    assert process.returncode == 0
    result = json.loads(output.read_text())
    assert set(result) == set(names)
    return result


def baseline():
    elf = SHARED/'vmlinux'
    assert pre.sha(elf) == DATA['original']['artifacts']['vmlinux']['sha256']
    exported, nm = elf_exports(elf)
    table = symvers(SHARED/'Module.symvers')
    builtin = {symbol: row for symbol, row in table.items() if row['module'] == 'vmlinux'}
    assert exported == set(builtin), (len(exported), len(builtin), sorted(exported-set(builtin))[:10])
    info = dict(build_id=identity(elf), exports=sorted(exported), symvers_builtin=builtin,
                layouts=layouts(elf, 'original363'), vmlinux_sha256=pre.sha(elf),
                embedded_initramfs=embedded_initramfs(elf, nm))
    (PRIVATE/'original363-abi-private.json').write_text(json.dumps(info, indent=2)+'\n')
    print(json.dumps(dict(original_build_id=info['build_id'], actual_builtin_exports=len(exported),
                          complete_dwarf_types=sum('error' not in row for row in info['layouts'].values()),
                          missing_reduced_dwarf_types=[name for name, row in info['layouts'].items() if 'error' in row],
                          baseline_only=True, passed=True)), flush=True)
    return info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-only', action='store_true')
    args = parser.parse_args()
    if args.baseline_only:
        baseline()
        return
    original_path = PRIVATE/'original363-abi-private.json'
    original = json.loads(original_path.read_text()) if original_path.exists() else baseline()
    assert original['vmlinux_sha256'] == pre.sha(SHARED/'vmlinux')
    built = json.loads((HERE/'build-validation.json').read_text())
    assert built['passed'] and built['image363_config_exact'] and built['embedded_config_matches_original']
    elf = PRIVATE/'vmlinux-k456-core0064-private'
    image = PRIVATE/'Image-k456-core0064-private'
    assert pre.sha(elf) == built['artifacts']['vmlinux']['sha256']
    assert pre.sha(image) == built['artifacts']['arch/arm64/boot/Image']['sha256']
    assert image.read_bytes()[56:60] == b'ARM\x64'
    exports, nm = elf_exports(elf)
    assert exports == set(original['exports'])
    if 'embedded_initramfs' not in original:
        old_exports, old_nm = elf_exports(SHARED/'vmlinux')
        original['embedded_initramfs'] = embedded_initramfs(SHARED/'vmlinux', old_nm)
    old_exports, old_nm = elf_exports(SHARED/'vmlinux')
    original_archive = PRIVATE/'original-embedded-initramfs-private.gz'
    candidate_archive = PRIVATE/'candidate-embedded-initramfs-private.gz'
    assert embedded_initramfs(SHARED/'vmlinux', old_nm, original_archive) == original['embedded_initramfs']
    initramfs = embedded_initramfs(elf, nm, candidate_archive)
    archive = archive_comparison(original_archive, candidate_archive)
    candidate_layouts = layouts(elf, 'candidate456')
    assert candidate_layouts == original['layouts'], [name for name in TYPES if candidate_layouts[name] != original['layouts'][name]]
    candidate_table = symvers(Path(json.loads((PRIVATE/'source-preparation-private.json').read_text())['output'])/'vmlinux.symvers')
    assert set(candidate_table) == exports
    assert candidate_table == original['symvers_builtin']
    module = PRIVATE.parent/'kernel455/bu64253-lifetime-r3-build1.ko'
    record455 = json.loads((HERE.parent/'kernel455/module-build-validation.json').read_text())
    assert pre.sha(module) == record455['module_sha256']
    imports = sorted({line.split()[-1] for line in pre.run(['aarch64-linux-gnu-nm', '-u', module]).splitlines() if line.strip()})
    assert len(imports) == record455['imported_symbols'] == 41
    assert set(imports) <= exports
    module_layouts = layouts(module, 'module455', TYPES+['bu64253'])
    module_compared = [name for name in TYPES if 'error' not in module_layouts[name] and 'error' not in candidate_layouts[name]]
    assert all(module_layouts[name] == candidate_layouts[name] for name in module_compared), [name for name in module_compared if module_layouts[name] != candidate_layouts[name]]
    assert 'error' not in module_layouts['bu64253']
    driver_fields = {field['name']: field for field in module_layouts['bu64253']['fields']}
    assert driver_fields['sd']['bitpos'] == 0
    assert driver_fields['ctrls']['bitpos']//8 == candidate_layouts['v4l2_subdev']['size']
    dependencies = json.loads((PRIVATE.parent/'kernel455/compiler-dependencies-private.json').read_text())
    source = Path(json.loads((PRIVATE/'source-preparation-private.json').read_text())['source'])
    source455 = SHARED.parent/'kernel455-lens-private/source-view'
    dependency_count = 0
    for relative in dependencies:
        if relative == 'drivers/media/i2c/bu64253.c':
            assert pre.sha(source455/relative) == record455['source_sha256']
            continue
        assert (source/relative).read_bytes() == (source455/relative).read_bytes(), relative
        dependency_count += 1
    assert dependency_count == 734
    # Keep original and candidate disassembly private; prove the changed object
    # was linked without putting raw address dumps in public reports.
    functions = [line.split()[-1] for line in nm.splitlines() if line.split() and
                 line.split()[-1] in ['v4l2_subdev_release', 'v4l2_device_release_subdev_node']]
    assert functions
    for label, binary in [('original363', SHARED/'vmlinux'), ('candidate456', elf)]:
        disassembly = b''
        for function in functions:
            disassembly += subprocess.check_output(['aarch64-linux-gnu-objdump', '-d', '--disassemble='+function, str(binary)])
        (PRIVATE/(label+'-release-disassembly-private.txt')).write_bytes(disassembly)
    original_disasm = (PRIVATE/'original363-release-disassembly-private.txt').read_bytes()
    candidate_disasm = (PRIVATE/'candidate456-release-disassembly-private.txt').read_bytes()
    assert original_disasm != candidate_disasm
    order = {}
    devnode_offset = next(field['bitpos']//8 for field in candidate_layouts['v4l2_subdev']['fields'] if field['name'] == 'devnode')
    for label, disassembly in [('original', original_disasm), ('candidate', candidate_disasm)]:
        lines = disassembly.decode().splitlines()
        stores = [i for i, line in enumerate(lines) if re.search(r'\bstr\s+xzr,\s*\[x\d+,\s*#'+str(devnode_offset)+r'\]', line)]
        calls = [i for i, line in enumerate(lines) if re.search(r'\bblr\s+x\d+', line)]
        assert len(stores) == len(calls) == 1
        order[label] = stores[0] < calls[0]
    assert order == dict(original=False, candidate=True)
    build_id = identity(elf)
    assert build_id == built['vmlinux_build_id'] and build_id != original['build_id']
    assert {path: pre.sha(Path(path)) for path in DATA['shared_before']} == DATA['shared_before']
    report = dict(stage=456, commit=pre.COMMIT, release=built['release'], build_banner_version=456,
                  config_sha256=built['artifacts']['.config']['sha256'], config_exactly_original363=True,
                  image_sha256=pre.sha(image), vmlinux_sha256=pre.sha(elf),
                  original_vmlinux_build_id=original['build_id'], candidate_vmlinux_build_id=build_id,
                  new_image_and_build_id_differ_from363=True,
                  actual_elf_exported_symbols=len(exports), actual_elf_export_names_exactly_original=True,
                  regenerated_vmlinux_symvers_exactly_original_builtin_metadata=True,
                  modversions_disabled_in_original_config=True,
                  compared_actual_dwarf_types=[name for name in TYPES if 'error' not in candidate_layouts[name]],
                  unavailable_reduced_dwarf_types=[name for name in TYPES if 'error' in candidate_layouts[name]],
                  image363_and_candidate_available_layouts_equal=True,
                  module455_compared_actual_dwarf_types=module_compared,
                  module455_api_dwarf_comparison_available=bool(module_compared),
                  module455_available_actual_dwarf_layouts_equal=True if module_compared else None,
                  module455_header_types_missing_from_reduced_dwarf=[name for name in TYPES if 'error' in module_layouts[name]],
                  module455_own_driver_struct_dwarf_size=module_layouts['bu64253']['size'],
                  module455_subdev_embedding_size_matches_actual_kernel=True,
                  module455_driver_member_offsets_bytes={name: field['bitpos']//8 for name, field in driver_fields.items()},
                  module455_other_compiler_source_dependencies_identical=dependency_count,
                  complete_struct_sizes={name: row['size'] for name, row in candidate_layouts.items() if 'error' not in row},
                  dwarf_reduced_member_pointee_types_may_be_incomplete=True,
                  module455_sha256=pre.sha(module), module455_imported_symbols=len(imports),
                  module455_imports_all_present_in_actual_candidate_exports=True,
                  core_release_function_disassembly_changed=True, actual_devnode_store_before_indirect_release_callback=order,
                  source_only_0064=True,
                  shared_artifacts_index_and_current_dtb_unchanged=True,
                  original_firmware_module_contents_and_initramfs_input_unchanged=True,
                  candidate_actual_embedded_initramfs=initramfs,
                  original_actual_embedded_initramfs=original['embedded_initramfs'],
                  actual_embedded_initramfs_comparison=archive,
                  boot_identity_requires_this_image_hash_and_running_kernel_build_id=True,
                  uname_release_alone_is_insufficient=True, boot_packaged=False,
                  phone_or_sdk_accessed=False, booted_or_installed=False, runtime_abi_not_yet_tested=True, passed=True)
    (HERE/'abi-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    (PRIVATE/'module455-imports-verified-private.json').write_text(json.dumps(imports, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
