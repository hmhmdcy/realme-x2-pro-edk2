from pathlib import Path
import hashlib,json,tarfile,struct
out=Path('/mnt/e/edk2-samurai-out/kernel115')
archive=out/'vendor-ipa-source-private.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='05744ff6a4c31548c16fdfb454ac8861dd9147b1a9390183a1603a8da5571a73'
target=out/'vendor-ipa-source'
target.mkdir(exist_ok=False)
with tarfile.open(archive) as tf:
    tf.extractall(target,filter='data')
for row in (target/'SHA256SUMS').read_text().splitlines():
    digest,rel=row.split(maxsplit=1)
    assert hashlib.sha256((target/rel).read_bytes()).hexdigest()==digest
assert ': OK' in (target/'vendor-after-check.txt').read_text()
files=[]
for p in sorted((target/'firmware').iterdir()):
    files.append(dict(name=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
mdt=(target/'firmware/ipa_fws.mdt').read_bytes()
assert mdt[:6]==b'\x7fELF\x01\x01'
header=struct.unpack_from('<16sHHIIIIIHHHHHH',mdt)
segments=[]
for i in range(header[10]):
    p=struct.unpack_from('<IIIIIIII',mdt,header[5]+i*header[9])
    segments.append(dict(index=i,type=p[0],offset=hex(p[1]),vaddr=hex(p[2]),paddr=hex(p[3]),filesz=p[4],memsz=p[5],flags=hex(p[6]),align=p[7]))
report=dict(same_handset_vendor_readonly=True,archive_hash_pass=True,member_hashes_pass=True,source_partition_unchanged=True,nv_source_checks_pass='FAILED' not in (target/'nv-check.txt').read_text(),firmware=files,elf_segments=segments,not_deployed=True,goal_complete=False)
(out/'ipa-firmware-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
