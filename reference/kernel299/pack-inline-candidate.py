"""Package only an isolated executable/library test bundle, never an APK upgrade."""
from pathlib import Path
import hashlib,io,json,re,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
build=json.loads((HERE/'inline-build-validation.json').read_text());assert build['build_exit']==0
tools=json.loads((HERE/'inline-smoke-tools-validation.json').read_text())
assert tools['application_source_sha256']==hashlib.sha256((HERE/'pipeline-smoke.cpp').read_bytes()).hexdigest()
assert tools['fixture_source_sha256']==hashlib.sha256((HERE/'pipeline-fixture.c').read_bytes()).hexdigest()
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');tree=sdk/'work/libcamera299-inline'
# Source must match the latest candidate, including restart fixes.
assert (tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp').read_bytes()==(HERE/'pipeline/camss_vfe.cpp').read_bytes()
files={
 'bin/pipeline-smoke':P/'pipeline-smoke-aarch64-private',
 'bin/pipeline-fixture':P/'pipeline-fixture-aarch64-private',
 'lib/libcamera.so.0.7':tree/'output/src/libcamera/libcamera.so.0.7.2',
 'lib/libcamera-base.so.0.7':tree/'output/src/libcamera/base/libcamera-base.so.0.7.2',
 'profile/manual.yaml':HERE/'manual-sunny-imx319-bls.yaml',
}
run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r[1-9][0-9]*',run)
archive=P/('inline-bundle-private.tar.gz' if run=='r1' else f'inline-bundle-{run}-private.tar.gz');assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name,path in files.items():
  raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name.startswith('bin/') else 0o600
  tar.addfile(item,io.BytesIO(raw))
report=dict(stage=299,run=run,archive_file=archive.name,archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
 private_test_bundle_only=True,not_system_package_upgrade=True,physical_pipeline_acceptance_pending=True,
 files={n:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for n,p in files.items()})
(HERE/f'inline-bundle-{run}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'inline-bundle-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
