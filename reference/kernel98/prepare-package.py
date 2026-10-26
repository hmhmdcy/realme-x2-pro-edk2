from pathlib import Path, PurePosixPath
import hashlib, json, re, shutil, subprocess, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel98')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel98')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
k = json.loads((out/'kernel-validation.json').read_text())
assert k['kernel_audit_pass'] and k['key_wait_behavior_unchanged'] and k['dtb_byte_identical']
assert json.loads((out/'address-isolation-validation.json').read_text())['address_isolation_audit_pass']
log = (out/'preflash.log').read_text(encoding='utf-8-sig')
for name in ('preflash.tar','boot-partition-before.img','logdump-before.img'):
    digest = re.search(r'([0-9a-f]{64})  /tmp/k98-'+re.escape(name), log)[1]
    assert sha(out/name) == digest
files = {}
with tarfile.open(out/'preflash.tar') as archive:
    for member in archive:
        if not member.isfile(): continue
        path = PurePosixPath(member.name)
        assert path.parts[0] == 'k98-preflash' and '..' not in path.parts
        name = str(PurePosixPath(*path.parts[1:]))
        assert name not in files
        files[name] = archive.extractfile(member).read()
checked = set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name = line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest()==digest
    checked.add(name)
assert checked == files.keys()-{'SHA256SUMS'}
assert len(files['nv-source-check.txt'].decode().splitlines())==6
assert all(x.endswith(': OK') for x in files['nv-source-check.txt'].decode().splitlines())
guard = files['guard.txt'];boot_id=guard.decode().splitlines()[0]
assert re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot_id)
assert sha(out/'boot-partition-before.img')=='a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7'
assert sha(out/'logdump-before.img')=='935141253c61f2b9bb4ab92103217adaa45800a00894215326e1dac0d955718a'
(out/'guard-before-flash.txt').write_bytes(guard)
(out/'persist-before.sha').write_bytes(files['persist-before.sha'])
boot = out.parent/'kernel93/boot-k93-connectivity.img'
assert sha(boot)=='0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158'
assert (out/'boot-partition-before.img').read_bytes()[:boot.stat().st_size]==boot.read_bytes()
target = out/'logdump-k98-connectivity.img'
assert not target.exists()
shutil.copyfile(out/'logdump-before.img',target)
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-']) == (out/'dtb-connectivity').read_bytes()
subprocess.run(['mcopy','-o','-i',str(target),str(out/'Image-connectivity'),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-']) == (out/'Image-connectivity').read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
new_data=[(ref/'samurai-radio-address').read_bytes(),(out/'hci_uart.ko').read_bytes()]
for name,content in files.items():
    if name.endswith('-mac-le.bin'):
        assert len(content)==6
        assert all(content not in data and content[::-1] not in data for data in new_data)
profile=(out.parent/'kernel95/wpa-test-private.conf').read_text()
for value in re.findall(r'^\s*#?\s*(?:psk|ssid)\s*=\s*(.+?)\s*$',profile,re.M):
    value=value.strip('"').encode()
    assert all(value not in data for data in new_data)
report=dict(candidate_audit_pass=True,kernel_build=97,original_initramfs_files_preserved=True,
    earlier_snapshots_preserved=True,dtb_byte_identical=True,firmware_boot_reused_byte_identical=True,
    embedded_wifi_credentials=False,embedded_device_addresses=False,nv_partition_writes=False,
    only_flash_partitions=['logdump'],before_boot_id=boot_id,boot_sha256=sha(boot),logdump_sha256=sha(target),
    full_backup_boot_sha256=sha(out/'boot-partition-before.img'),full_backup_logdump_sha256=sha(out/'logdump-before.img'),
    preflash_sha256=sha(out/'preflash.tar'),private_preflash_files_verified=len(checked),
    address_query_independence_ram_tested=True,uart_diagnostics_only=True,key_wait_behavior_unchanged=True,goal_complete=False)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key!='before_boot_id'},indent=2))
