from pathlib import Path, PurePosixPath
import hashlib, json, re, shutil, subprocess, tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel100')
root=Path('/mnt/e/RealmeX2Pro edk2')
firmware=Path('/home/cy122/edk2-samurai/repo')
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
k=json.loads((out/'kernel-validation.json').read_text())
assert k['kernel_audit_pass'] and k['readiness_fix_embedded'] and k['motor_driver_unchanged']
assert json.loads((out.parent/'kernel99/checkpoint-validation.json').read_text())['checkpoint_audit_pass']
log=(out/'preflash.log').read_text(encoding='utf-8-sig')
for filename in ('preflash.tar','boot-partition-before.img','logdump-before.img'):
    digest=re.search(r'([0-9a-f]{64})  /tmp/k100-'+re.escape(filename),log)[1]
    assert sha(out/filename)==digest
assert sha(out/'boot-partition-before.img')=='91b64b25be666ec62778e96bbb2e67b985c84ac1d84f4dca10c0d0911ac068df'
assert sha(out/'logdump-before.img')=='c325eb6421b1194c17e309143183e0cf97192a395d7f4e537e829047ae6abea9'
assert (out/'boot-partition-before.img').read_bytes()[:(out/'boot-reused.img').stat().st_size]==(out/'boot-reused.img').read_bytes()
assert (firmware/'boot-samurai.img').read_bytes()==(out/'boot-reused.img').read_bytes()
assert (firmware/'workspace/Build/samurai/RELEASE_GCC5/FV/SM8150_UEFI.fd').read_bytes()==(out.parent/'kernel99/firmware-after.fd').read_bytes()
assert (firmware/'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb').read_bytes()==(out/'dtb-readiness').read_bytes()
files={}
with tarfile.open(out/'preflash.tar') as archive:
    for member in archive:
        if not member.isfile():continue
        parts=PurePosixPath(member.name).parts
        assert parts[0]=='k100-preflash' and '..' not in parts
        name=str(PurePosixPath(*parts[1:]));assert name not in files
        files[name]=archive.extractfile(member).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest()==digest
    checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
assert len(files['nv-source-check.txt'].decode().splitlines())==6
assert all(line.endswith(': OK') for line in files['nv-source-check.txt'].decode().splitlines())
guard=files['guard.txt'];boot_id=guard.decode().splitlines()[0]
assert re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot_id)
(out/'guard-before-flash.txt').write_bytes(guard)
(out/'persist-before.sha').write_bytes(files['persist-before.sha'])
target=out/'logdump-k100-readiness.img'
assert not target.exists()
assert subprocess.check_output(['mcopy','-i',str(out/'logdump-before.img'),'::/samurai.dtb','-'])==(out/'dtb-readiness').read_bytes()
shutil.copyfile(out/'logdump-before.img',target)
subprocess.run(['mcopy','-o','-i',str(target),str(out/'Image-readiness'),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==(out/'Image-readiness').read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
new_data=[(out/'Image-readiness').read_bytes(),(out/'dtb-readiness').read_bytes(),(out/'boot-reused.img').read_bytes()]
for name,address in files.items():
    if name.endswith('-mac-le.bin'):
        assert len(address)==6 and all(address not in data and address[::-1] not in data for data in new_data)
profile=(out.parent/'kernel95/wpa-test-private.conf').read_text()
for value in re.findall(r'^\s*#?\s*(?:psk|ssid)\s*=\s*(.+?)\s*$',profile,re.M):
    assert all(value.strip('"').encode() not in data for data in new_data)
report=dict(candidate_audit_pass=True,logical_stage=100,kernel_build=99,
    original_initramfs_files_preserved=True,earlier_snapshots_preserved=True,dtb_byte_identical=True,
    firmware_boot_reused_byte_identical=True,readiness_fix_embedded=True,motor_driver_unchanged=True,
    embedded_wifi_credentials=False,embedded_device_addresses=False,nv_partition_writes=False,
    only_flash_partitions=['logdump'],before_boot_id=boot_id,boot_sha256=sha(out/'boot-reused.img'),
    logdump_sha256=sha(target),full_backup_boot_sha256=sha(out/'boot-partition-before.img'),
    full_backup_logdump_sha256=sha(out/'logdump-before.img'),preflash_sha256=sha(out/'preflash.tar'),
    private_preflash_files_verified=len(checked),goal_complete=False)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key!='before_boot_id'},indent=2))
