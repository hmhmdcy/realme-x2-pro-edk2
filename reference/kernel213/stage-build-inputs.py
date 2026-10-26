from pathlib import Path
import hashlib,host,json,tarfile
here=Path(__file__).resolve().parent;manifest=json.loads((here/'sdk-fetch-validation.json').read_text());assert manifest['all_signatures_verified'] and len(manifest['signed_apks'])>=10
private=host.PRIVATE;packages=private/'sdk-apks-r2'
selected=[r for r in manifest['signed_apks'] if '-dev-' in r['name'] or r['name'].startswith(('py3-jinja2-','py3-ply-','py3-yaml-','py3-markupsafe-'))]
assert len(selected)>=10
source=private/'libcamera-helper-source.tar.gz';assert hashlib.sha256(source.read_bytes()).hexdigest()==json.loads((here/'helper-source-validation.json').read_text())['source_archive_sha256']
bundle=private/'build-inputs.tar';assert not bundle.exists()
with tarfile.open(bundle,'w') as archive:
    archive.add(source,arcname='source.tar.gz')
    for record in selected:
        path=packages/record['name'];assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'];archive.add(path,arcname='apks/'+path.name)
digest=hashlib.sha256(bundle.read_bytes()).hexdigest();remote='/var/lib/samurai/k213-libcamera-build'
host.ssh('test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k213-baseline/boot-id-private.txt)" && test "$(cat /proc/sys/kernel/tainted)" = 0 && mkdir -m700 '+remote+'/input-chunks')
chunks=private/'input-chunks';chunks.mkdir(mode=0o700)
with bundle.open('rb') as reader:
    index=0
    while data:=reader.read(1048576):
        path=chunks/(str(index).zfill(4)+'.part');path.write_bytes(data);host.upload(path,remote+'/input-chunks/'+path.name);index+=1
        if index%8==0:print(json.dumps(dict(uploaded_one_mib_chunks=index)),flush=True)
code=r'''
from pathlib import Path
import hashlib,json,tarfile
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
out=root/'k213-libcamera-build';parts=sorted((out/'input-chunks').glob('*.part'));assert len(parts)==CHUNK_COUNT
bundle=out/'build-inputs.tar';assert not bundle.exists()
with bundle.open('xb') as destination:
    for p in parts:destination.write(p.read_bytes())
assert hashlib.sha256(bundle.read_bytes()).hexdigest()==DIGEST
inputs=out/'inputs';inputs.mkdir(mode=0o700)
with tarfile.open(bundle) as archive:archive.extractall(inputs,filter='data')
assert len(list((inputs/'apks').glob('*.apk')))==PACKAGE_COUNT
print(json.dumps(dict(stage=213,build_inputs_verified=True,signed_development_apks_staged=PACKAGE_COUNT,no_system_package_install=True)))
'''.replace('CHUNK_COUNT',str(index)).replace('PACKAGE_COUNT',str(len(selected))).replace('DIGEST',repr(digest))
p=host.ssh('python3 -',input=code.encode(),timeout=60);(private/'build-inputs-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);report.update(staged_bytes=bundle.stat().st_size,one_mib_chunks=index)
(here/'build-inputs-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
