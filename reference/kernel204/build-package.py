from pathlib import Path
import hashlib, json, lzma, os, re, shutil, struct, subprocess, sys, uuid, zlib

os.umask(0o077)
repo = Path('/home/cy122/edk2-samurai/repo')
ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel204')
target = out / 'firmware'
audit_existing = '--audit-existing-build' in sys.argv
if audit_existing:
    assert (target / 'boot-candidate-private.img').exists()
else:
    assert not target.exists()
    target.mkdir(mode=0o700)
sha = lambda b: hashlib.sha256(b).hexdigest()
source = json.loads((ref.parent / 'kernel164/source-validation.json').read_text())
for name, digest in source['after_sha256'].items():
    assert sha((repo / name).read_bytes()) == digest, name
dt = json.loads((ref / 'uart-candidate-validation.json').read_text())
dtb = (out / 'sm8150-samurai-bt-wake-static-private.dtb').read_bytes()
assert sha(dtb) == dt['candidate_dtb_sha256']
blob = repo / 'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb'
old_blob = blob.read_bytes()
if not audit_existing:
    (target / 'repository-dtb-before-private.dtb').write_bytes(old_blob)
diff = subprocess.check_output(['git', 'diff', '--binary'], cwd=repo)
fvpath = repo / 'workspace/Build/samurai/RELEASE_GCC5/FV'
for label, path in [('boot-local-before-private.img', repo / 'boot-samurai.img'),
                    ('fd-local-before-private.fd', fvpath / 'SM8150_UEFI.fd')]:
    if not audit_existing:
        shutil.copyfile(path, target / label)
compat = (repo / 'Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb').read_bytes()
env = os.environ.copy()
env.update(PATH='/home/cy122/.local/bin:' + env['PATH'], CPATH='/home/cy122/edk2-samurai/local/uuid/usr/include',
           LIBRARY_PATH='/home/cy122/edk2-samurai/local/uuid/usr/lib/x86_64-linux-gnu')
if not audit_existing:
    try:
        blob.write_bytes(dtb)
        with (target / 'firmware-build-private.log').open('wb') as log:
            subprocess.run(['./build.sh', '-d', 'samurai', '--toolchain', 'GCC5', '--skip-rootfs-gen'],
                           cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        for label, path in [('boot-candidate-private.img', repo / 'boot-samurai.img'),
                            ('firmware-candidate-private.fd', fvpath / 'SM8150_UEFI.fd'),
                            ('fvmain-candidate-private.Fv', fvpath / 'FVMAIN.Fv')]:
            shutil.copyfile(path, target / label)
    finally:
        blob.write_bytes(old_blob)
        os.utime(blob, None)
assert old_blob == (target / 'repository-dtb-before-private.dtb').read_bytes()
assert subprocess.check_output(['git', 'diff', '--binary'], cwd=repo) == diff
for name, digest in source['after_sha256'].items():
    assert sha((repo / name).read_bytes()) == digest
namespace = {}
helpers = (ref.parent / 'kernel104/verify-firmware.py').read_text().split('dt_audit=')[0]
exec(compile(helpers, 'existing-firmware-parser', 'exec'), namespace)
fv, sections, align, fdt_nodes = (namespace[n] for n in ['fv', 'sections', 'align', 'fdt_nodes'])
dt_guid, lz_guid = (namespace[n] for n in ['dt_guid', 'lz_guid'])

def unpack(boot):
    assert boot[:8] == b'ANDROID!'
    ks, rs, ss, page, version = [struct.unpack_from('<I', boot, p)[0] for p in [8, 16, 24, 36, 40]]
    assert page == 2048 and version == 1 and rs == 1 and ss == 0
    size = page + align(ks, page) + align(rs, page)
    d = zlib.decompressobj(31)
    raw = d.decompress(boot[page:page+ks]) + d.flush()
    assert d.eof and not d.unconsumed_tail and d.unused_data == compat
    fd = raw[144:]
    assert len(fd) == 0x700000
    compact = fv(fd)
    images = [m for m in compact.values() if m['type'] == 0xb]
    assert len(images) == 1 and len(images[0]['sections']) == 1
    typ, body, sec = images[0]['sections'][0]
    assert typ == 2 and str(uuid.UUID(bytes_le=body[:16])) == lz_guid
    offset, attrs = struct.unpack_from('<HH', body, 16)
    nested = sections(lzma.decompress(sec[offset:], format=lzma.FORMAT_ALONE))
    assert len(nested) == 1 and nested[0][0] == 0x17
    main = nested[0][1]
    return dict(boot=boot[:size], size=size, page=page, shim=raw[:144], fd=fd, main=main, modules=fv(main),
                ramdisk=boot[page+align(ks, page):page+align(ks, page)+rs])

before = (out.parent / 'kernel200/boot-partition-k200-mmcx.img').read_bytes()
assert sha(before) == '5109097b74aafd38838174f31fbff2d8c940977fdc4982658ebe86f671d1e1f0'
old = unpack(before)
new = unpack((target / 'boot-candidate-private.img').read_bytes())
assert old['shim'] == new['shim'] and old['ramdisk'] == new['ramdisk']
headers = [bytearray(v['boot'][:v['page']]) for v in [old, new]]
for h in headers:
    h[8:12] = b'\0' * 4
    h[576:608] = b'\0' * 32
assert headers[0] == headers[1]
assert old['modules'].keys() == new['modules'].keys()
changed = []
for guid, m in old['modules'].items():
    n = new['modules'][guid]
    assert (m['type'], m['attrs']) == (n['type'], n['attrs'])
    if m['body'] != n['body']:
        assert guid == dt_guid, n['name']
        changed.append(dict(guid=guid, name=n['name']))
assert len(changed) == 1 and changed[0]['guid'] == dt_guid
assert new['modules'][dt_guid]['sections'][0][1] == dtb
assert new['fd'] == (target / 'firmware-candidate-private.fd').read_bytes()
assert new['main'] == (target / 'fvmain-candidate-private.Fv').read_bytes()
oldtree = fdt_nodes(old['modules'][dt_guid]['sections'][0][1])
newtree = fdt_nodes(dtb)
assert set(oldtree) <= set(newtree)
assert set(newtree)-set(oldtree)==set(dt['new_sleep_nodes'])
dt_changes = [(p, n) for p in oldtree for n in set(oldtree[p]) | set(newtree[p]) if oldtree[p].get(n) != newtree[p].get(n)]
assert len(dt_changes)==4 and {n for p,n in dt_changes}=={'interrupts','interrupts-extended','pinctrl-names','pinctrl-1'},dt_changes
assert all(p=='/soc@0/geniqup@cc0000/serial@c8c000' for p,n in dt_changes)
assert oldtree['/soc@0/camss@acb3000']==newtree['/soc@0/camss@acb3000']

def normalize(line):
    line = re.sub(r'using serial compilation of \d+ LTRANS jobs', 'using serial compilation of N LTRANS jobs', line)
    return re.sub(r'(warning: )\S+\.dll has a LOAD segment with RWX permissions',
                  r'\1<module>.dll has a LOAD segment with RWX permissions', line)
diagnostics = lambda text: [l for l in text.splitlines() if re.search(r'\b(?:warning|error):', l, re.I)]
current = diagnostics((target / 'firmware-build-private.log').read_text())
prior = diagnostics((out.parent / 'kernel164/firmware/firmware-build-private.log').read_text())
assert not any(re.search(r'\berror:', l, re.I) for l in current)
assert all(normalize(l) in {normalize(x) for x in prior} for l in current), current
boot_path = out / 'boot-partition-k204-bt-wake.img'
assert not boot_path.exists()
boot_path.write_bytes(new['boot'] + before[new['size']:])
assert len(boot_path.read_bytes()) == len(before) == 100663296
assert boot_path.read_bytes()[new['size']:] == before[new['size']:]

baseline = json.loads((ref.parent / 'kernel183/build-package-validation.json').read_text())
report = dict(stage=204, kernel_build=183, firmware_build_pass=True,
    legacy_firmware_diagnostics=len(current), new_diagnostic_templates=0,
    firmware_only_dtb_changed=True, changed_modules=changed,
    all_firmware_code_and_non_version_data_unchanged=True,
    dtb_semantic_changes=[dict(node=p, property=n) for p, n in dt_changes], new_sleep_nodes=dt['new_sleep_nodes'],
    dtb_sha256=sha(dtb), kernel_image_preserved=baseline['image_sha256'],
    logdump_preserved=baseline['logdump_sha256'], repository_dtb_restored=True,
    bootshim_ramdisk_android_header_compat_preserved=True, boot_tail_preserved=True,
    fv_ffs_gzip_lzma_checked=True, boot_bytes=boot_path.stat().st_size,
    boot_sha256=sha(boot_path.read_bytes()), rollback_boot_sha256=sha(before),
    candidate_camss_sha256='82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58',
    flash_partitions=['boot'], hardware_not_deployed=True)
for directory in [out, ref]:
    (directory / 'build-package-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
