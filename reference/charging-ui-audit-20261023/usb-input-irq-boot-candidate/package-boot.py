"""Default read-only check; one private native-DTB-FFS substitution, never deploys."""
from pathlib import Path
import ast
import hashlib
import json
import lzma
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import traceback
import zlib

sys.dont_write_bytecode = True
if sys.flags.optimize:
    raise RuntimeError('Non-optimized interpreter required')
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
ROOT = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OLD = ROOT / 'gauge-image501-boot-private-01'
CURRENT = OLD / 'boot-gauge501-private.img'
OUT = ROOT / 'usb-input-irq-boot-private-01'
DTB = ROOT / 'usb-input-irq-board-private-01/samurai-usb-input-irq-native-private.dtb'
EFI = ROOT / 'gauge-image501-bds-private-01/BdsDxe/OUTPUT/BdsDxe.efi'
PAIR = REF / 'charging-ui-audit-20261023/usb-input-irq-board-candidate/pair-manifest.json'
BDS = '6d33944a-ec75-4855-a54d-809c75241f6c'
DT = '25462cda-221f-47df-ac1d-259cfaa4e326'
SEC = '8af09f13-44c5-96ec-1437-dd899cb5ee5d'
CONTAINER = '9e21fd93-9c72-4c15-8c4b-e77f1db2d792'
LIMIT, PARTITION = 6684672, 100663296
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, obj):
    with path.open('w') as stream:
        json.dump(obj, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


# Reuse exact parser and helper bodies, without running old packaging entrypoints
# or baseline-draft's top-level reads of shared firmware build inputs.
parser = REF / 'kernel104/verify-firmware.py'
assert file_sha(parser) == '2e0b03aa3cf7ae7651e0b2e1153c1c5eb0cba3a3b41ef1d375c9b06358cb9d5d'
scope = {}
exec(compile(parser.read_text().split('\ndt_audit=', 1)[0], str(parser) + ':definitions-only', 'exec'), scope)
fv, sections, align = scope['fv'], scope['sections'], scope['align']
old_source = REF / 'charging-session-20261023/gauge-image501-carriers-candidate/package-boot.py'
assert file_sha(old_source) == '6581d1c4c2eb0e6a409f31fb5859c95389d6cdd31f64a436b65473cbde4d8f08'
source = old_source.read_text()
for node in ast.parse(source).body:
    if isinstance(node, ast.FunctionDef) and node.name in {'raw_files', 'extract_current', 'id_value'}:
        exec(compile(ast.get_source_segment(source, node), str(old_source) + ':' + node.name, 'exec'), globals())
inspection = REF / 'charging-session-20261023/eud-boot-packaging-review/inspection.json'
assert file_sha(inspection) == '2caa68c513fd7503e0357aa4eb392594c906c82133c6e8d5d1fd3c3e703a3b87'
m = json.loads(inspection.read_bytes())
TOOLS = {Path(row['path']).name: row['path'] for row in m['tools']}


def inf(template, paths, output):
    ordered = iter(paths)
    text = re.sub(r'^EFI_FILE_NAME\s*=.*$', lambda _: 'EFI_FILE_NAME = ' + str(next(ordered)),
                  template.read_text(), flags=re.M)
    assert next(ordered, None) is None
    output.write_text(text)


def decode_payload(header, payload, ramdisk):
    assert header[:8] == b'ANDROID!'
    ks, rs, second, page, version = [struct.unpack_from('<I', header, off)[0] for off in [8, 16, 24, 36, 40]]
    assert (rs, second, page, version) == (1, 0, 2048, 1) and ks == len(payload)
    assert ramdisk == b'\n' and header[576:608] == id_value(payload, ramdisk)
    d = zlib.decompressobj(31)
    raw = d.decompress(payload) + d.flush()
    assert d.eof and not d.unconsumed_tail and len(raw) == 7340176
    compat = d.unused_data
    assert sha(compat) == m['android']['compat_sha256']
    gz = payload[:-len(compat)]
    assert gz[:10].hex() == m['android']['gzip_header_hex'] and gz[3] == 0
    fd = raw[144:]
    outer = fv(fd)
    assert list(outer) == [SEC, CONTAINER]
    assert len(outer[CONTAINER]['sections']) == 1
    typ, body, section = outer[CONTAINER]['sections'][0]
    assert typ == 2
    import uuid
    assert str(uuid.UUID(bytes_le=body[:16])) == m['compression']['guided_guid']
    offset, attributes = struct.unpack_from('<HH', body, 16)
    assert (offset, attributes) == (24, 1)
    nested = sections(lzma.decompress(section[offset:], format=lzma.FORMAT_ALONE))
    assert len(nested) == 1 and nested[0][0] == 0x17
    return {'header': header, 'payload': payload, 'gzip': gz, 'raw': raw,
            'shim': raw[:144], 'fd': fd, 'main': nested[0][1], 'compat': compat,
            'ks': ks, 'ram_offset': 2048 + align(ks, 2048), 'used': 4096 + align(ks, 2048)}


def unpack(path):
    assert path.stat().st_size == PARTITION
    with path.open('rb') as stream:
        header = stream.read(2048)
        ks = struct.unpack_from('<I', header, 8)[0]
        payload = stream.read(ks)
        pad = stream.read(align(ks, 2048) - ks)
        assert not any(pad)
        ram_page = stream.read(2048)
    result = decode_payload(header, payload, ram_page[:1])
    result['ram_page'] = ram_page
    return result


def check_local():
    assert file_sha(CURRENT) == '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
    assert file_sha(OLD / 'result.json') == '2d46df7c53dd8378800160d542bb9ded28067039b6403b87d47d625664bb31b8'
    receipt = json.loads((OLD / 'result.json').read_bytes())
    assert receipt['passed'] and receipt['parent_inputs_unchanged'] and receipt['SEC_full_FFS_preserved']
    assert file_sha(PAIR) == '1d1e65c1e29a25694906f1c3004972e751209b5562e070bec885ced35bcafb16'
    pair = json.loads(PAIR.read_bytes())
    assert pair['required_together'] and pair['new_DTB_must_not_be_used_with_old_R7_module']
    assert file_sha(DTB) == pair['native_DTB']['sha256'] == '13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f'
    assert file_sha(ROOT / 'usb-input-irq-board-private-01/samurai-usb-input-irq-private.ko') == pair['USB_module']['sha256']
    assert file_sha(EFI) == '071a628bd34c8d4715c0b57b89a219e21c236d2f5f16c8d82bd832de4dcc196b'
    assert 'bq27xxx_battery.samurai_instant_current=1'.encode('utf-16-le') in EFI.read_bytes()
    for name in ['FVMAIN.inf', 'FVMAIN_COMPACT.inf']:
        assert file_sha(OLD / name) == receipt['artifacts'][name]
    for ext in ['.ffs', '.efi', '.map']:
        name = SEC.upper() + ext
        # The executed501 receipt lists only top-level artifacts. Its before
        # snapshot pins the original pre-rebase SEC inputs copied here.
        matches = [value for key, value in receipt['inputs_before'].items() if key.endswith('/' + name)]
        assert len(set(matches)) == 1 and file_sha(OLD / 'inputs' / name) == matches[0]
    for row in m['tools']:
        assert file_sha(Path(row['path'])) == row['sha256']
    old = unpack(CURRENT)
    assert (old['ks'], old['used']) == (6680472, LIMIT)
    mods = fv(old['main'])
    assert len(mods) == 101 and mods[BDS]['sections'][1][1] == EFI.read_bytes()
    assert len(mods[DT]['sections']) == 1 and mods[DT]['sections'][0][0] == 0x19
    assert sha(mods[DT]['sections'][0][1]) == '9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'
    assert mods[DT]['type'] == 2
    return old


def verify_main(main, old):
    a, b = raw_files(old['main']), raw_files(main)
    assert list(a) == list(b) and len(b) == 101
    changed = [guid for guid in a if a[guid]['full'] != b[guid]['full']]
    assert changed == [DT], changed
    assert all(a[guid]['full'] == b[guid]['full'] for guid in a if guid != DT)
    oldmods, mods = fv(old['main']), fv(main)
    assert all((oldmods[g]['type'], oldmods[g]['attrs']) == (mods[g]['type'], mods[g]['attrs']) for g in a)
    assert len(mods[DT]['sections']) == 1 and mods[DT]['sections'][0][0] == 0x19
    assert mods[DT]['sections'][0][1] == DTB.read_bytes()
    assert mods[BDS]['sections'][1][1] == EFI.read_bytes()
    return {'changed_complete_FFS': changed, 'other100_complete_FFS_exact': True,
            'BDS_complete_FFS_and_EFI_exact': True, 'native_DTB_exact': True}


def equal_tail(a, b, offset):
    with a.open('rb') as x, b.open('rb') as y:
        x.seek(offset)
        y.seek(offset)
        while True:
            left = x.read(1024 * 1024)
            right = y.read(1024 * 1024)
            if left != right:
                return False
            if not left:
                return True


def execute():
    assert not OUT.exists(), 'Unique candidate output exists; do not replay'
    assert not (HERE / 'result.json').exists()
    old = check_local()
    paths = {CURRENT, DTB, EFI, PAIR, parser, old_source, inspection, Path(__file__), OLD / 'result.json',
             OLD / 'FVMAIN.inf', OLD / 'FVMAIN_COMPACT.inf'}
    paths.update(Path(row['path']) for row in m['tools'])
    paths.update(OLD / 'inputs' / (SEC.upper() + ext) for ext in ['.ffs', '.efi', '.map'])
    before = {str(path): file_sha(path) for path in paths}
    mount_before = Path('/proc/self/mountinfo').read_bytes()
    OUT.mkdir(parents=True)
    (OUT / 'inputs').mkdir()
    (OUT / 'sections').mkdir()
    result = {'passed': False, 'private_output': str(OUT), 'host_pid': os.getpid(), 'commands': [],
              'runner_sha256': file_sha(Path(__file__)), 'parent_inputs_before': before,
              'source_boot_sha256': before[str(CURRENT)], 'BDS_EFI_sha256': before[str(EFI)],
              'native_DTB_sha256': before[str(DTB)], 'paired_ko_manifest_sha256': before[str(PAIR)],
              'max_used': LIMIT, 'original_payload_page_slack': 104,
              'Image_SDK_BDS_build_rootfs_package_device_action': False}

    def tool(name, args, stage, stdin=None, stdout=None):
        argv = [TOOLS[name]] + [str(value) for value in args]
        entry = {'stage': stage, 'argv': argv}
        result['commands'].append(entry)
        env = {**os.environ, 'PATH': '/usr/bin:/bin'}
        env.pop('GZIP', None)
        with (OUT / (stage + '.stderr')).open('xb') as error, (OUT / (stage + '.stdout')).open('xb') as log:
            if stdin is None:
                proc = subprocess.Popen(argv, cwd=OUT, env=env, stdout=log, stderr=error)
                try:
                    entry.update(pid=proc.pid, terminal=False)
                    save(OUT / 'result.json', result)
                    print(json.dumps({'stage': stage, 'pid': proc.pid, 'started': True}), flush=True)
                finally:
                    ret = proc.wait()
            else:
                with Path(stdin).open('rb') as source, Path(stdout).open('xb') as output:
                    st = os.fstat(source.fileno())
                    assert stat.S_ISREG(st.st_mode) and st.st_size == 7340176 and st.st_mtime_ns == 1792719172000000000
                    entry['stdin_regular_and_original_repro_mtime'] = True
                    proc = subprocess.Popen(argv, cwd=OUT, env=env, stdin=source, stdout=output, stderr=error)
                    try:
                        entry.update(pid=proc.pid, terminal=False)
                        save(OUT / 'result.json', result)
                        print(json.dumps({'stage': stage, 'pid': proc.pid, 'started': True}), flush=True)
                    finally:
                        ret = proc.wait()
        entry.update(terminal=True, returncode=ret, stderr_sha256=file_sha(OUT / (stage + '.stderr')))
        save(OUT / 'result.json', result)
        assert ret == 0, (stage, ret)

    try:
        inputs = extract_current(old['main'], OUT / 'inputs')
        tool('GenSec', ['-s', 'EFI_SECTION_RAW', '-o', OUT / 'sections/DTB.raw', DTB], 'DTB-RAW')
        tool('GenFfs', ['-t', 'EFI_FV_FILETYPE_FREEFORM', '-g', DT, '-o', inputs[DT], '-i', OUT / 'sections/DTB.raw'], 'DTB-FFS')
        inf(OLD / 'FVMAIN.inf', [inputs[row['guid']] for row in m['main_FV']['files']], OUT / 'FVMAIN.inf')
        tool('GenFv', ['-g', m['main_FV']['filesystem_guid'], '-i', OUT / 'FVMAIN.inf', '-o', OUT / 'main.Fv'], 'mainFV')
        result['main_verification'] = verify_main((OUT / 'main.Fv').read_bytes(), old)
        tool('GenSec', ['-s', 'EFI_SECTION_FIRMWARE_VOLUME_IMAGE', '-o', OUT / 'main.fv.sec', OUT / 'main.Fv'], 'FV-IMAGE')
        tool('GenSec', ['--sectionalign', '8', '-o', OUT / 'main.aligned', OUT / 'main.fv.sec'], 'align8')
        tool('LzmaCompress', ['-e', '-o', OUT / 'main.lzma', OUT / 'main.aligned'], 'LZMA')
        tool('GenSec', ['-s', 'EFI_SECTION_GUID_DEFINED', '-g', m['compression']['guided_guid'], '-r', 'PROCESSING_REQUIRED', '-o', OUT / 'main.guided', OUT / 'main.lzma'], 'GUIDED')
        tool('GenFfs', ['-t', 'EFI_FV_FILETYPE_FIRMWARE_VOLUME_IMAGE', '-g', CONTAINER, '-o', OUT / 'container.ffs', '-i', OUT / 'main.guided'], 'containerFFS')
        for ext in ['.ffs', '.efi', '.map']:
            shutil.copy2(OLD / 'inputs' / (SEC.upper() + ext), OUT / 'inputs' / (SEC.upper() + ext))
        inf(OLD / 'FVMAIN_COMPACT.inf', [OUT / 'inputs' / (SEC.upper() + '.ffs'), OUT / 'container.ffs'], OUT / 'FVMAIN_COMPACT.inf')
        tool('GenFv', ['-g', m['compact_FV']['filesystem_guid'], '-i', OUT / 'FVMAIN_COMPACT.inf', '-o', OUT / 'compact.fd'], 'compactFD')
        fd = (OUT / 'compact.fd').read_bytes()
        a, b = raw_files(old['fd']), raw_files(fd)
        assert len(fd) == 7340032 and list(a) == list(b) == [SEC, CONTAINER]
        assert b[SEC]['offset'] == a[SEC]['offset'] == 0xfe8 and b[SEC]['full'] == a[SEC]['full']
        assert b[CONTAINER]['offset'] == a[CONTAINER]['offset']
        header_size = struct.unpack_from('<H', fd, 48)[0]
        assert fd[:header_size] == old['fd'][:header_size]
        raw = old['shim'] + fd
        (OUT / 'raw.bin').write_bytes(raw)
        os.utime(OUT / 'raw.bin', ns=(1792719172000000000, 1792719172000000000))
        tool('gzip', ['-c'], 'gzip', stdin=OUT / 'raw.bin', stdout=OUT / 'raw.gz')
        gz = (OUT / 'raw.gz').read_bytes()
        assert gz[:10] == old['gzip'][:10]
        payload = gz + old['compat']
        ks = len(payload)
        new_ram, used = 2048 + align(ks, 2048), 4096 + align(ks, 2048)
        result.update(new_kernel_size=ks, new_used=used, geometry_passed=used <= LIMIT)
        assert used <= LIMIT, 'Compressed result exceeds original absolute tail; no boot output'
        header = bytearray(old['header'])
        header[8:12] = struct.pack('<I', ks)
        header[576:608] = id_value(payload, b'\n')
        target = OUT / 'boot-usb-input-irq-private.img'
        with target.open('xb') as output, CURRENT.open('rb') as original:
            output.write(header)
            output.write(payload)
            output.write(b'\0' * (new_ram - 2048 - ks))
            output.write(old['ram_page'])
            assert output.tell() == used
            original.seek(used)
            shutil.copyfileobj(original, output, 1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        assert target.stat().st_size == PARTITION
        parsed = unpack(target)
        assert parsed['raw'][:144] == old['shim'] and parsed['fd'] == fd
        result['written_main_verification'] = verify_main(parsed['main'], old)
        check_header = bytearray(parsed['header'])
        old_header = bytearray(old['header'])
        for item in [check_header, old_header]:
            item[8:12] = b'\0' * 4
            item[576:608] = b'\0' * 32
        assert check_header == old_header and parsed['ram_page'] == old['ram_page']
        assert parsed['compat'] == old['compat'] and equal_tail(target, CURRENT, used)
        assert equal_tail(target, CURRENT, LIMIT)
        result.update(passed=True, boot_path=str(target), boot_sha256=file_sha(target), boot_bytes=PARTITION,
                      SEC_complete_FFS_and_offset_exact=True, SEC_offset=0xfe8,
                      shim_compat_ramdisk_exact=True, header_only_size_ID_changed=True,
                      absolute_tail_exact=True, written_boot_fully_reparsed=True,
                      no_external_FAT_Image_or_rootfs_modified=True)
    except BaseException as error:
        result.update(error=repr(error), traceback=traceback.format_exc())
    finally:
        after = {str(path): file_sha(path) for path in paths}
        result.update(parent_inputs_after=after, parent_inputs_unchanged=before == after,
                      parent_mountinfo_unchanged=mount_before == Path('/proc/self/mountinfo').read_bytes())
        result['passed'] = result['passed'] and result['parent_inputs_unchanged'] and result['parent_mountinfo_unchanged']
        result['artifact_sha256'] = {str(path.relative_to(OUT)): file_sha(path) for path in OUT.rglob('*')
                                     if path.is_file() and path.name != 'result.json'}
        save(OUT / 'result.json', result)
        save(HERE / 'result.json', result)
        print(json.dumps({key: result.get(key) for key in ['passed', 'new_kernel_size', 'new_used',
                         'boot_sha256', 'parent_inputs_unchanged', 'error']}), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    if sys.argv[1:] in [[], ['--check-local']]:
        data = check_local()
        print(json.dumps({'passed': True, 'tools_executed': False, 'candidate_directory_exists': OUT.exists(),
                          'original_kernel_size': data['ks'], 'max_used': LIMIT, 'original_slack': 104}))
    elif sys.argv[1:] == ['--execute-boot']:
        raise SystemExit(execute())
    else:
        raise SystemExit('Default check-local; only separately approved --execute-boot')
