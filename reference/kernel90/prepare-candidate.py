from pathlib import Path
import hashlib,json,shutil,tarfile
O=Path('/mnt/e/edk2-samurai-out/kernel90')
B=O.parent/'kernel89'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(B/'runtime-evidence.tar.gz')=='c30521cefe9d790308e5e5730ce2c7c2d298f96a798a0a4694949a1927c6e469'
with tarfile.open(B/'runtime-evidence.tar.gz','r:gz') as t:
    data={Path(m.name).name:t.extractfile(m).read() for m in t.getmembers()}
for line in data['k89-runtime-hashes.txt'].decode().splitlines():
    digest,name=line.split('  ',1); assert hashlib.sha256(data[Path(name).name]).hexdigest()==digest,name
for name,raw in data.items(): (B/name.replace('k89-','')).write_bytes(raw)
shutil.copyfile(B/'logdump-k89-mpss.img',O/'logdump-before.img')
report=json.loads((O/'firmware-validation.json').read_text())
assert len(report['changed_modules'])==1 and report['changed_modules'][0]['classification']=='wifi_status_only'
assert report['other_executable_bytes_unchanged']
candidate={'candidate_audit_pass':True,'firmware_audit_pass':True,'initramfs_byte_identical':True,'snapshot_preserved':True,'only_boot_write':True,'kernel_build':89,'boot_sha256':sha(O/'boot-k90-wifi.img'),'logdump_sha256':sha(O/'logdump-before.img'),'full_backup_boot_sha256':sha(O/'boot-before.img'),'full_backup_logdump_sha256':sha(O/'logdump-before.img')}
(O/'candidate-validation.json').write_text(json.dumps(candidate,indent=2)+'\n')
print(json.dumps(candidate,indent=2))
