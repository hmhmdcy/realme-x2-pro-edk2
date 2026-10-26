from pathlib import Path
import hashlib, json, shutil, subprocess, tarfile

O=Path('/mnt/e/edk2-samurai-out/kernel89')
P=O.parent/'kernel88'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(O/'preflash.tar.gz')=='118847bf635099f10a0cb342e40de1b2f6671c50dd767a14fd4ef55226a5c3cf'
assert sha(O/'boot-partition-before.img')=='ac0cb3a2ff3bc48e8af6f1ba9eaf760feaf9514ba61c3e56508d01a3240bbaa5'
assert sha(O/'logdump-before.img')=='cf11644e32a138ff1319fe9e44529f1ef7b2a1907c1f8876c597f970a526d286'
with tarfile.open(O/'preflash.tar.gz','r:gz') as t:
    members={Path(m.name).name:t.extractfile(m).read() for m in t.getmembers()}
for line in members['k89-preflash-hashes.txt'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(members[Path(name).name]).hexdigest()==digest,name
for name,data in members.items(): (O/name.replace('k89-','')).write_bytes(data)
assert hashlib.sha256(members['k89-preflash-snapshot.txt']).hexdigest()=='550d76908bd09bb280f57a5937fce7ec0101e4c167fed850b42834085e53f2f2'
target=O/'logdump-k89-mpss.img'
assert not target.exists()
shutil.copyfile(O/'logdump-before.img',target)
for src,dest in [(P/'Image-wifi','::/Image'),(P/'samurai-wifi.dtb','::/samurai.dtb')]:
    subprocess.run(['mcopy','-o','-i',str(target),str(src),dest],check=True)
for dest,name in [('::/Image','Image-wifi'),('::/samurai.dtb','samurai-wifi.dtb')]:
    actual=subprocess.check_output(['mcopy','-i',str(target),dest,'-'])
    assert actual==(P/name).read_bytes(),name
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
firmware=json.loads((O/'firmware-validation.json').read_text())
assert firmware['other_executable_bytes_unchanged'] and firmware['firmware_dtb_raw_section_matches']
assert firmware['boot_after_sha256']==sha(O/'boot-k89-mpss.img')
report={'candidate_audit_pass':True,'boot_sha256':sha(O/'boot-k89-mpss.img'),'boot_bytes':(O/'boot-k89-mpss.img').stat().st_size,'logdump_sha256':sha(target),'logdump_bytes':target.stat().st_size,'full_backup_boot_sha256':sha(O/'boot-partition-before.img'),'full_backup_logdump_sha256':sha(O/'logdump-before.img'),'snapshot_preserved':True,'firmware_audit_pass':True,'initramfs_byte_identical':True,'mpss_manual_start':True,'wifi_disabled':True,'deployed':False}
(O/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
