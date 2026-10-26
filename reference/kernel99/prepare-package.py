from pathlib import Path, PurePosixPath
import hashlib, json, re, shutil, subprocess, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel99')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
k = json.loads((out/'kernel-validation.json').read_text())
f = json.loads((out/'firmware-validation.json').read_text())
assert k['kernel_audit_pass'] and k['cpio_byte_identical'] and k['other_dtb_nodes_semantically_preserved']
assert f['firmware_dtb_raw_section_matches'] and f['other_executable_bytes_unchanged']
log = (out/'preflash.log').read_text(encoding='utf-8-sig')
for name in ('preflash.tar','boot-partition-before.img','logdump-before.img'):
    digest = re.search(r'([0-9a-f]{64})  /tmp/k99-'+re.escape(name),log)[1]
    assert sha(out/name)==digest
files={}
with tarfile.open(out/'preflash.tar') as archive:
    for member in archive:
        if not member.isfile(): continue
        parts=PurePosixPath(member.name).parts
        assert parts[0]=='k99-preflash' and '..' not in parts
        name=str(PurePosixPath(*parts[1:]));assert name not in files
        files[name]=archive.extractfile(member).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest()==digest
    checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
assert len(files['nv-source-check.txt'].decode().splitlines())==6
assert all(x.endswith(': OK') for x in files['nv-source-check.txt'].decode().splitlines())
assert sha(out/'boot-partition-before.img')=='a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7'
assert sha(out/'logdump-before.img')=='0ebd3ec3ab41a70b86f03b09cff2dd0d9e39d0bcdf739b2fdf2c96d0694e0fc2'
guard=files['guard.txt'];boot_id=guard.decode().splitlines()[0]
assert re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot_id)
(out/'guard-before-flash.txt').write_bytes(guard)
(out/'persist-before.sha').write_bytes(files['persist-before.sha'])
boot=out/'boot-k99-haptics.img'
assert sha(boot)==f['boot_after_sha256']
assert (out/'boot-partition-before.img').read_bytes()[:(out/'boot-before.img').stat().st_size]==(out/'boot-before.img').read_bytes()
target=out/'logdump-k99-haptics.img'
assert not target.exists()
shutil.copyfile(out/'logdump-before.img',target)
for name,input_path in [('Image',out/'Image-haptics'),('samurai.dtb',out/'dtb-haptics')]:
    subprocess.run(['mcopy','-o','-i',str(target),str(input_path),'::/'+name],check=True)
    assert subprocess.check_output(['mcopy','-i',str(target),'::/'+name,'-'])==input_path.read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
new_data=[(out/'Image-haptics').read_bytes(),(out/'dtb-haptics').read_bytes(),boot.read_bytes()]
for name,address in files.items():
    if name.endswith('-mac-le.bin'):
        assert len(address)==6 and all(address not in data and address[::-1] not in data for data in new_data)
profile=(out.parent/'kernel95/wpa-test-private.conf').read_text()
for value in re.findall(r'^\s*#?\s*(?:psk|ssid)\s*=\s*(.+?)\s*$',profile,re.M):
    value=value.strip('"').encode()
    assert all(value not in data for data in new_data)
report=dict(candidate_audit_pass=True,kernel_build=98,logical_stage=99,
    original_initramfs_files_preserved=True,earlier_snapshots_preserved=True,
    firmware_dtb_raw_section_matches=True,other_executable_bytes_unchanged=True,
    cpio_byte_identical=True,embedded_wifi_credentials=False,embedded_device_addresses=False,nv_partition_writes=False,
    only_flash_partitions=['boot','logdump'],before_boot_id=boot_id,boot_sha256=sha(boot),boot_bytes=boot.stat().st_size,
    logdump_sha256=sha(target),full_backup_boot_sha256=sha(out/'boot-partition-before.img'),
    full_backup_logdump_sha256=sha(out/'logdump-before.img'),preflash_sha256=sha(out/'preflash.tar'),
    private_preflash_files_verified=len(checked),goal_complete=False)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key!='before_boot_id'},indent=2))
