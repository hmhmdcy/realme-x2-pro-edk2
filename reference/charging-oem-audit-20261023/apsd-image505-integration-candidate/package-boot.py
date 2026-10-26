"""Actual505 BDS/native-DTB two-FFS offline carrier; never deploys."""
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
CURRENT = ROOT / 'usb-input-irq-boot-private-01/boot-usb-input-irq-private.img'
OUT = ROOT / 'apsd-image505-boot-private-01'
DTB = ROOT / 'apsd-image505-dtb-private-02/samurai-apsd505-native-private.dtb'
EFI = Path('/home/cy122/charging-management-20261023/apsd-image505-bds-01/BdsDxe.efi')
PAIR = HERE / 'assembly-inputs.json'
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
    assert file_sha(CURRENT)=='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
    pair=json.loads(PAIR.read_bytes())
    assert pair['prepared'] and not pair['installed']
    assert file_sha(EFI)==pair['artifacts']['BDS_EFI']['sha256']=='939345bc6bb9f114e77da614e33e36d5bd4bfc59f8c17d3bc547bf2f35084f0b'
    assert file_sha(DTB)==pair['artifacts']['native_DTB']['sha256']=='d5fa6cabdd231fed8e35b26cb17e8d4c59068705d90285775b7ede48f2e338d3'
    assert pair['actual_cmdline'].encode('utf-16-le') in EFI.read_bytes()
    assert file_sha(OLD/'result.json')=='2d46df7c53dd8378800160d542bb9ded28067039b6403b87d47d625664bb31b8'
    previous=json.loads((OLD/'result.json').read_bytes());assert previous['passed']
    for name in ['FVMAIN.inf','FVMAIN_COMPACT.inf']:assert file_sha(OLD/name)==previous['artifacts'][name]
    for tool in m['tools']:assert file_sha(Path(tool['path']))==tool['sha256']
    old=unpack(CURRENT);mods=fv(old['main']);assert len(mods)==101 and old['used']==LIMIT
    assert sha(mods[BDS]['sections'][1][1])=='071a628bd34c8d4715c0b57b89a219e21c236d2f5f16c8d82bd832de4dcc196b'
    assert sha(mods[DT]['sections'][0][1])=='13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f'
    return old

def verify_main(main,old):
    a,b=raw_files(old['main']),raw_files(main)
    assert list(a)==list(b) and len(b)==101
    changed=[guid for guid in a if a[guid]['full']!=b[guid]['full']];assert set(changed)=={BDS,DT}
    assert all(a[guid]['full']==b[guid]['full'] for guid in a if guid not in {BDS,DT})
    previous,mods=fv(old['main']),fv(main)
    assert all((previous[guid]['type'],previous[guid]['attrs'])==(mods[guid]['type'],mods[guid]['attrs']) for guid in a)
    bs=mods[BDS]['sections'];assert [item[0] for item in bs]==[0x13,0x10,0x15]
    assert bs[0][2]==previous[BDS]['sections'][0][2] and bs[2][2]==previous[BDS]['sections'][2][2]
    assert bs[1][1]==EFI.read_bytes() and mods[DT]['sections'][0][1]==DTB.read_bytes()
    return dict(changed_complete_FFS=changed,other99_complete_FFS_exact=True,BDS_depex_UI_exact=True,BDS_EFI_and_native_DTB_exact=True)


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
    assert not (HERE / 'boot-package-result.json').exists()
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
        bds=fv(old['main'])[BDS]['sections']
        (OUT/'sections/BDS.dpx').write_bytes(bds[0][2]);(OUT/'sections/BDS.ui').write_bytes(bds[2][2])
        tool('GenSec',['-s','EFI_SECTION_PE32','-o',OUT/'sections/BDS.pe32',EFI],'BDS-PE32')
        tool('GenFfs',['-t','EFI_FV_FILETYPE_DRIVER','-g',BDS,'-o',inputs[BDS],'-oi',OUT/'sections/BDS.dpx','-oi',OUT/'sections/BDS.pe32','-oi',OUT/'sections/BDS.ui'],'BDS-FFS')

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
        target = OUT / 'boot-apsd505-private.img'
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
        save(HERE / 'boot-package-result.json', result)
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
        raise SystemExit('Default check-local; authorized offline --execute-boot; no device access')
