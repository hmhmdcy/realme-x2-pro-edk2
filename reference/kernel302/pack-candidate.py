"""Package the candidate module, signed object and standard IPC worker privately."""
from pathlib import Path
import hashlib,io,json,re,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;tree=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
build=json.loads((HERE/'build-validation.json').read_text());contract=json.loads((HERE/'ipa-contract-validation.json').read_text());tools=json.loads((HERE/'runtime-tools-validation.json').read_text())
assert build['build_exit']==0 and contract['real_module_dlopen_contract_exit']==0
for name,sha in build['source_sha256'].items():assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==sha
assert tools['application_source_sha256']==hashlib.sha256((HERE/'pipeline-smoke.cpp').read_bytes()).hexdigest()
if (HERE/'fixture-validation.json').exists():assert json.loads((HERE/'fixture-validation.json').read_text())['binary_sha256']==hashlib.sha256((P/'pipeline-fixture-aarch64-private').read_bytes()).hexdigest()
assert (tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp').read_bytes()==(HERE/'pipeline/camss_vfe.cpp').read_bytes()
assert (tree/'src/ipa/camss-vfe/camss.cpp').read_bytes()==(HERE/'ipa/camss.cpp').read_bytes()
files={
 'bin/pipeline-smoke':P/'pipeline-smoke-aarch64-private',
 'bin/pipeline-fixture':P/'pipeline-fixture-aarch64-private',
 'lib/libcamera.so.0.7':tree/'output/src/libcamera/libcamera.so.0.7.2',
 'lib/libcamera-base.so.0.7':tree/'output/src/libcamera/base/libcamera-base.so.0.7.2',
 'ipa/ipa_camss_vfe.so':tree/'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
 'ipa/ipa_camss_vfe.so.sign':tree/'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
 'proxy/camss_ipa_proxy':tree/'output/src/libcamera/proxy/worker/camss_ipa_proxy',
 'profile/manual.yaml':HERE/'imx319-manual.yaml',
}
assert hashlib.sha256(files['ipa/ipa_camss_vfe.so'].read_bytes()).hexdigest()==contract['module_sha256']
run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r[1-9][0-9]*',run)
archive=P/f'ipa-bundle-{run}-private.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name,path in files.items():
  raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name.startswith(('bin/','proxy/')) else 0o600
  tar.addfile(item,io.BytesIO(raw))
out=dict(stage=302,run=run,archive_file=archive.name,archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
 actual_ipa_module_and_worker_included=True,no_private_signing_key_in_bundle=True,not_system_package_upgrade=True,
 files={n:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for n,p in files.items()})
(HERE/f'ipa-bundle-{run}-validation.json').write_text(json.dumps(out,indent=2)+'\n');(HERE/'ipa-bundle-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
