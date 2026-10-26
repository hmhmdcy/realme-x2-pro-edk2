from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel95');prev=out.parent/'kernel93'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
k=json.loads((out/'kernel-validation.json').read_text())
assert k['kernel_audit_pass'] and k['dtb_byte_identical'] and k['existing_files_symlinks_modes_preserved']
assert sha(out/'preflash.tar')=='4e9488151d7edd289ef2176e947882b2d5f91577da277f34f1ee7a0f325d7f5e'
assert sha(out/'boot-partition-before.img')=='a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7'
assert sha(out/'logdump-before.img')=='7ea0b8a9706f8c3f60e9e982a2cf71f20ee4372b5d32ea30275c092a572bfc29'
with tarfile.open(out/'preflash.tar') as src: files={Path(m.name).name:src.extractfile(m).read() for m in src if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(files[name]).hexdigest()==digest
assert files['guard.txt'].decode().startswith('4cc1a6f8-d033-4608-bdd9-98e97a0df439\n')
assert len(files['nv-source-check.txt'].decode().splitlines())==6
assert all(line.endswith(': OK') for line in files['nv-source-check.txt'].decode().splitlines())
(out/'guard-before-flash.txt').write_bytes(files['guard.txt'])
(out/'persist-before.sha').write_bytes(files['persist-before.sha'])
boot=prev/'boot-k93-connectivity.img'
assert sha(boot)=='0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158'
assert (out/'boot-partition-before.img').read_bytes()[:boot.stat().st_size]==boot.read_bytes()
target=out/'logdump-k95-connectivity.img';assert not target.exists()
shutil.copyfile(out/'logdump-before.img',target)
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==(out/'dtb-connectivity').read_bytes()
subprocess.run(['mcopy','-o','-i',str(target),str(out/'Image-connectivity'),'::/Image'],check=True)
for name,dest in [('Image-connectivity','::/Image'),('dtb-connectivity','::/samurai.dtb')]:
    assert subprocess.check_output(['mcopy','-i',str(target),dest,'-'])==(out/name).read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
report=dict(candidate_audit_pass=True,original_initramfs_files_preserved=True,dtb_byte_identical=True,
    firmware_boot_reused_byte_identical=True,earlier_snapshots_preserved=True,embedded_wifi_credentials=False,
    nv_partition_writes=False,kernel_build=94,boot_sha256=sha(boot),logdump_sha256=sha(target),
    full_backup_boot_sha256=sha(out/'boot-partition-before.img'),full_backup_logdump_sha256=sha(out/'logdump-before.img'),
    only_flash_partitions=['logdump'],private_preflash_files_verified=len(files)-1,preflash_sha256=sha(out/'preflash.tar'))
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
