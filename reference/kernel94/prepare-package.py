from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel94');prev=out.parent/'kernel93'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
k=json.loads((out/'kernel-validation.json').read_text())
assert k['kernel_audit_pass'] and k['dtb_byte_identical'] and k['existing_files_symlinks_modes_preserved']
assert sha(out/'preflash.tar')=='8fd2578bc6244a37c79777bc65c752f522575d50416539089beb1a4b801cce9e'
assert sha(out/'boot-partition-before.img')=='a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7'
assert sha(out/'logdump-before.img')=='7905d198f229f44cfd279d14f044bf659b050be0baa02a3d1a5d67c135f9c4ee'
with tarfile.open(out/'preflash.tar') as src: files={Path(m.name).name:src.extractfile(m).read() for m in src if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(files[name]).hexdigest()==digest
assert files['guard.txt'].decode().startswith('b65a234f-44f4-4ad3-9d40-ecafdeb233b1\n')
assert len(files['nv-source-check.txt'].decode().splitlines())==6
assert all(line.endswith(': OK') for line in files['nv-source-check.txt'].decode().splitlines())
(out/'guard-before-flash.txt').write_bytes(files['guard.txt'])
(out/'persist-before.sha').write_bytes(files['persist-before.sha'])
boot=prev/'boot-k93-connectivity.img'
assert sha(boot)=='0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158'
assert (out/'boot-partition-before.img').read_bytes()[:boot.stat().st_size]==boot.read_bytes()
target=out/'logdump-k94-connectivity.img';assert not target.exists()
shutil.copyfile(out/'logdump-before.img',target)
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==(out/'dtb-connectivity').read_bytes()
subprocess.run(['mcopy','-o','-i',str(target),str(out/'Image-connectivity'),'::/Image'],check=True)
for name,dest in [('Image-connectivity','::/Image'),('dtb-connectivity','::/samurai.dtb')]:
    assert subprocess.check_output(['mcopy','-i',str(target),dest,'-'])==(out/name).read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
report=dict(candidate_audit_pass=True,original_initramfs_files_preserved=True,dtb_byte_identical=True,
    firmware_boot_reused_byte_identical=True,earlier_snapshots_preserved=True,embedded_wifi_credentials=False,
    nv_partition_writes=False,kernel_build=93,boot_sha256=sha(boot),logdump_sha256=sha(target),
    full_backup_boot_sha256=sha(out/'boot-partition-before.img'),full_backup_logdump_sha256=sha(out/'logdump-before.img'),
    only_flash_partitions=['logdump'],private_preflash_files_verified=len(files)-1,preflash_sha256=sha(out/'preflash.tar'))
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
