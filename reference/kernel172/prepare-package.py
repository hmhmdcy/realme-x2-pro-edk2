from pathlib import Path

ref = Path(__file__).parent
s = (ref.parent / 'kernel171/build-package.py').read_text()
s = s.replace("out = Path('/mnt/e/edk2-samurai-out/kernel171')", "out = Path('/mnt/e/edk2-samurai-out/kernel172')")
s = s.replace("dt = json.loads((ref / 'dtb-build-validation.json').read_text())", "dt = json.loads((ref / 'kernel-build-validation.json').read_text())")
s = s.replace('samurai-sd1-k171-private.dtb','samurai-headset-k172-private.dtb')
s = s.replace("dt['dtb_after_sha256']", "dt['dtb_sha256']")
s = s.replace("out.parent / 'kernel164/boot-partition-k164-panel-handoff.img'", "out.parent / 'kernel171/boot-partition-k171-speaker-sd1.img'")
s = s.replace('d96c8b6cb7cf4cef7349360ea87793692ec3b3df8200934f4264dc3cc361f37c', '612a012426200d4997b33ee98edd18ea6e15a61d23901aa82cb61acd68c392f2')
a = s.index('version_before ='); b = s.index("assert new['modules'][dt_guid]", a)
s = s[:a] + '''for guid, m in old['modules'].items():
    n = new['modules'][guid]
    assert (m['type'], m['attrs']) == (n['type'], n['attrs'])
    if m['body'] != n['body']:
        assert guid == dt_guid, n['name']
        changed.append(dict(guid=guid, name=n['name']))
assert len(changed) == 1 and changed[0]['guid'] == dt_guid
''' + s[b:]
a = s.index('assert len(dt_changes)'); b = s.index('\ndef normalize', a)
s = s[:a] + '''assert len(dt_changes) == 2 and sorted(n for p, n in dt_changes) == ['audio-routing', 'widgets'], dt_changes
assert sorted((r['node'], r['property']) for r in dt['dtb_semantic_changes']) == sorted(dt_changes)
''' + s[b:]
s = s.replace('boot-partition-k171-speaker-sd1.img', 'boot-partition-k172-headset.img')
# The replacement above also touched the rollback path: restore it explicitly.
s = s.replace("out.parent / 'kernel171/boot-partition-k172-headset.img'", "out.parent / 'kernel171/boot-partition-k171-speaker-sd1.img'")
s = s.replace("out.parent / 'kernel168/logdump-k168-audio.img'", "out.parent / 'kernel171/logdump-k171-speaker-sd1.img'")
s = s.replace('3ecb785f64bb533b4b649baa179bf66e8166f74ee85a41a07b9ce6cc26fb60b9', 'd711ab4122eba4b0f2cc9d9792c89eb05c49957fb637b19aa595e878909921f6')
s = s.replace("image = subprocess.check_output(['mcopy', '-i', str(logdump_old), '::/Image', '-'])", "image = (out / 'Image-k172-headset-private').read_bytes()\nassert sha(image) == dt['image_sha256']")
s = s.replace('logdump-k171-speaker-sd1.img', 'logdump-k172-headset.img')
s = s.replace("out.parent / 'kernel171/logdump-k172-headset.img'", "out.parent / 'kernel171/logdump-k171-speaker-sd1.img'")
old = "shutil.copyfile(logdump_old, logdump)\n"
assert s.count(old) == 1
s = s.replace(old, old + "subprocess.run(['mcopy', '-o', '-i', str(logdump), str(out / 'Image-k172-headset-private'), '::/Image'], check=True)\n")
s = s.replace('dict(stage=171, kernel_build_kept=168', 'dict(stage=172, kernel_build=172')
s = s.replace('firmware_only_dtb_and_version_metadata_changed=True', 'firmware_only_dtb_changed=True')
s = s.replace('firmware_version_before=version_before, firmware_version_after=version_after,\n              version_metadata_only_modules=metadata_changed, ', '')
s = s.replace('image_unchanged=True', 'image_unchanged=False, modules132_runtime_compatible=dt["modules132_runtime_compatible"]')
s = s.replace('bds164_exact_except_version_string=True', 'bds171_exact=True')
assert not (ref / 'build-package.py').exists()
(ref / 'build-package.py').write_text(s)
compile(s, 'build-package.py', 'exec')
print('K172_PACKAGE_BUILDER_PREPARED')
