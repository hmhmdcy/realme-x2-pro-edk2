from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
O=Path('/mnt/e/edk2-samurai-out/kernel91')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(O/'preflash.tar.gz')=='9215645947d6d18db4eb7f379a719e62b7e3cad5c3cee65b1962eef7ef4c62a2'
assert sha(O/'boot-partition-before.img')=='34ee326617d685bd715eb881abd22c86474b880eab2f73b5d61ea8629a9fb841'
assert sha(O/'logdump-before.img')=='73c7154f3f221c906a49d8077ae98ca5a08fabf3a9bf29ba2c68615d496b5675'
assert sha(O/'nv-snapshots.tar')=='e4bf2dd89453471849ddee3602ae378602a300c24e62eb46d27c0d14908b8f84'
assert sha(O/'nv-SHA256SUMS')=='2712ab15bc76642a2b918f27cb018af49341873f5d06f64e081412361f6a0850'
with tarfile.open(O/'preflash.tar.gz','r:gz') as t:
    data={Path(m.name).name:t.extractfile(m).read() for m in t.getmembers()}
for line in data['k91-preflash-hashes.txt'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(data[Path(name).name]).hexdigest()==digest
for name,raw in data.items(): (O/name.replace('k91-','')).write_bytes(raw)
(O/'guard-before-flash.txt').write_bytes(data['k91-preflash-partition-hashes.txt'])
with tarfile.open(O/'nv-snapshots.tar') as t:
    nv={Path(m.name).name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
assert len(nv)==6
for line in (O/'nv-SHA256SUMS').read_text().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(nv[name]).hexdigest()==digest
assert 'PASS:' in (O/'device-unit-tests.txt').read_text()
target=O/'logdump-k91-rmtfs.img';assert not target.exists()
shutil.copyfile(O/'logdump-before.img',target)
for name,dest in [('Image-rmtfs','::/Image'),('firmware-after.dtb','::/samurai.dtb')]:
    subprocess.run(['mcopy','-o','-i',str(target),str(O/name),dest],check=True)
    assert subprocess.check_output(['mcopy','-i',str(target),dest,'-'])==(O/name).read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
fw=json.loads((O/'firmware-validation.json').read_text())
assert fw['other_executable_bytes_unchanged'] and len(fw['changed_modules'])==1
assert sha(O/'cpio-before')=='74052b3e705e5af1c2268590206da264a339cf4e042e5ed601c54f56ad66b102'
report=dict(candidate_audit_pass=True,firmware_audit_pass=True,initramfs_byte_identical=True,snapshot_preserved=True,
            kernel_build=90,boot_sha256=sha(O/'boot-k91-rmtfs.img'),logdump_sha256=sha(target),
            full_backup_boot_sha256=sha(O/'boot-partition-before.img'),full_backup_logdump_sha256=sha(O/'logdump-before.img'),
            only_flash_partitions=['logdump','boot'],nv_partition_writes=False)
(O/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
