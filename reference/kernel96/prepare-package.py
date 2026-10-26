from pathlib import Path,PurePosixPath
import hashlib,json,shutil,subprocess,tarfile,re
out=Path('/mnt/e/edk2-samurai-out/kernel96')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
k=json.loads((out/'kernel-validation.json').read_text())
assert k['kernel_audit_pass'] and k['dtb_byte_identical'] and k['existing_files_symlinks_modes_preserved']
assert sha(out/'preflash.tar')=='0f2c2706db7537ced585100416c10fe0fd0061176a1e39b94bcccc7e64bc8d4a'
assert sha(out/'boot-partition-before.img')=='a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7'
assert sha(out/'logdump-before.img')=='f69091aa4dde55bee83f639ee1442ba567190ca52fa3baf2216f0eae84da4fe5'
files={}
with tarfile.open(out/'preflash.tar') as src:
    for m in src:
        if not m.isfile():continue
        p=PurePosixPath(m.name);assert p.parts[0]=='k96-preflash' and '..' not in p.parts
        name=str(PurePosixPath(*p.parts[1:]));assert name not in files
        files[name]=src.extractfile(m).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name in files and name not in checked
    assert hashlib.sha256(files[name]).hexdigest()==digest;checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
guard=files['guard.txt'].decode();boot_id=guard.splitlines()[0]
assert re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot_id)
assert boot_id in files['state.txt'].decode()
assert len(files['nv-source-check.txt'].decode().splitlines())==6
assert all(x.endswith(': OK') for x in files['nv-source-check.txt'].decode().splitlines())
assert 'WIFI_ACTIVE_LIFECYCLE_PASS' in files['queries/k96-runtime-wifi-active.log'].decode()
assert 'BT_SCAN_WITH_MPSS_OFFLINE_PASS' in files['queries/k96-runtime-mpss-offline.log'].decode()
assert 'failed to assign msa map permissions: -22' in files['dmesg.txt'].decode()
for kind in ('bt','wlan'):
    raw=files[f'queries/k96-verified-{kind}-dms-response.bin']
    mac=files[f'queries/k96-verified-{kind}-mac-le.bin']
    assert len(raw)==24 and raw[:7]==bytes.fromhex('0201005c001100')
    assert raw[7:14]==bytes.fromhex('02040000000000')
    assert raw[14:18]==bytes.fromhex('10070006') and raw[18:]==mac
    assert len(mac)==6 and any(mac) and any(x!=255 for x in mac) and not(mac[5]&3)
(out/'guard-before-flash.txt').write_bytes(files['guard.txt'])
(out/'persist-before.sha').write_bytes(files['persist-before.sha'])
boot=out.parent/'kernel93/boot-k93-connectivity.img'
assert sha(boot)=='0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158'
assert (out/'boot-partition-before.img').read_bytes()[:boot.stat().st_size]==boot.read_bytes()
target=out/'logdump-k96-connectivity.img';assert not target.exists()
shutil.copyfile(out/'logdump-before.img',target)
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==(out/'dtb-connectivity').read_bytes()
subprocess.run(['mcopy','-o','-i',str(target),str(out/'Image-connectivity'),'::/Image'],check=True)
for name,dest in [('Image-connectivity','::/Image'),('dtb-connectivity','::/samurai.dtb')]:
    assert subprocess.check_output(['mcopy','-i',str(target),dest,'-'])==(out/name).read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
report=dict(candidate_audit_pass=True,original_initramfs_files_preserved=True,dtb_byte_identical=True,
    firmware_boot_reused_byte_identical=True,earlier_snapshots_preserved=True,embedded_wifi_credentials=False,
    embedded_device_addresses=False,nv_partition_writes=False,kernel_build=95,boot_sha256=sha(boot),logdump_sha256=sha(target),
    full_backup_boot_sha256=sha(out/'boot-partition-before.img'),full_backup_logdump_sha256=sha(out/'logdump-before.img'),
    only_flash_partitions=['logdump'],private_preflash_files_verified=len(checked),preflash_sha256=sha(out/'preflash.tar'),
    before_boot_id=boot_id,stage95_wifi_recovery_failed_preserved=True,goal_complete=False)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key!='before_boot_id'},indent=2))
