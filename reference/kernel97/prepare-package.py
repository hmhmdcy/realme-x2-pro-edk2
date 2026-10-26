from pathlib import Path, PurePosixPath
import hashlib, json, re, shutil, subprocess, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel97')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
k = json.loads((out / 'kernel-validation.json').read_text())
assert k['kernel_audit_pass'] and k['existing_files_symlinks_modes_preserved'] and k['dtb_byte_identical']
assert json.loads((out / 'runtime-validation.json').read_text())['runtime_address_lifecycle_pass']
recorded = dict(re.findall(r'([0-9a-f]{64})  /tmp/k97-(preflash.tar|boot-partition-before.img|logdump-before.img)', (out / 'preflash.log').read_text(encoding='utf-8-sig')))
recorded = {name: digest for digest, name in recorded.items()}
retry = (out / 'preflash-manifest-retry1.log').read_text(encoding='utf-8-sig')
recorded['preflash.tar'] = re.search(r'([0-9a-f]{64})  /tmp/k97-preflash-retry1.tar', retry).group(1)
assert 'a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7  /dev/sde11' in retry
assert '226c4da4c28953c394e9677af069e48c3cad0f036f922ea47712b762761c8722  /dev/sde32' in retry
for name in ('preflash.tar', 'boot-partition-before.img', 'logdump-before.img'):
    assert sha(out / name) == recorded[name]
assert sha(out / 'boot-partition-before.img') == 'a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7'
assert sha(out / 'logdump-before.img') == '226c4da4c28953c394e9677af069e48c3cad0f036f922ea47712b762761c8722'
files = {}
with tarfile.open(out / 'preflash.tar') as archive:
    for member in archive:
        if not member.isfile():
            continue
        path = PurePosixPath(member.name)
        assert path.parts[0] == 'k97-preflash-retry1' and '..' not in path.parts
        name = str(PurePosixPath(*path.parts[1:]))
        assert name not in files
        files[name] = archive.extractfile(member).read()
checked = set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1); name = name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest() == digest
    checked.add(name)
assert checked == files.keys() - {'SHA256SUMS'}
assert files['k97-runtime-retry1/result.txt'] == b'RUNTIME_ADDRESS_LIFECYCLE_PASS\n'
assert 'k97-runtime/samurai-bt-address-before-length-fix' in files
assert len(files['nv-source-check.txt'].decode().splitlines()) == 6
assert all(line.endswith(': OK') for line in files['nv-source-check.txt'].decode().splitlines())
boot_id = files['guard.txt'].decode().splitlines()[0]
assert re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot_id)
assert boot_id in files['state.txt'].decode()
(out / 'guard-before-flash.txt').write_bytes(files['guard.txt'])
(out / 'persist-before.sha').write_bytes(files['persist-before.sha'])
boot = out.parent / 'kernel93/boot-k93-connectivity.img'
assert sha(boot) == '0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158'
assert (out / 'boot-partition-before.img').read_bytes()[:boot.stat().st_size] == boot.read_bytes()
target = out / 'logdump-k97-connectivity.img'
assert not target.exists()
shutil.copyfile(out / 'logdump-before.img', target)
assert subprocess.check_output(['mcopy', '-i', str(target), '::/samurai.dtb', '-']) == (out / 'dtb-connectivity').read_bytes()
subprocess.run(['mcopy', '-o', '-i', str(target), str(out / 'Image-connectivity'), '::/Image'], check=True)
for name, dest in (('Image-connectivity', '::/Image'), ('dtb-connectivity', '::/samurai.dtb')):
    assert subprocess.check_output(['mcopy', '-i', str(target), dest, '-']) == (out / name).read_bytes()
assert set(subprocess.check_output(['mdir', '-b', '-s', '-i', str(target), '::'], text=True).splitlines()) == {'::/Image', '::/samurai.dtb'}
query = files['samurai-radio-address/current'].decode().strip().split('/')[-1]
new_data = [(out / name).read_bytes() for name in ('samurai-dms-mac-read', 'samurai-bt-address')]
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel97')
new_data += [(ref / name).read_bytes() for name in ('samurai-wifi', 'samurai-bluetooth', 'samurai-radio-address')]
for kind in ('bt', 'wlan'):
    value = files[f'samurai-radio-address/{query}/{kind}-mac-le.bin']
    assert len(value) == 6
    assert all(value not in content and value[::-1] not in content for content in new_data)
profile = (out.parent / 'kernel95/wpa-test-private.conf').read_text()
for value in re.findall(r'^\s*#?\s*(?:psk|ssid)\s*=\s*(.+?)\s*$', profile, flags=re.M):
    value = value.strip('"').encode()
    assert all(value not in content for content in new_data)
report = dict(candidate_audit_pass=True, original_initramfs_files_preserved=True,
              dtb_byte_identical=True, firmware_boot_reused_byte_identical=True,
              earlier_snapshots_preserved=True, embedded_wifi_credentials=False,
              embedded_device_addresses=False, nv_partition_writes=False, kernel_build=96,
              boot_sha256=sha(boot), logdump_sha256=sha(target),
              full_backup_boot_sha256=sha(out / 'boot-partition-before.img'),
              full_backup_logdump_sha256=sha(out / 'logdump-before.img'),
              only_flash_partitions=['logdump'], private_preflash_files_verified=len(checked),
              preflash_sha256=sha(out / 'preflash.tar'), before_boot_id=boot_id,
              bluetooth_scan_only=True, goal_complete=False)
(out / 'candidate-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'before_boot_id'}, indent=2))
