from pathlib import Path
import tarfile,hashlib,json,shutil
out=Path('/mnt/e/edk2-samurai-out/kernel119');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel119')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
    with tarfile.open(path) as tf:
        d={}
        for m in tf:
            assert not m.issym() and not m.islnk()
            if not m.isfile():continue
            name=m.name.removeprefix('./');assert name not in d and '..' not in Path(name).parts and not Path(name).is_absolute()
            d[name]=tf.extractfile(m).read()
    for line in d['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1);assert hashlib.sha256(d[name.removeprefix('./')]).hexdigest()==digest
    return d
assert sha(out/'preflash.tar')=='b59460a09c1764cd49b94f840e041242219ebf2975539d1cbf4c6efd6dadcf73'
d=load(out/'preflash.tar');old=load(out.parent/'kernel112/layout-after.tar')
for dev in ('sda','sdb','sdc','sdd','sde','sdf'):
    for suffix in ('geometry','head','tail'):assert d[f'{dev}.{suffix}']==old[f'{dev}.{suffix}']
assert b'#115 SMP PREEMPT' in d['uname.txt'] and d['state.txt'].splitlines()[-1]==b'0'
assert d['boot-id-private.txt']==(out.parent/'kernel115/final-boot-id-private.txt').read_bytes()
assert d['phosh.txt'].strip() and d['phoc.txt'].strip() and d['connector.txt'].strip()==b'connected'
assert d['traces.txt'].strip()==b'0\n0' and d['sensors.txt'].strip()==b'offline\nvdd=0 vddio=0'
assert d['pcm.txt'].strip()==b'closed\nclosed'
assert d['amps.txt'].count(b'powered=0 muted=1')==2
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert d[name].count(b': OK')==count and b'FAILED' not in d[name]
assert d['ipa-module.sha256'].decode().split()[0]=='bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0'
parts=dict(line.split('  ')[::-1] for line in d['partition-check.sha256'].decode().splitlines())
candidate=json.loads((out.parent/'kernel118/candidate-package-validation.json').read_text())
for dev,name,dest in [('/dev/sde11','boot-partition-k115.img','boot-partition-before.img'),('/dev/sde32','logdump-k115-ipa-zram.img','logdump-before.img')]:
    source=out.parent/'kernel115'/name;assert parts[dev]==sha(source)
    target=out/dest
    if not target.exists():shutil.copy2(source,target)
    assert sha(target)==parts[dev]
assert parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
assert parts['/dev/sde11']==candidate['boot_115_sha256'] and parts['/dev/sde32']==candidate['rollback_logdump_115_sha256']
(out/'source-boot-id-private.txt').write_bytes(d['boot-id-private.txt'])
report=dict(preflash_audit_pass=True,current_kernel=115,target_kernel=118,live_backups_match=True,rollback_reused_byte_identical_115_backups=True,archive_members_verified=True,same_current_boot=True,taint=0,gpt18_unchanged=True,nv6_source4_vendor_preserved=True,persist_unchanged=True,current_gui_verified=True,current_audio_idle_verified=True,ipa_fixed_module_preserved=True,traces_off=True,archive_sha256=sha(out/'preflash.tar'),before_boot_sha256=parts['/dev/sde11'],before_logdump_sha256=parts['/dev/sde32'],flash_partitions=['logdump'],goal_complete=False)
(ref/'preflash-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'preflash-validation.json').write_text(json.dumps(dict(report,boot_id=d['boot-id-private.txt'].decode().strip()),indent=2)+'\n')
print(json.dumps(report,indent=2))
