from pathlib import Path
import hashlib, json, shutil, subprocess, tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel93')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
k=json.loads((out/'kernel-validation.json').read_text());f=json.loads((out/'firmware-validation.json').read_text())
assert k['kernel_audit_pass'] and k['config_unchanged'] and k['existing_files_symlinks_modes_preserved']
assert f['other_executable_bytes_unchanged'] and len(f['changed_modules'])==1
assert sha(out/'preflash.tar')=='b16c67e7ed39f52a6d26989b02fda54a142becc6a75bb74cd43dd43e0e40d9c3'
assert sha(out/'boot-partition-before.img')=='cd75317e7384dd65463982134fd9a9ffdd35cb1f21f06a337824683c18636f48'
assert sha(out/'logdump-before.img')=='7972dae9d5f3c709fd41f8b0e577417e1f6278930afa04762bae70dbb85ace86'
with tarfile.open(out/'preflash.tar') as src: files={Path(m.name).name:src.extractfile(m).read() for m in src if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(files[name]).hexdigest()==digest
assert files['guard.txt'].decode().startswith('7198e2c9-17e4-42af-ac12-71a2013b5ea8\n')
assert all(line.endswith(': OK') for line in files['nv-source-check.txt'].decode().splitlines())
assert files['persist-check.txt'].decode().endswith(': OK\n')
(out/'guard-before-flash.txt').write_bytes(files['guard.txt'])
target=out/'logdump-k93-connectivity.img';assert not target.exists()
shutil.copyfile(out/'logdump-before.img',target)
for name,dest in [('Image-connectivity','::/Image'),('dtb-connectivity','::/samurai.dtb')]:
    subprocess.run(['mcopy','-o','-i',str(target),str(out/name),dest],check=True)
    assert subprocess.check_output(['mcopy','-i',str(target),dest,'-'])==(out/name).read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
report=dict(candidate_audit_pass=True,firmware_audit_pass=True,original_initramfs_files_preserved=True,
    earlier_snapshots_preserved=True,embedded_wifi_credentials=False,nv_partition_writes=False,
    kernel_build=92,boot_sha256=sha(out/'boot-k93-connectivity.img'),logdump_sha256=sha(target),
    full_backup_boot_sha256=sha(out/'boot-partition-before.img'),full_backup_logdump_sha256=sha(out/'logdump-before.img'),
    only_flash_partitions=['logdump','boot'],private_preflash_files_verified=len(files)-1)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
