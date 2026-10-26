from pathlib import Path, PurePosixPath
import hashlib, json, re, shutil, subprocess, tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel103')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
k=json.loads((out/'kernel-validation.json').read_text())
f=json.loads((out/'firmware-validation.json').read_text())
assert k['kernel_audit_pass'] and k['original_initramfs_files_preserved']
assert f['firmware_dtb_raw_section_matches'] and f['other_executable_bytes_unchanged']
log=(out/'preflash.log').read_text(encoding='utf-8-sig')
for name in ('preflash.tar','boot-partition-before.img','logdump-before.img'):
    match=re.search(r'([0-9a-f]{64})  /tmp/k103-'+re.escape(name),log)
    assert match and sha(out/name)==match[1]
assert sha(out/'boot-partition-before.img')=='4b3e76ae4c1ea5da894f219c20e5ca680785afd880dc2dd9fce09a3f914566ea'
assert sha(out/'logdump-before.img')=='6c96d1de3a12c64e321450b686d0ed62fb75e34b203e2bded5e972246f40f75d'
files={}
with tarfile.open(out/'preflash.tar') as tar:
    for m in tar:
        if not m.isfile():continue
        parts=PurePosixPath(m.name).parts
        assert parts[0]=='k103-preflash' and '..' not in parts
        name=str(PurePosixPath(*parts[1:]));assert name not in files
        files[name]=tar.extractfile(m).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest()==digest
    checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
assert len(files['nv-source-check.txt'].splitlines())==6
assert all(line.endswith(b': OK') for line in files['nv-source-check.txt'].splitlines())
boot_id=files['guard.txt'].decode().splitlines()[0]
assert boot_id==(out/'baseline-boot-private.txt').read_text(encoding='utf-8-sig').splitlines()[0]
(out/'guard-before-flash.txt').write_bytes(files['guard.txt'])
(out/'persist-before.sha').write_bytes(files['persist-before.sha'])
boot=out/'boot-k103-audio.img'
assert sha(boot)==f['boot_after_sha256']
assert (out/'boot-partition-before.img').read_bytes()[:(out/'boot-before.img').stat().st_size]==(out/'boot-before.img').read_bytes()
target=out/'logdump-k103-audio.img'
assert not target.exists()
shutil.copyfile(out/'logdump-before.img',target)
for name,path in [('Image',out/'Image-audio'),('samurai.dtb',out/'dtb-audio')]:
    subprocess.run(['mcopy','-o','-i',str(target),str(path),'::/'+name],check=True)
    assert subprocess.check_output(['mcopy','-i',str(target),'::/'+name,'-'])==path.read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
candidate=[(out/'Image-audio').read_bytes(),(out/'dtb-audio').read_bytes(),boot.read_bytes()]
for name,data in files.items():
    if name.endswith('-mac-le.bin'):
        assert len(data)==6 and all(data not in blob and data[::-1] not in blob for blob in candidate)
profile=(out.parent/'kernel102/wpa-5g-private.conf').read_text()
for value in re.findall(r'^\s*#?\s*(?:psk|ssid)\s*=\s*(.+?)\s*$',profile,re.M):
    assert all(value.strip('"').encode() not in blob for blob in candidate)
report=dict(candidate_audit_pass=True,kernel_build=102,logical_stage=103,original_initramfs_files_preserved=True,
  earlier_snapshots_preserved=True,firmware_dtb_raw_section_matches=True,other_executable_bytes_unchanged=True,
  embedded_wifi_credentials=False,embedded_device_addresses=False,nv_partition_writes=False,
  only_flash_partitions=['boot','logdump'],before_boot_id=boot_id,boot_sha256=sha(boot),boot_bytes=boot.stat().st_size,
  logdump_sha256=sha(target),full_backup_boot_sha256=sha(out/'boot-partition-before.img'),
  full_backup_logdump_sha256=sha(out/'logdump-before.img'),preflash_sha256=sha(out/'preflash.tar'),
  private_preflash_files_verified=len(checked),goal_complete=False)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('AUDIO_TRANSPORT_CANDIDATE_AUDIT_PASS')
