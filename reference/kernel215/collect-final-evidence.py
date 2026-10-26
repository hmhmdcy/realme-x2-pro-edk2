from pathlib import Path
import hashlib,host,json,tarfile
here=Path(__file__).resolve().parent
assert json.loads((here/'test-pattern-acceptance-validation.json').read_text())['sensor_test_pattern_now_effective']
assert all(p['exit']==0 and p['frames']==6 for p in json.loads((here/'default-clients-validation.json').read_text())['clients'].values())
original=(here.parent/'kernel214/collect-final-evidence.py').read_text();code=original.split("code=r'''",1)[1].split("'''",1)[0].replace('k214-','k215-')
p=host.ssh('python3 -',input=code.encode(),timeout=60);record=json.loads(p.stdout);(host.PRIVATE/'final-evidence-manifest-private.json').write_bytes(p.stdout)
target=host.PRIVATE/'final-evidence-private.tar.gz';assert not target.exists()
with target.open('xb') as output:
    for offset in range(0,record['bytes'],65536):
        p=host.ssh('dd if=/tmp/k215-final-evidence-private.tar.gz bs=65536 skip='+str(offset//65536)+' count=1',timeout=30);assert len(p.stdout)==min(65536,record['bytes']-offset);output.write(p.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:
    members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers()};assert members==record['members']
report=dict(stage=215,native_final_evidence_archive_retrieved=True,archive_and_all_member_hashes_verified=True,verified_members=len(members),original_sensor_module_and_all_original_metadata_backups_exported=True,private_signing_keys_and_scene_images_excluded=True,transfer_chunk_bytes=65536,archive_remains_private=True)
(here/'final-evidence-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
