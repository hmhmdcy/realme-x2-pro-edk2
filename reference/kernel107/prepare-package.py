from pathlib import Path,PurePosixPath
import hashlib,json,re,shutil,subprocess,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel107');prev=out.parent/'kernel106'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
k=json.loads((out/'kernel-validation.json').read_text())
old=json.loads((prev/'candidate-validation.json').read_text())
oldtests=json.loads((prev/'tests-validation.json').read_text())
assert k['kernel_audit_pass'] and k['dtb_byte_identical'] and k['original_initramfs_files_preserved']
log=(out/'preflash.log').read_text(encoding='utf-8-sig')
for n in ['preflash.tar','boot-partition-before.img','logdump-before.img']:
    m=re.search(r'([a-f0-9]{64})  /tmp/k107-'+re.escape(n),log)
    assert m and sha(out/n)==m[1]
assert sha(out/'boot-partition-before.img')==oldtests['full_boot_readback_sha256']
assert sha(out/'logdump-before.img')==old['logdump_sha256']
files={}
with tarfile.open(out/'preflash.tar') as t:
    for m in t:
        assert not m.issym() and not m.islnk()
        if not m.isfile():continue
        p=PurePosixPath(m.name)
        assert p.parts[0]=='k107-preflash' and '..' not in p.parts and not p.is_absolute()
        n=str(PurePosixPath(*p.parts[1:]));assert n not in files
        files[n]=t.extractfile(m).read()
verified=set()
for l in files['SHA256SUMS'].decode().splitlines():
    h,n=l.split('  ',1);n=n.removeprefix('./')
    assert n not in verified and hashlib.sha256(files[n]).hexdigest()==h;verified.add(n)
assert verified==files.keys()-{'SHA256SUMS'}
assert len(files['nv-source-check.txt'].splitlines())==6 and all(l.endswith(b': OK') for l in files['nv-source-check.txt'].splitlines())
boot_id=files['guard.txt'].decode().splitlines()[0]
assert boot_id==(out/'baseline-boot-private.txt').read_text(encoding='utf-8-sig').splitlines()[0]
(out/'guard-before-flash.txt').write_bytes(files['guard.txt'])
(out/'persist-before.sha').write_bytes(files['persist-before.sha'])
target=out/'logdump-k107-radio.img';assert not target.exists()
shutil.copyfile(out/'logdump-before.img',target)
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==(out/'dtb-radio').read_bytes()
subprocess.run(['mcopy','-o','-i',str(target),str(out/'Image-radio'),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==(out/'Image-radio').read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
blobs=[(out/'Image-radio').read_bytes(),(out/'dtb-radio').read_bytes()]
for n,data in files.items():
    if n.endswith('-mac-le.bin'):
        assert len(data)==6 and all(data not in b and data[::-1] not in b for b in blobs)
for v in re.findall(r'^\s*#?\s*(?:psk|ssid)\s*=\s*(.+?)\s*$',(out/'wpa-5g-private.conf').read_text(),re.M):
    assert all(v.strip('"').encode() not in b for b in blobs)
report=dict(candidate_audit_pass=True,kernel_build=106,logical_stage=107,original_initramfs_files_preserved=True,earlier_snapshots_preserved=True,dtb_byte_identical=True,firmware_boot_unchanged=True,embedded_wifi_credentials=False,embedded_device_addresses=False,nv_partition_writes=False,only_flash_partitions=['logdump'],before_boot_id=boot_id,boot_sha256=old['boot_sha256'],boot_bytes=old['boot_bytes'],logdump_sha256=sha(target),full_backup_boot_sha256=sha(out/'boot-partition-before.img'),full_backup_logdump_sha256=sha(out/'logdump-before.img'),preflash_sha256=sha(out/'preflash.tar'),private_preflash_files_verified=len(verified),goal_complete=False)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('LOGDUMP_ONLY_CANDIDATE_AUDIT_PASS')
