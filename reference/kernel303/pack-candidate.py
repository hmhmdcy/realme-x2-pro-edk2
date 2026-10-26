"""Package reviewable opt-in bundles after source and contract verification."""
from pathlib import Path
import hashlib, io, json, re, sys, tarfile
import host
HERE = Path(__file__).resolve().parent
tree = Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
build = json.loads((HERE / 'build-validation.json').read_text())
contract = json.loads((HERE / 'ipa-contract-validation.json').read_text())
proxy = json.loads((HERE / 'proxy-contract-validation.json').read_text())
runtime = json.loads((HERE / 'runtime-tools-validation.json').read_text())
wire = json.loads((HERE / 'serializer-validation.json').read_text())
assert build['build_exit'] == 0 and contract['ae_simulation_pass'] and proxy['threaded_passed'] and wire['passed']
for name, digest in build['source_sha256'].items():
    assert hashlib.sha256((tree / name).read_bytes()).hexdigest() == digest
    source = HERE / ('camss.mojom' if name.endswith('.mojom') else ('ipa/' if '/ipa/' in name else 'pipeline/') + name.rsplit('/', 1)[1])
    assert source.read_bytes() == (tree / name).read_bytes(), name
assert hashlib.sha256((tree / 'output/src/ipa/camss-vfe/ipa_camss_vfe.so').read_bytes()).hexdigest() == contract['module_sha256']
version=sys.argv[1] if len(sys.argv)>1 else 'r1'
assert re.fullmatch(r'r[1-9][0-9]*',version)
kinds=[sys.argv[2]] if len(sys.argv)>2 else ['joint','ae']
assert all(k in ['joint','ae'] for k in kinds)
for kind in kinds:
    files = {
     'bin/pipeline-smoke': host.PRIVATE / f'{kind}-smoke-aarch64-private',
     'bin/pipeline-fixture': host.PRIVATE / 'pipeline-fixture-aarch64-private',
     'lib/libcamera.so.0.7': tree / 'output/src/libcamera/libcamera.so.0.7.2',
     'lib/libcamera-base.so.0.7': tree / 'output/src/libcamera/base/libcamera-base.so.0.7.2',
     'ipa/ipa_camss_vfe.so': tree / 'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
     'ipa/ipa_camss_vfe.so.sign': tree / 'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
     'proxy/camss_ipa_proxy': tree / 'output/src/libcamera/proxy/worker/camss_ipa_proxy',
     'profile/manual.yaml': HERE / 'imx319-ae.yaml' if kind == 'ae' else HERE.parent / 'kernel302/imx319-manual.yaml',
    }
    assert hashlib.sha256(files['bin/pipeline-smoke'].read_bytes()).hexdigest() == runtime['applications'][kind]['binary_sha256']
    archive = host.PRIVATE / f'candidate-{kind}-{version}-private.tar.gz'
    assert not archive.exists()
    with tarfile.open(archive, 'w:gz') as tar:
        for name, path in files.items():
            raw = path.read_bytes()
            item = tarfile.TarInfo(name); item.size = len(raw)
            item.mode = 0o700 if name.startswith(('bin/', 'proxy/')) else 0o600
            tar.addfile(item, io.BytesIO(raw))
    out = dict(stage=303, kind=kind, archive_file=archive.name,
               archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
               files={n: dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for n, p in files.items()},
               not_installed=True, hardware_verified=False, isolated_ipc_verified=proxy['passed'], private_signing_key_excluded=True)
    (HERE / f'bundle-{kind}-validation.json').write_text(json.dumps(out, indent=2) + '\n')
    (HERE / f'bundle-{kind}-{version}-validation.json').write_text(json.dumps(out, indent=2) + '\n')
    print(kind, out['archive_sha256'])
