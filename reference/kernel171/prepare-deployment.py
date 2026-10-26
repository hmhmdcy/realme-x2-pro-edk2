from pathlib import Path
import json, tarfile

ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel171')
build = json.loads((ref / 'build-package-validation.json').read_text())
assert build['image_unchanged'] and build['all_firmware_code_and_non_version_data_unchanged']
files = ['collect-preflash.py', 'quiesce-current163.sh', 'check-quiesce.py',
         'freeze-for-bootloader.sh', 'enter-bootloader.ps1', 'enable-transition-eud.ps1']
for name in files:
    text = (ref.parent / 'kernel169' / name).read_text()
    for old, new in [('kernel169', 'kernel171'), ('k169', 'k171'), ('K169', 'K171'),
                     ('stage=169', 'stage=171'), ('same168-second', 'speaker-sd1')]:
        text = text.replace(old, new)
    if name == 'collect-preflash.py':
        text = text.replace("if part=='logdump': assert actual_size==size", 'assert actual_size==size')
        text = text.replace("capture(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],'nv-check.txt')", """
hashes=dict((line.split()[1],line.split()[0]) for line in (out/'partition-check.sha256').read_text().splitlines())
assert hashes['/dev/sde11']=='d96c8b6cb7cf4cef7349360ea87793692ec3b3df8200934f4264dc3cc361f37c'
assert hashes['/dev/sde32']=='3ecb785f64bb533b4b649baa179bf66e8166f74ee85a41a07b9ce6cc26fb60b9'
assert hashes['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
capture(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],'nv-check.txt')""")
    assert not (ref / name).exists()
    (ref / name).write_text(text)
with tarfile.open(out / 'deployment-tools-private.tar', 'w') as archive:
    for name in files:
        if not name.endswith('.ps1'):
            archive.add(ref / name, arcname=name)
print(json.dumps(dict(stage=171, current_kernel=168, target_kernel=168,
                      fresh_boot_identity_required=True, target_boot_and_logdump=171)))
