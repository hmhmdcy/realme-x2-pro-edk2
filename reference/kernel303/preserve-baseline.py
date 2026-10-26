"""Preserve the tested SDK sources and verify the independently runnable 302 bundle."""
from pathlib import Path
import hashlib, json, tarfile
import host
HERE = Path(__file__).resolve().parent
tree = Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
expected = json.loads((HERE.parent / 'kernel302/build-validation.json').read_text())['source_sha256']
for name, digest in expected.items():
    assert hashlib.sha256((tree / name).read_bytes()).hexdigest() == digest, name
bundle = host.PRIVATE.parent / 'kernel302/ipa-bundle-r2-private.tar.gz'
assert hashlib.sha256(bundle.read_bytes()).hexdigest() == 'a12020406954ba8663d92a53155445a8b04c532172392e428be9f109baa66c94'
archive = host.PRIVATE / 'tested302-source-private.tar.gz'
assert not archive.exists()
names = ['include/libcamera/ipa/camss.mojom', 'src/ipa/camss-vfe', 'src/libcamera/pipeline/camss-vfe']
with tarfile.open(archive, 'w:gz') as tar:
    for name in names:
        tar.add(tree / name, arcname=name)
report = dict(stage=303, baseline=302, source_sha256=expected,
              preserved_source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
              tested302_runnable_bundle_verified=True, phone_contact_failed=True,
              hardware_experiments_started=False)
(HERE / 'baseline-preservation-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
