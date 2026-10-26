from pathlib import Path
import hashlib, json, lzma, re, struct, zlib

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel164')
out = Path('/mnt/e/edk2-samurai-out/kernel164')
target = out / 'firmware'
namespace = {}
helpers = (ref.parent / 'kernel104/verify-firmware.py').read_text().split('dt_audit=')[0]
exec(compile(helpers, 'verified-firmware-format-helpers', 'exec'), namespace)
fv, sections, align = (namespace[name] for name in ['fv', 'sections', 'align'])
dt_guid, lz_guid, cmd = (namespace[name] for name in ['dt_guid', 'lz_guid', 'cmd'])
sha = lambda data: hashlib.sha256(data).hexdigest()
def diagnostic_lines(path):
    return [line for line in path.read_text().splitlines() if re.search(r'\b(?:warning|error):', line, re.I)]
def normalized(line):
    return re.sub(r'using serial compilation of \d+ LTRANS jobs', 'using serial compilation of N LTRANS jobs', line)
current_diagnostics = diagnostic_lines(target / 'firmware-build-private.log')
pristine_diagnostics = diagnostic_lines(target / 'pristine-comparison-build-private.log')
assert all(normalized(line) in {normalized(row) for row in pristine_diagnostics} for line in current_diagnostics)
assert not any(re.search(r'\berror:', line, re.I) for line in current_diagnostics)
assert all('warning: Suspicious expression:' in line or 'has a LOAD segment with RWX permissions' in line or
           'warning: using serial compilation of' in line for line in current_diagnostics)
backup = json.loads((ref / 'boot-backup-validation.json').read_text())
before = (out / 'boot-partition-before-private.img').read_bytes()
assert len(before) == 100663296 and sha(before) == backup['boot_backup_sha256']
expected_before = json.loads((ref.parent / 'kernel132/boot-package-validation.json').read_text())
assert sha(before) == expected_before['boot_sha256']
compat = (target / 'compat-before.dtb').read_bytes()
dtb = (target / 'firmware-after.dtb').read_bytes()
expected_dtb = json.loads((ref.parent / 'kernel163/build-package-validation.json').read_text())['dtb_sha256']
assert sha(dtb) == expected_dtb
def unpack(boot):
    assert boot[:8] == b'ANDROID!'
    ks, rs, ss, page, version = [struct.unpack_from('<I', boot, offset)[0] for offset in (8, 16, 24, 36, 40)]
    assert page == 2048 and version == 1 and rs == 1 and ss == 0
    size = page + align(ks, page) + align(rs, page)
    decoder = zlib.decompressobj(31)
    raw = decoder.decompress(boot[page:page+ks]) + decoder.flush()
    assert decoder.eof and not decoder.unconsumed_tail and decoder.unused_data == compat
    fd = raw[144:]
    assert len(fd) == 0x700000
    compact = fv(fd)
    images = [entry for entry in compact.values() if entry['type'] == 0xb]
    assert len(images) == 1 and len(images[0]['sections']) == 1
    kind, body, section = images[0]['sections'][0]
    import uuid
    assert kind == 2 and str(uuid.UUID(bytes_le=body[:16])) == lz_guid
    offset, attrs = struct.unpack_from('<HH', body, 16)
    nested = sections(lzma.decompress(section[offset:], format=lzma.FORMAT_ALONE))
    assert len(nested) == 1 and nested[0][0] == 0x17
    main = nested[0][1]
    modules = fv(main)
    assert modules[dt_guid]['sections'][0][1] == dtb
    assert cmd.encode('utf-16-le') in main and 'Linux (mainline samurai)'.encode('utf-16-le') in main
    return dict(boot=boot[:size], size=size, page=page, shim=raw[:144], fd=fd, main=main, modules=modules,
                ramdisk=boot[page+align(ks, page):page+align(ks, page)+rs])
actual = unpack(before)
pristine = unpack((target / 'boot-pristine-current.img').read_bytes())
candidate = unpack((target / 'boot-panel-handoff.img').read_bytes())
assert candidate['fd'] == (target / 'firmware-after.fd').read_bytes() == (target / 'fvcompact-after.Fv').read_bytes()
assert candidate['main'] == (target / 'fvmain-after.Fv').read_bytes()
assert actual['shim'] == candidate['shim'] == pristine['shim']
assert actual['ramdisk'] == candidate['ramdisk'] == pristine['ramdisk']
headers = [bytearray(data['boot'][:data['page']]) for data in [actual, candidate]]
for header in headers:
    header[8:12] = b'\0'*4
    header[576:608] = b'\0'*32
assert headers[0] == headers[1]
assert actual['modules'].keys() == candidate['modules'].keys() == pristine['modules'].keys()
changes = []
pristine_changes = []
for guid, entry in actual['modules'].items():
    new = candidate['modules'][guid]
    old = pristine['modules'][guid]
    assert (entry['type'], entry['attrs']) == (new['type'], new['attrs']) == (old['type'], old['attrs'])
    if entry['body'] != old['body']:
        pristine_changes.append(dict(guid=guid, name=old['name']))
    if entry['body'] != new['body']:
        changes.append(dict(guid=guid, name=new['name'], before_sha256=sha(entry['body']), after_sha256=sha(new['body'])))
assert len(changes) == 1 and changes[0]['name'] == 'BdsDxe', changes
assert not pristine_changes, pristine_changes
image = out / 'boot-partition-k164-panel-handoff.img'
assert not image.exists()
image.write_bytes(candidate['boot'] + before[candidate['size']:])
assert len(image.read_bytes()) == 100663296 and image.read_bytes()[candidate['size']:] == before[candidate['size']:]
report = dict(stage=164, kernel_build_kept=163, firmware_audit_pass=True,
              full_firmware_and_pristine_comparison_build_pass=True,
              current_compiler_advisory_templates_reproduced_in_pristine_build=True,
              diagnostic_count=len(current_diagnostics), distinct_diagnostic_templates=len({normalized(row) for row in current_diagnostics}),
              pristine_all_modules_byte_exact_current132=True, only_bds_executable_changed=True,
              changed_modules=changes, embedded_dtb_unchanged_current132_and163=True, dtb_sha256=sha(dtb),
              bootshim_ramdisk_android_header_and_compat_preserved=True,
              gzip_crc_fv_ffs_and_lzma_checks_pass=True, boot_tail_preserved=True,
              boot_bytes=image.stat().st_size, boot_sha256=sha(image.read_bytes()),
              boot_payload_bytes=candidate['size'], current_backup_sha256=sha(before),
              intended_flash_partitions=['boot'], logdump163_kept=True, deployed=False,
              physical_bug_fixed=False)
for directory in [ref, out]:
    (directory / 'boot-package-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
